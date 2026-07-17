"""Build personal ASR post-correction data and run MLX LoRA fine-tuning."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from ..components.config_manager import get_config_manager
from ..core.text_rewrite import (
    DEFAULT_ASR_POST_SCENE,
    SYSTEM_PROMPT_FALLBACK,
    build_asr_post_user_prompt,
)


BASE_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
BASE_MODEL_LOCAL_NAME = "Qwen2.5-1.5B-Instruct"
LORA_MODEL_ID = "botaruibo/MyVoiceTyping-qwen2.5-1.5b-lora"
MIN_AUTO_TUNE_RECORDS = 50
GIB = 1024 ** 3
MIN_QWEN15B_Q4_GGUF_BYTES = 900 * 1024 ** 2


@dataclass
class AutoTuneDatasetResult:
    dataset_dir: Path
    train_path: Path
    valid_path: Path
    total_count: int
    train_count: int
    valid_count: int


@dataclass
class AutoTuneRunResult:
    dataset: AutoTuneDatasetResult
    run_dir: Path
    adapter_dir: Path
    command: list[str]
    params: dict[str, Any]
    upgraded_model_path: Optional[Path] = None


def _emit(
    progress: Optional[Callable[[dict[str, Any]], None]],
    *,
    phase: str,
    message: str,
    percent: Optional[float] = None,
    action: str = "update",
    title: str = "自动调优模型",
) -> None:
    print(message)
    if progress:
        progress({
            "action": action,
            "phase": phase,
            "title": title,
            "message": message,
            "progress": percent,
        })


def calculate_mlx_lora_params(record_count: int) -> dict[str, Any]:
    """Calculate conservative MLX LoRA parameters from personal sample count."""
    count = max(0, int(record_count or 0))
    batch_size = 1 if count < 80 else 2 if count < 300 else 4
    iters = max(20, min(1000, count * 4))
    steps_per_report = max(5, min(20, max(1, iters // 10)))
    steps_per_eval = max(10, min(100, max(1, iters // 5)))
    val_batches = max(1, min(25, max(1, math.ceil(max(count, 1) * 0.1 / batch_size))))
    save_every = max(20, min(200, max(1, iters // 2)))
    return {
        "batch_size": batch_size,
        "iters": iters,
        "learning_rate": 1e-5,
        "steps_per_report": steps_per_report,
        "steps_per_eval": steps_per_eval,
        "val_batches": val_batches,
        "save_every": save_every,
        "max_seq_length": 1024,
        "num_layers": 16,
    }


def _path_from_config(value: Any, base_dir: Optional[Path] = None) -> Path:
    path = Path(str(value or "")).expanduser()
    if path.is_absolute():
        return path
    return (base_dir or Path.cwd()) / path


def _dataset_from_metadata(metadata: dict[str, Any]) -> AutoTuneDatasetResult:
    dataset = metadata.get("dataset") or {}
    return AutoTuneDatasetResult(
        dataset_dir=Path(str(dataset.get("dataset_dir") or "")),
        train_path=Path(str(dataset.get("train_path") or "")),
        valid_path=Path(str(dataset.get("valid_path") or "")),
        total_count=int(dataset.get("total_count") or 0),
        train_count=int(dataset.get("train_count") or 0),
        valid_count=int(dataset.get("valid_count") or 0),
    )


def _find_pending_upgrade_run() -> Optional[dict[str, Any]]:
    """Find the newest finished LoRA run whose GGUF upgrade is still incomplete."""
    config = get_config_manager()
    runs_dir = config.get_train_dir() / "runs"
    if not runs_dir.exists():
        return None
    for run_config_path in sorted(runs_dir.glob("auto_*/run_config.json"), reverse=True):
        try:
            metadata = json.loads(run_config_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if metadata.get("status") != "success":
            continue
        if metadata.get("upgrade_status") == "success" and metadata.get("upgraded_model_path"):
            continue
        run_dir = run_config_path.parent
        adapter_dir = _path_from_config(metadata.get("adapter_path"), Path.cwd())
        if not adapter_dir.exists():
            adapter_dir = run_dir / "adapters"
        if not (adapter_dir / "adapters.safetensors").exists():
            continue
        base_model_dir = _path_from_config(metadata.get("base_model"), Path.cwd())
        if not base_model_dir.exists():
            base_model_dir = config.get_train_dir() / "basemodel" / BASE_MODEL_LOCAL_NAME
        return {
            "run_config_path": run_config_path,
            "run_dir": run_dir,
            "adapter_dir": adapter_dir,
            "base_model_dir": base_model_dir,
            "metadata": metadata,
            "dataset": _dataset_from_metadata(metadata),
            "params": metadata.get("params") or {},
        }
    return None


def _format_space_gib(bytes_value: int) -> str:
    gib = max(0.0, bytes_value / GIB)
    if gib < 10:
        return f"{gib:.1f} GB"
    return f"{math.ceil(gib)} GB"


def _estimate_auto_tune_required_space(
    *,
    needs_base_download: bool,
    needs_lora_download: bool,
    has_convert_script: bool,
    has_quantize_bin: bool,
    pending: Optional[dict[str, Any]],
) -> int:
    """Estimate minimum free disk space needed for the remaining auto-tune work."""
    if pending is not None:
        upgrade_dir = Path(pending["run_dir"]) / "upgrade"
        q4_gguf = upgrade_dir / "MyVoiceTyping-1.5b-q4_k_m.gguf"
        f16_gguf = upgrade_dir / "MyVoiceTyping-1.5b-f16.gguf"
        fused_dir = upgrade_dir / "fused_model"
        if _is_complete_q4_gguf(q4_gguf):
            return int(2.0 * GIB)
        if f16_gguf.exists():
            return int(4.0 * GIB)
        if fused_dir.exists():
            return int(7.0 * GIB)
        return int(8.0 * GIB)

    # Peak scratch files for a fresh full upgrade: fused HF model (~3G),
    # F16 GGUF (~3G), Q4 GGUF (~1G), plus logs and filesystem breathing room.
    required_gib = 8.0
    if needs_base_download:
        required_gib += 3.5
    if needs_lora_download:
        required_gib += 0.3
    if not (has_convert_script and has_quantize_bin):
        required_gib += 1.0
    return int(math.ceil(required_gib) * GIB)


def preview_auto_tune_plan() -> dict[str, Any]:
    """Return a lightweight preview used by the confirmation dialog."""
    config = get_config_manager()
    history_path = config.get_transcripts_dir() / "voice_history.jsonl"
    records = _read_history_records(history_path)
    params = calculate_mlx_lora_params(len(records))
    train_dir = config.get_train_dir()
    base_model_dir = train_dir / "basemodel" / BASE_MODEL_LOCAL_NAME
    lora_dir = train_dir / "lora"
    needs_base_download = not _model_dir_has_files(base_model_dir)
    needs_lora_download = not _model_dir_has_files(lora_dir)

    # Conservative user-facing estimate. Real time depends heavily on Apple Silicon
    # generation, memory pressure, network speed, and sample length.
    train_minutes = max(5, min(45, math.ceil(params["iters"] / 35)))
    download_minutes = 20 if needs_base_download else 0
    if needs_lora_download:
        download_minutes += 2
    total_min = max(5, train_minutes + download_minutes)
    total_max = max(total_min + 5, total_min + (25 if needs_base_download else 10))
    has_convert_script = _llama_cpp_convert_script() is not None
    has_quantize_bin = _llama_cpp_quantize_bin() is not None
    pending = _find_pending_upgrade_run()
    required_space_bytes = _estimate_auto_tune_required_space(
        needs_base_download=needs_base_download,
        needs_lora_download=needs_lora_download,
        has_convert_script=has_convert_script,
        has_quantize_bin=has_quantize_bin,
        pending=pending,
    )
    try:
        train_dir.mkdir(parents=True, exist_ok=True)
        available_space_bytes = shutil.disk_usage(train_dir).free
    except Exception:
        available_space_bytes = 0
    return {
        "record_count": len(records),
        "min_record_count": MIN_AUTO_TUNE_RECORDS,
        "too_few_records": len(records) < MIN_AUTO_TUNE_RECORDS,
        "pending_upgrade_run": str(pending["run_dir"]) if pending else "",
        "params": params,
        "needs_base_download": needs_base_download,
        "needs_lora_download": needs_lora_download,
        "can_upgrade_gguf": has_convert_script and has_quantize_bin,
        "has_convert_script": has_convert_script,
        "has_quantize_bin": has_quantize_bin,
        "estimated_minutes_text": f"{total_min}-{total_max} 分钟",
        "required_disk_space_bytes": required_space_bytes,
        "required_disk_space_text": _format_space_gib(required_space_bytes),
        "available_disk_space_bytes": available_space_bytes,
        "available_disk_space_text": _format_space_gib(available_space_bytes) if available_space_bytes else "未知",
        "download_note": "首次运行需要下载 Qwen2.5-1.5B 基线模型，文件较大。" if needs_base_download else "基线模型已存在，将直接进入数据准备和训练。",
    }


def _read_history_records(history_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not history_path.exists():
        return records
    for line in history_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        raw_text = str(item.get("raw_text") or item.get("input") or "").strip()
        final_text = str(item.get("final_text") or item.get("output") or raw_text).strip()
        if not raw_text or not final_text:
            continue
        item["raw_text"] = raw_text
        item["final_text"] = final_text
        item["scene"] = str(item.get("scene") or DEFAULT_ASR_POST_SCENE).strip() or DEFAULT_ASR_POST_SCENE
        records.append(item)
    return records


def _chatml_record(record: dict[str, Any], system_prompt: str) -> dict[str, Any]:
    scene = str(record.get("scene") or DEFAULT_ASR_POST_SCENE)
    raw_text = str(record.get("raw_text") or "")
    final_text = str(record.get("final_text") or raw_text)
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_asr_post_user_prompt(raw_text, scene=scene)},
            {"role": "assistant", "content": final_text},
        ],
        "scene": scene,
        "raw_text": raw_text,
        "final_text": final_text,
        "metadata": {
            "id": str(record.get("id") or record.get("dataId") or ""),
            "dataId": str(record.get("dataId") or ""),
            "scene": scene,
            "scene_bundle_id": str(record.get("scene_bundle_id") or ""),
            "scene_app_name": str(record.get("scene_app_name") or ""),
            "source": "voice_history",
        },
    }


def build_auto_tune_dataset(
    history_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    min_records: int = MIN_AUTO_TUNE_RECORDS,
) -> AutoTuneDatasetResult:
    config = get_config_manager()
    history_path = history_path or (config.get_transcripts_dir() / "voice_history.jsonl")
    output_dir = output_dir or (config.get_train_dir() / "dataset")
    records = _read_history_records(history_path)
    if len(records) < min_records:
        raise ValueError(f"历史语音输入记录不足，至少需要 {min_records} 条，当前 {len(records)} 条")

    output_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = (config.main_prompt or SYSTEM_PROMPT_FALLBACK).strip() or SYSTEM_PROMPT_FALLBACK

    # Keep chronological order but make validation deterministic: last 10%, at least one.
    valid_count = max(1, min(len(records) - 1, math.ceil(len(records) * 0.1)))
    train_records = records[:-valid_count]
    valid_records = records[-valid_count:]

    train_path = output_dir / "train.jsonl"
    valid_path = output_dir / "valid.jsonl"
    test_path = output_dir / "test.jsonl"
    summary_path = output_dir / "summary.json"

    def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(_chatml_record(item, system_prompt), ensure_ascii=False) + "\n")

    _write_jsonl(train_path, train_records)
    _write_jsonl(valid_path, valid_records)
    _write_jsonl(test_path, valid_records)
    summary = {
        "source": str(history_path),
        "dataset_dir": str(output_dir),
        "total_count": len(records),
        "train_count": len(train_records),
        "valid_count": len(valid_records),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return AutoTuneDatasetResult(
        dataset_dir=output_dir,
        train_path=train_path,
        valid_path=valid_path,
        total_count=len(records),
        train_count=len(train_records),
        valid_count=len(valid_records),
    )


def _model_dir_has_files(path: Path) -> bool:
    return path.exists() and any(p.is_file() for p in path.rglob("*") if ".cache" not in p.parts)


def _download_modelscope_repo(
    model_id: str,
    target_dir: Path,
    revision: str = "master",
    progress: Optional[Callable[[dict[str, Any]], None]] = None,
) -> None:
    from modelscope.hub.snapshot_download import snapshot_download
    from modelscope.hub.callback import ProgressCallback

    target_dir.mkdir(parents=True, exist_ok=True)

    class _AutoTuneDownloadCallback(ProgressCallback):
        _min_determinate_bytes = 5 * 1024 * 1024

        def __init__(self, filename: str, file_size: int):
            super().__init__(filename, file_size)
            self.downloaded = 0
            self._last_report = 0.0
            _emit(
                progress,
                phase="download",
                message=f"正在下载 {filename}",
                percent=None,
            )

        def update(self, size: int):
            self.downloaded += int(size or 0)
            now = time.time()
            if now - self._last_report < 0.15:
                return
            self._last_report = now
            if self.file_size >= self._min_determinate_bytes:
                percent = max(0.0, min(29.0, (self.downloaded / max(self.file_size, 1)) * 29.0))
                _emit(
                    progress,
                    phase="download",
                    message=f"下载 {self.filename}: {percent / 29.0 * 100:.1f}%",
                    percent=percent,
                )
            else:
                _emit(progress, phase="download", message=f"正在下载 {self.filename}", percent=None)

        def end(self):
            _emit(progress, phase="download", message=f"已下载 {self.filename}", percent=None)

    callbacks = [_AutoTuneDownloadCallback] if progress else None
    snapshot_download(
        model_id,
        local_dir=str(target_dir),
        revision=revision,
        progress_callbacks=callbacks,
    )


def ensure_auto_tune_models(progress: Optional[Callable[[dict[str, Any]], None]] = None) -> tuple[Path, Optional[Path]]:
    config = get_config_manager()
    train_dir = config.get_train_dir()
    base_model_dir = train_dir / "basemodel" / BASE_MODEL_LOCAL_NAME
    lora_dir = train_dir / "lora"

    if not _model_dir_has_files(base_model_dir):
        _emit(progress, phase="download", message=f"正在下载自动调优基础模型: {BASE_MODEL_ID}", percent=None)
        _download_modelscope_repo(BASE_MODEL_ID, base_model_dir, progress=progress)
    else:
        _emit(progress, phase="download", message=f"自动调优基础模型已存在: {base_model_dir}", percent=18)

    if not _model_dir_has_files(lora_dir):
        _emit(progress, phase="download", message=f"正在下载自动调优初始 LoRA: {LORA_MODEL_ID}", percent=None)
        _download_modelscope_repo(LORA_MODEL_ID, lora_dir, progress=progress)
    else:
        _emit(progress, phase="download", message=f"自动调优初始 LoRA 已存在: {lora_dir}", percent=24)

    candidates = sorted(
        list(lora_dir.rglob("adapters.safetensors")) + list(lora_dir.rglob("*.safetensors")),
        key=lambda p: (p.name != "adapters.safetensors", len(str(p))),
    )
    return base_model_dir, candidates[0] if candidates else None


def _resolve_python_executable() -> str:
    project_root = Path(__file__).resolve().parents[2]
    venv_python = project_root / "venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _stream_subprocess(
    cmd: list[str],
    log_path: Path,
    *,
    progress: Optional[Callable[[dict[str, Any]], None]] = None,
    phase: str,
    total_iters: int = 0,
    base_percent: float = 0.0,
    span_percent: float = 100.0,
    extra_env: Optional[dict[str, str]] = None,
) -> None:
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, **(extra_env or {}), "PYTHONUNBUFFERED": "1"},
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
            message = line.strip()
            if not message:
                continue
            percent = None
            if total_iters > 0:
                match = re.search(r"\bIter(?:ation)?\s+(\d+)", message, re.IGNORECASE)
                if match:
                    current = max(0, min(total_iters, int(match.group(1))))
                    percent = base_percent + span_percent * current / total_iters
            if progress and (percent is not None or "Iter " in message or "Val" in message):
                _emit(progress, phase=phase, message=message[:160], percent=percent)
        code = process.wait()
    if code != 0:
        tail = ""
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = "\n".join(lines[-12:])
        except Exception:
            pass
        detail = f"命令退出码 {code}: {' '.join(cmd)}"
        if tail:
            detail += f"\n最近日志:\n{tail}"
        raise RuntimeError(detail)


def _llama_cpp_convert_script() -> Optional[Path]:
    env_path = os.environ.get("LLAMA_CPP_CONVERT_SCRIPT") or os.environ.get("MYVOICETYPING_GGUF_CONVERT_SCRIPT")
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            return path
    project_root = Path(__file__).resolve().parents[2]
    try:
        tools_dir = get_config_manager().get_tools_dir()
        candidate = tools_dir / "bin" / "convert_hf_to_gguf.py"
        if candidate.exists():
            return candidate
    except Exception:
        pass
    bundled = project_root / "tools" / "bin" / "convert_hf_to_gguf.py"
    if bundled.exists():
        return bundled
    found = shutil.which("convert_hf_to_gguf.py")
    return Path(found) if found else None


def _llama_cpp_pythonpath(convert_script: Path) -> str:
    """Prefer the gguf package bundled with the same llama.cpp checkout."""
    llama_cpp_dir = convert_script.resolve().parent
    entries: list[str] = []
    gguf_py_dir = llama_cpp_dir / "gguf-py"
    if gguf_py_dir.exists():
        entries.append(str(gguf_py_dir))
    entries.append(str(llama_cpp_dir))
    existing = os.environ.get("PYTHONPATH")
    if existing:
        entries.append(existing)
    return os.pathsep.join(entries)


def _write_convert_sitecustomize(directory: Path) -> Path:
    """Hide broken optional sklearn/scipy imports from the converter process."""
    directory.mkdir(parents=True, exist_ok=True)
    sitecustomize_path = directory / "sitecustomize.py"
    sitecustomize_path.write_text(
        "\n".join([
            '"""Scoped import guards for llama.cpp GGUF conversion."""',
            "import importlib.util",
            "",
            "_original_find_spec = importlib.util.find_spec",
            "",
            "def _find_spec(name, package=None):",
            "    if name == 'sklearn' or name.startswith('sklearn.'):",
            "        return None",
            "    return _original_find_spec(name, package)",
            "",
            "importlib.util.find_spec = _find_spec",
            "",
        ]),
        encoding="utf-8",
    )
    return sitecustomize_path


def _llama_cpp_convert_env(convert_script: Path, work_dir: Path) -> dict[str, str]:
    guard_dir = work_dir / "_convert_python_guard"
    _write_convert_sitecustomize(guard_dir)
    pythonpath = os.pathsep.join([
        str(guard_dir),
        _llama_cpp_pythonpath(convert_script),
    ])
    return {
        "PYTHONPATH": pythonpath,
        "TRANSFORMERS_NO_ADVISORY_WARNINGS": "1",
    }


def _remove_path_quietly(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    except Exception as e:
        print(f"⚠️ 清理临时文件失败: {path} ({e})")


def _is_complete_q4_gguf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size >= MIN_QWEN15B_Q4_GGUF_BYTES
    except Exception:
        return False


def _llama_cpp_quantize_bin() -> Optional[str]:
    project_root = Path(__file__).resolve().parents[2]
    try:
        tools_dir = get_config_manager().get_tools_dir()
        candidate = tools_dir / "bin" / "llama-quantize"
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    except Exception:
        pass
    bundled = project_root / "tools" / "bin" / "llama-quantize"
    if bundled.exists() and os.access(bundled, os.X_OK):
        return str(bundled)
    for name in ("llama-quantize", "quantize"):
        found = shutil.which(name)
        if found:
            return found
    env_path = os.environ.get("LLAMA_CPP_QUANTIZE_BIN") or os.environ.get("MYVOICETYPING_GGUF_QUANTIZE_BIN")
    if env_path and Path(env_path).expanduser().exists():
        return str(Path(env_path).expanduser())
    return None


def _installer_script_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    candidates = [
        project_root / "scripts" / "install_llama_cpp_tools.sh",
    ]
    try:
        exe_path = Path(sys.executable).resolve()
        candidates.append(exe_path.parent.parent / "Resources" / "scripts" / "install_llama_cpp_tools.sh")
    except Exception:
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("未找到 llama.cpp 工具安装脚本 install_llama_cpp_tools.sh")


def ensure_llama_cpp_tools(
    *,
    run_dir: Path,
    progress: Optional[Callable[[dict[str, Any]], None]] = None,
) -> tuple[Path, str]:
    """Ensure GGUF conversion tools exist, installing llama.cpp tools if needed."""
    convert_script = _llama_cpp_convert_script()
    quantize_bin = _llama_cpp_quantize_bin()
    if convert_script is not None and quantize_bin is not None:
        _emit(progress, phase="tools", message="llama.cpp GGUF 转换工具已存在", percent=28)
        return convert_script, quantize_bin

    config = get_config_manager()
    tools_dir = config.get_tools_dir()
    installer = _installer_script_path()
    log_path = run_dir / "install_llama_cpp_tools.log"
    _emit(
        progress,
        phase="tools",
        message="未检测到 GGUF 转换工具，正在自动安装 llama.cpp 工具…",
        percent=25,
    )
    env = {
        **os.environ,
        "LLAMA_CPP_TOOLS_ROOT": str(tools_dir),
        "PYTHONUNBUFFERED": "1",
    }

    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["bash", str(installer), "--install"],
            cwd=str(Path(__file__).resolve().parents[2]),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
            message = line.strip()
            if message:
                percent = None
                if "克隆" in message or "Cloning" in message:
                    percent = 25
                elif "构建" in message or "Build files" in message:
                    percent = 27
                elif "安装完成" in message or "工具已就绪" in message:
                    percent = 29
                _emit(progress, phase="tools", message=message[:160], percent=percent)
        code = process.wait()

    if code != 0:
        tail = ""
        try:
            tail = "\n".join(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-16:])
        except Exception:
            pass
        raise RuntimeError(
            "自动安装 llama.cpp GGUF 工具失败。请确认已安装 Xcode Command Line Tools、git、cmake，"
            f"并检查日志: {log_path}\n{tail}"
        )

    convert_script = _llama_cpp_convert_script()
    quantize_bin = _llama_cpp_quantize_bin()
    if convert_script is None or quantize_bin is None:
        raise RuntimeError(f"llama.cpp 工具安装结束但仍未检测到转换工具，请检查日志: {log_path}")
    _emit(progress, phase="tools", message="llama.cpp GGUF 转换工具安装完成", percent=29)
    return convert_script, quantize_bin


def _resolve_llama_cpp_model_dir() -> Path:
    config = get_config_manager()
    configured = Path(str(config.get("llama_cpp_model_path") or "data/models/MyVoiceTyping-1.5b-q4")).expanduser()
    if configured.is_absolute():
        return configured
    if configured.parts and configured.parts[0] == "data" and len(configured.parts) >= 3 and configured.parts[1] == "models":
        return config.get_models_dir() / Path(*configured.parts[2:])
    return config.get_models_dir() / configured.name


def upgrade_LLM_model(
    *,
    base_model_dir: Path,
    adapter_dir: Path,
    run_dir: Path,
    progress: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Path:
    """Fuse the trained LoRA, convert to Q4 GGUF, and replace the active local LLM model."""
    upgrade_dir = run_dir / "upgrade"
    fused_dir = upgrade_dir / "fused_model"
    f16_gguf = upgrade_dir / "MyVoiceTyping-1.5b-f16.gguf"
    q4_gguf = upgrade_dir / "MyVoiceTyping-1.5b-q4_k_m.gguf"
    upgrade_dir.mkdir(parents=True, exist_ok=True)

    convert_script = _llama_cpp_convert_script()
    quantize_bin = _llama_cpp_quantize_bin()
    if convert_script is None or quantize_bin is None:
        raise RuntimeError(
            "LoRA 已训练完成，但缺少 GGUF 转换工具。请安装 llama.cpp，并设置 "
            "LLAMA_CPP_CONVERT_SCRIPT=/path/to/convert_hf_to_gguf.py 与 "
            "LLAMA_CPP_QUANTIZE_BIN=/path/to/llama-quantize 后重试升级。"
        )

    if q4_gguf.exists() and not _is_complete_q4_gguf(q4_gguf):
        _emit(progress, phase="upgrade", message="检测到未完整的 Q4 GGUF，删除后重新生成…", percent=93)
        _remove_path_quietly(q4_gguf)

    if _is_complete_q4_gguf(q4_gguf):
        _emit(progress, phase="upgrade", message="检测到已生成的 Q4 GGUF，继续替换正式模型…", percent=97)
    else:
        if f16_gguf.exists():
            _emit(progress, phase="upgrade", message="检测到已生成的 F16 GGUF，继续量化…", percent=94)
        else:
            if fused_dir.exists():
                _emit(progress, phase="upgrade", message="检测到已合并模型，继续转换 GGUF…", percent=91)
            else:
                _emit(progress, phase="upgrade", message="正在合并 LoRA 到基线模型…", percent=88)
                fuse_cmd = [
                    _resolve_python_executable(),
                    "-m",
                    "src.model_train.mlx_lm_runner",
                    "fuse",
                    "--model",
                    str(base_model_dir),
                    "--adapter-path",
                    str(adapter_dir),
                    "--save-path",
                    str(fused_dir),
                ]
                _stream_subprocess(
                    fuse_cmd,
                    upgrade_dir / "fuse.log",
                    progress=progress,
                    phase="upgrade",
                    base_percent=88,
                    span_percent=4,
                )

            _emit(progress, phase="upgrade", message="正在转换为 F16 GGUF…", percent=92)
            convert_cmd = [
                _resolve_python_executable(),
                str(convert_script),
                str(fused_dir),
                "--outfile",
                str(f16_gguf),
                "--outtype",
                "f16",
            ]
            _stream_subprocess(
                convert_cmd,
                upgrade_dir / "convert_gguf.log",
                progress=progress,
                phase="upgrade",
                extra_env=_llama_cpp_convert_env(convert_script, upgrade_dir),
            )

        _emit(progress, phase="upgrade", message="正在量化为 Q4_K_M GGUF…", percent=96)
        quant_cmd = [str(quantize_bin), str(f16_gguf), str(q4_gguf), "Q4_K_M"]
        _stream_subprocess(quant_cmd, upgrade_dir / "quantize.log", progress=progress, phase="upgrade")

    if not _is_complete_q4_gguf(q4_gguf):
        actual_size = q4_gguf.stat().st_size if q4_gguf.exists() else 0
        raise RuntimeError(
            f"量化完成后 GGUF 文件不完整: {q4_gguf} "
            f"(actual={actual_size} bytes, expected>={MIN_QWEN15B_Q4_GGUF_BYTES} bytes)"
        )

    # F16 GGUF is only an intermediate file. Remove it before copying the
    # final Q4 model so low-disk machines can finish metadata updates.
    _remove_path_quietly(f16_gguf)

    target_dir = _resolve_llama_cpp_model_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = target_dir / f".backup_{time.strftime('%Y%m%d_%H%M%S')}"
    old_ggufs = sorted(target_dir.glob("*.gguf"))
    if old_ggufs:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for old_file in old_ggufs:
            shutil.move(str(old_file), str(backup_dir / old_file.name))

    target_file = target_dir / q4_gguf.name
    shutil.copy2(q4_gguf, target_file)
    _remove_path_quietly(fused_dir)

    metadata = {
        "upgraded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_run_dir": str(run_dir),
        "base_model": str(base_model_dir),
        "adapter_dir": str(adapter_dir),
        "backup_dir": str(backup_dir if old_ggufs else ""),
        "model_file": target_file.name,
    }
    (target_dir / "upgrade_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    config = get_config_manager()
    config.set("llama_cpp_model_file", target_file.name)
    _emit(progress, phase="upgrade", message=f"本地纠错模型已升级: {target_file}", percent=100)
    return target_file


def run_mlx_lora_auto_tune(
    progress: Optional[Callable[[dict[str, Any]], None]] = None,
    *,
    upgrade_model: bool = True,
) -> AutoTuneRunResult:
    config = get_config_manager()
    _emit(progress, phase="prepare", message="正在准备自动调优数据集…", percent=4, action="start")

    pending = _find_pending_upgrade_run() if upgrade_model else None
    if pending is not None:
        metadata = dict(pending["metadata"])
        run_dir = pending["run_dir"]
        adapter_dir = pending["adapter_dir"]
        base_model_dir = pending["base_model_dir"]
        dataset = pending["dataset"]
        params = pending["params"]
        _emit(
            progress,
            phase="resume",
            message=f"发现上次训练已完成，继续升级模型：{run_dir.name}",
            percent=12,
        )
        if not base_model_dir.exists():
            base_model_dir, _ = ensure_auto_tune_models(progress=progress)
        ensure_llama_cpp_tools(run_dir=run_dir, progress=progress)
        try:
            upgraded_model_path = upgrade_LLM_model(
                base_model_dir=base_model_dir,
                adapter_dir=adapter_dir,
                run_dir=run_dir,
                progress=progress,
            )
            metadata["upgraded_model_path"] = str(upgraded_model_path)
            metadata["upgrade_status"] = "success"
            metadata["upgrade_error"] = ""
            metadata["upgrade_finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            (pending["run_config_path"]).write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            metadata["upgrade_status"] = "failed"
            metadata["upgrade_error"] = str(e)
            (pending["run_config_path"]).write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            raise
        _emit(progress, phase="done", message=f"自动调优续跑完成: {upgraded_model_path}", percent=100)
        return AutoTuneRunResult(dataset, run_dir, adapter_dir, metadata.get("command") or [], params, upgraded_model_path)

    dataset = build_auto_tune_dataset()
    params = calculate_mlx_lora_params(dataset.total_count)
    _emit(progress, phase="prepare", message=f"训练集已生成：{dataset.train_count} 条训练，{dataset.valid_count} 条验证", percent=10)

    run_name = f"auto_{time.strftime('%Y%m%d_%H%M%S')}"
    run_dir = config.get_train_dir() / "runs" / run_name
    adapter_dir = run_dir / "adapters"
    run_dir.mkdir(parents=True, exist_ok=True)

    base_model_dir, resume_adapter = ensure_auto_tune_models(progress=progress)
    if upgrade_model:
        ensure_llama_cpp_tools(run_dir=run_dir, progress=progress)

    cmd = [
        _resolve_python_executable(),
        "-m",
        "src.model_train.mlx_lm_runner",
        "lora",
        "--model",
        str(base_model_dir),
        "--train",
        "--data",
        str(dataset.dataset_dir),
        "--mask-prompt",
        "--batch-size",
        str(params["batch_size"]),
        "--iters",
        str(params["iters"]),
        "--learning-rate",
        str(params["learning_rate"]),
        "--steps-per-report",
        str(params["steps_per_report"]),
        "--steps-per-eval",
        str(params["steps_per_eval"]),
        "--val-batches",
        str(params["val_batches"]),
        "--save-every",
        str(params["save_every"]),
        "--adapter-path",
        str(adapter_dir),
        "--max-seq-length",
        str(params["max_seq_length"]),
        "--num-layers",
        str(params["num_layers"]),
    ]
    if resume_adapter is not None:
        cmd.extend(["--resume-adapter-file", str(resume_adapter)])

    metadata = {
        "run_name": run_name,
        "dataset": dataset.__dict__ | {
            "dataset_dir": str(dataset.dataset_dir),
            "train_path": str(dataset.train_path),
            "valid_path": str(dataset.valid_path),
        },
        "params": params,
        "base_model": str(base_model_dir),
        "resume_adapter_file": str(resume_adapter or ""),
        "adapter_path": str(adapter_dir),
        "command": cmd,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (run_dir / "run_config.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    log_path = run_dir / "train.log"
    started = time.time()
    _emit(progress, phase="train", message=f"开始自动调优训练，共 {dataset.total_count} 条样本，iters={params['iters']}", percent=30)
    try:
        _stream_subprocess(
            cmd,
            log_path,
            progress=progress,
            phase="train",
            total_iters=int(params["iters"]),
            base_percent=30,
            span_percent=55,
        )
    except Exception as e:
        metadata["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        metadata["elapsed_seconds"] = round(time.time() - started, 2)
        metadata["status"] = "failed"
        metadata["error"] = str(e)
        (run_dir / "run_config.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        raise
    metadata["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    metadata["elapsed_seconds"] = round(time.time() - started, 2)
    metadata["status"] = "success"
    (run_dir / "run_config.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    upgraded_model_path = None
    if upgrade_model:
        try:
            upgraded_model_path = upgrade_LLM_model(
                base_model_dir=base_model_dir,
                adapter_dir=adapter_dir,
                run_dir=run_dir,
                progress=progress,
            )
            metadata["upgraded_model_path"] = str(upgraded_model_path)
            metadata["upgrade_status"] = "success"
        except Exception as e:
            metadata["upgrade_status"] = "failed"
            metadata["upgrade_error"] = str(e)
            (run_dir / "run_config.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            raise
        (run_dir / "run_config.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    _emit(progress, phase="done", message=f"自动调优完成: {adapter_dir}", percent=100)
    return AutoTuneRunResult(dataset, run_dir, adapter_dir, cmd, params, upgraded_model_path)
