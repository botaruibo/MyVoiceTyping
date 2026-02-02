"""
PyInstaller runtime hook for FunASR.

结论（来自你的构建产物 `build/MyVoiceInput/PYZ-00.toc`）：`funasr` 其实已经被打进了 PYZ。
但是 FunASR 的模型注册在 frozen 环境里可能依赖“隐式 import / 自动发现”。

这个 hook 的目的：
- 固化关键模块的 import 顺序
- 避免因 PYZ/zipimport 导致注册逻辑没触发
- 尽量在缺少可选依赖（triton/onnx 等）时也不影响启动

它会在你的应用入口（`run.py`）之前执行。
"""

import importlib
import inspect
import os
import sys
from pathlib import Path


def _setup_modelscope_cache() -> None:
    if os.environ.get("MODELSCOPE_CACHE"):
        return

    candidates = [
        Path.home() / ".cache" / "modelscope",
        Path.home() / "cache" / "modelscope",
    ]
    cache_root = next((p for p in candidates if p.exists()), candidates[0])
    os.environ["MODELSCOPE_CACHE"] = str(cache_root)


def _patch_inspect_for_frozen_sources() -> None:
    """让 inspect 能在 frozen 环境下找到 .py 源码。"""
    orig_getsourcefile = inspect.getsourcefile

    def patched_getsourcefile(obj):
        filename = orig_getsourcefile(obj)
        if filename and not os.path.isabs(filename):
            roots: list[Path] = []
            if hasattr(sys, "_MEIPASS"):
                roots.append(Path(sys._MEIPASS))
            roots.append(Path(sys.executable).resolve().parent)

            for root in roots:
                candidate = root / filename
                if candidate.exists():
                    return str(candidate)
        return filename

    inspect.getsourcefile = patched_getsourcefile
    print("[runtime_hook] patched inspect.getsourcefile for frozen environment")


def _patch_torchscript_for_frozen() -> None:
    """在 PyInstaller/frozen 环境下，TorchScript 可能因拿不到源码而报错。"""
    try:
        import torch

        orig_script = torch.jit.script

        def safe_script(obj, *args, **kwargs):
            try:
                return orig_script(obj, *args, **kwargs)
            except Exception as e:
                msg = str(e)
                if (
                    "could not get source code" in msg
                    or "TorchScript requires source access" in msg
                    or "Can't get source for" in msg
                ):
                    return obj
                raise

        torch.jit.script = safe_script

        try:
            import torch.jit._script
            torch.jit._script.script = safe_script
        except Exception:
            pass

        print("[runtime_hook] patched torch.jit.script for frozen environment")
    except Exception as e:
        print(f"[runtime_hook] torchscript patch skipped: {e}")


def _try_import(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        print(f"[runtime_hook] imported: {module_name}")
        return True
    except Exception as e:
        print(f"[runtime_hook] import failed: {module_name} ({e})")
        return False


def _funasr_source_root():
    """返回发行包里 funasr 源码目录（我们已通过 spec 把 .py 作为 datas 打包进来）。"""
    roots = []
    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))
    roots.append(Path(sys.executable).resolve().parent)

    for root in roots:
        candidate = root / "funasr"
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _module_name_from_py_file(funasr_root: Path, py_file: Path) -> str:
    rel = py_file.relative_to(funasr_root)
    parts = list(rel.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(["funasr", *parts])

# --------------------
# Registration index
# --------------------
# 性能优化（1）：只扫描一次 funasr 源码，构建 (table_name, class_name) -> [module...] 的索引。
# 性能优化（2）：仅在“确实检测到注册缺失”时才构建索引；正常情况下不会额外扫描。

_REGISTRATION_INDEX = None

def _iter_funasr_py_files(funasr_root: Path):
    """扫描 funasr 源码一次，构建 (table_name, class_name) -> [module_name...] 索引。"""

    funasr_root = _funasr_source_root()
    if funasr_root is None:
        return {}

    import re

    # 匹配：tables.register("xxx", "yyy") 以及单引号/空格等变体
    pat = re.compile(
        r"tables\.register\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)"
    )

    index = {}

    for py_file in funasr_root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        module_name = None

        for m in pat.finditer(text):
            table_name = m.group(1)
            class_name = m.group(2)

            if module_name is None:
                module_name = _module_name_from_py_file(funasr_root, py_file)
                if not module_name:
                    break

            key = (table_name, class_name)
            bucket = index.get(key)
            if bucket is None:
                bucket = set()
                index[key] = bucket
            bucket.add(module_name)

    return {k: sorted(v) for k, v in index.items()}


def _build_registration_index():
    """扫描 funasr 源码一次，构建 (table_name, class_name) -> [module_name...] 索引。"""

    funasr_root = _funasr_source_root()
    if funasr_root is None:
        return {}

    import re

    # 匹配：tables.register("xxx", "yyy") 以及单引号/空格等变体
    pat = re.compile(
        r"tables\.register\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)"
    )

    index = {}

    for py_file in funasr_root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        module_name = None

        for m in pat.finditer(text):
            table_name = m.group(1)
            class_name = m.group(2)

            if module_name is None:
                module_name = _module_name_from_py_file(funasr_root, py_file)
                if not module_name:
                    break

            key = (table_name, class_name)
            bucket = index.get(key)
            if bucket is None:
                bucket = set()
                index[key] = bucket
            bucket.add(module_name)

    return {k: sorted(v) for k, v in index.items()}


def _get_registration_index():
    global _REGISTRATION_INDEX
    if _REGISTRATION_INDEX is None:
        _REGISTRATION_INDEX = _build_registration_index()
        print(f"[runtime_hook] built funasr registration index: {len(_REGISTRATION_INDEX)} entries")
    return _REGISTRATION_INDEX


def _find_registering_modules(table_name: str, class_name: str) -> list:
    """在 funasr 源码里找谁注册了 (table_name, class_name)。

    优化点：只扫描一次源码，后续查表 O(1)。
    """
    index = _get_registration_index()
    return index.get((table_name, class_name), [])


def _ensure_registered(table_name: str, class_name: str) -> bool:
    """确保 funasr.register.tables.<table_name>[class_name] 已存在；必要时自动定位并 import。"""
    try:
        from funasr.register import tables
    except Exception as e:
        print(f"[runtime_hook] cannot import funasr.register.tables: {e}")
        return False

    table = getattr(tables, table_name, None)
    if not isinstance(table, dict):
        print(f"[runtime_hook] tables.{table_name} not found or not a dict")
        return False

    if table.get(class_name) is not None:
        return True

    candidates = _find_registering_modules(table_name, class_name)
    if candidates:
        print(f"[runtime_hook] {class_name} missing in {table_name}; candidates: {candidates}")

    for mod in candidates:
        _try_import(mod)
        if table.get(class_name) is not None:
            return True

    print(f"[runtime_hook] still missing: tables.{table_name}[{class_name}] after auto-import")
    return False


def _audit_and_fix_from_model_configs() -> None:
    """从离线模型 config.yaml 推导需要的注册项，并自动补齐。"""
    try:
        import yaml
    except Exception as e:
        print(f"[runtime_hook] yaml not available, skip config audit: {e}")
        return

    roots = []
    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))
    roots.append(Path(sys.executable).resolve().parent)

    models_root = None
    for root in roots:
        candidate = root / "data" / "models"
        if candidate.exists():
            models_root = candidate
            break

    if models_root is None:
        print("[runtime_hook] cannot find bundled data/models, skip config audit")
        return

    field_to_table = {
        "model": "model_classes",
        "encoder": "encoder_classes",
        "frontend": "frontend_classes",
        "tokenizer": "tokenizer_classes",
        "specaug": "specaug_classes",
    }

    for cfg_path in models_root.rglob("config.yaml"):
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"[runtime_hook] failed to parse yaml: {cfg_path} ({e})")
            continue

        for field, table_name in field_to_table.items():
            val = cfg.get(field)
            if isinstance(val, str) and val.strip():
                ok = _ensure_registered(table_name, val.strip())
                if not ok:
                    print(
                        f"[runtime_hook] missing registration: field={field} value={val} "
                        f"table={table_name} (from {cfg_path})"
                    )


def _force_funasr_registration_imports() -> None:
    # 先 import 你当前项目确定会用到的核心模块（快）
    modules = [
        "funasr",
        "funasr.register",
        "funasr.auto.auto_model",
        "funasr.models.sense_voice",
        "funasr.models.sense_voice.model",
        "funasr.models.fsmn_vad_streaming",
        "funasr.models.fsmn_vad_streaming.model",
        "funasr.models.fsmn_vad_streaming.encoder",
        "funasr.frontends.wav_frontend",
        "funasr.tokenizer.sentencepiece_tokenizer",
        "funasr.models.specaug.specaug",
        "funasr.models.specaug.mask_along_axis",
        "funasr.models.specaug.time_warp",
        "funasr.models.specaug.profileaug",
    ]

    for name in modules:
        _try_import(name)

    # 再基于离线模型 config.yaml 做一次“注册自检 + 自动补齐”
    _audit_and_fix_from_model_configs()


_setup_modelscope_cache()
_patch_inspect_for_frozen_sources()
_patch_torchscript_for_frozen()
_force_funasr_registration_imports()