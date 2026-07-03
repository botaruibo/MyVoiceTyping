"""
本地STT处理器 - 基于FunASR模型
"""
import os
import shutil
import sys
import threading
from pathlib import Path
import re
from difflib import SequenceMatcher
import numpy as np
import soundfile as sf

try:
    from ..components.gui_tk import enqueue_action
except ImportError:
    # 兼容性处理：如果没有 event_bus，定义一个空函数防止报错
    def enqueue_action(*args, **kwargs):
        pass

STT_MODEL_ID = "botaruibo/SenseVoiceSmall-onnx"
PUNC_MODEL_ID = "botaruibo/punc_ct-onnx"
# PUNC_MODEL_ID = "iic/punc_ct-transformer_cn-en-common-vocab471067-large-onnx"


def _get_bundled_models_root() -> Path | None:
    candidates: list[Path] = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "data" / "models")
    if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
        exe_path = Path(sys.executable).resolve()
        contents_dir = exe_path.parent.parent
        candidates.extend([
            contents_dir / "Resources" / "data" / "models",
            contents_dir / "Frameworks" / "data" / "models",
        ])
    candidates.append(Path(__file__).resolve().parents[2] / "data" / "models")

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            if candidate.exists() and candidate.is_dir():
                return candidate
        except Exception:
            continue
    return None


def get_models_root() -> Path:
    """
    获取模型根目录
    - 开发时：工程项目根目录下 data/models。
    - 安装应用后：下载到用户可写的 Application Support，避免写入 .app 包内部。
    """
    if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
        return Path.home() / "Library" / "Application Support" / "MyVoiceTyping" / "data" / "models"

    # 开发环境：当前文件在 src/core/stt_local_processor.py -> ... -> ProjectRoot
    return Path(__file__).resolve().parents[2] / "data" / "models"


def _find_existing_model_dir(local_name: str) -> Path | None:
    for root in (get_models_root(), _get_bundled_models_root()):
        if root is None:
            continue
        candidate = root / local_name
        if _is_stt_model_present(candidate):
            return candidate
    return None


def download_model_with_progress(model_id, target_dir, local_name, revision='v1.0'):
    """
    通用模型下载（带 GUI 进度），供 STT 与文本纠错等模块复用。

    使用 tqdm hook 实现带 GUI 进度的下载：直接修改 tqdm.tqdm.update 方法，
    确保补丁对所有已导入 tqdm 的模块生效。

    :param model_id: ModelScope 模型 id，例如 "botaruibo/xxx"
    :param target_dir: 下载目标目录 (Path)
    :param local_name: 用于进度展示的本地名称
    :param revision: ModelScope 版本号，默认 v1.0
    """
    import tqdm
    import time

    target_dir = Path(target_dir)
    stop_monitor = threading.Event()

    def _format_bytes(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024.0
        return f"{size} B"

    def _dir_snapshot() -> tuple[int, int]:
        total_size = 0
        total_files = 0
        if not target_dir.exists():
            return 0, 0
        for file_path in target_dir.rglob("*"):
            try:
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            except Exception:
                continue
        return total_files, total_size

    def _monitor_download_dir() -> None:
        last_size = -1
        last_files = -1
        while not stop_monitor.wait(1.0):
            files, size = _dir_snapshot()
            if files != last_files or size != last_size:
                last_files = files
                last_size = size
                desc = f"已写入 {_format_bytes(size)}，{files} 个文件"
                print(f"==下载目录监控: {local_name} {desc}")

    # 记录原始方法以便恢复
    _orig_update = tqdm.tqdm.update
    _last_report_time = [0]  # 使用列表以便在闭包中修改
    _min_determinate_bytes = 5 * 1024 * 1024

    def patched_update(self, n=1):
        res = _orig_update(self, n)
        try:
            now = time.time()
            # 限制上报频率 (每 100ms 一次)
            if now - _last_report_time[0] < 0.1:
                if not (self.total and self.n >= self.total):
                    return res
            _last_report_time[0] = now

            if self.total:
                desc = self.desc or "下载中..."
                # ModelScope 会同时为配置/README 等小文件创建 tqdm，它们会瞬间 100%，
                # 直接映射到主进度条会造成“20% -> 100% -> 25%”的闪烁。
                if self.total < _min_determinate_bytes:
                    enqueue_action('progress_update', None, {'progress': -1, 'desc': desc})
                    return res

                percentage = (self.n / self.total) * 100
                print(f"==进度上报: {percentage:.2f}% - {desc}")
                enqueue_action('progress_update', None, {'progress': percentage, 'desc': desc})
            else:
                enqueue_action('progress_update', None, {'progress': -1, 'desc': self.desc or "正在下载..."})
        except Exception as e:
            print(f"⚠️ 进度上报失败: {e}")
        return res

    try:
        print(f"⬇️ [GUI] 开始下载: {model_id}")
        enqueue_action('progress_start', None, {'title': '模型初始化下载', 'label': f'正在下载 {local_name}...'})
        threading.Thread(target=_monitor_download_dir, daemon=True).start()

        # 应用补丁：直接修改类方法，这比替换类更彻底
        tqdm.tqdm.update = patched_update
        if hasattr(tqdm, 'auto'):
            tqdm.auto.tqdm.update = patched_update

        target_dir.parent.mkdir(parents=True, exist_ok=True)

        # 延迟加载 modelscope 确保补丁已就绪
        from modelscope.hub.snapshot_download import snapshot_download

        snapshot_download(
            model_id,
            local_dir=str(target_dir),
            revision=revision,
        )
        print(f"✅ 模型 {local_name} 下载成功")

    except Exception as e:
        raise Exception(f"❌ 模型下载失败: {e}")
    finally:
        stop_monitor.set()
        tqdm.tqdm.update = _orig_update
        if hasattr(tqdm, 'auto'):
            tqdm.auto.tqdm.update = _orig_update
        enqueue_action('progress_end', None, None)


def _is_stt_model_present(target_dir: Path) -> bool:
    """判断 STT/标点模型目录是否已下载（含配置与核心 onnx 文件）。"""
    if not target_dir.exists():
        return False
    has_config = (target_dir / "config.yaml").exists() or (target_dir / "configuration.json").exists()
    has_model = (target_dir / "model.onnx").exists() or (target_dir / "model_quant.onnx").exists()
    return has_config and has_model


def is_model_downloaded(model_id: str) -> bool:
    """检查指定 STT/标点模型是否已存在于本地或打包目录中（不触发下载）。"""
    local_name = model_id.split("/")[-1]
    return _find_existing_model_dir(local_name) is not None


def ensure_model_files(model_id: str) -> None:
    """检查并按需下载 STT/标点模型文件（仅下载，不加载到内存）。

    与 LocalSTTProcessor 的加载逻辑共用同一套存在性判定与目录修复，
    供应用启动阶段集中预下载使用。
    """
    local_name = model_id.split("/")[-1]
    target_dir = _find_existing_model_dir(local_name)
    is_exist = target_dir is not None

    if not is_exist:
        target_dir = get_models_root() / local_name
        print(f"⬇️ 未检测到本地模型，开始下载: {model_id} -> {target_dir}")
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            download_model_with_progress(model_id, target_dir, local_name, revision='v1.0')
            print(f"✅ 模型 {local_name} 下载成功，正在整理文件结构...")
        except Exception as e:
            raise Exception(f"模型下载失败: {e}")

    # 目录结构修复：确保关键文件在 target_dir 根目录下
    try:
        for root, dirs, files in os.walk(str(target_dir)):
            current_root = Path(root)
            if current_root == target_dir:
                continue
            for file in files:
                if file.endswith(('.onnx', '.json', '.yaml', '.txt', '.bin', '.model')):
                    src_path = current_root / file
                    dst_path = target_dir / file
                    if not dst_path.exists():
                        print(f"📂 [目录修复] 移动 {file} -> {target_dir}")
                        shutil.move(str(src_path), str(dst_path))
        for root, dirs, files in os.walk(str(target_dir), topdown=False):
            for d in dirs:
                d_path = Path(root) / d
                try:
                    if not any(d_path.iterdir()):
                        d_path.rmdir()
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ 目录结构检查警告: {e}")


class LocalSTTProcessor:
    """
     * 初始化本地STT处理器
     * @param config 配置对象
    """
    def __init__(self, config):
        self.config = config
        self._stt_model_id = STT_MODEL_ID
        self._punc_model_id = PUNC_MODEL_ID
        self._download_model(model_id=self._stt_model_id)
        self._download_model(model_id=self._punc_model_id)
        self.model = self._init_stt_model()
        self.punc = self._init_punc_model()

    def _get_hotwords(self) -> list[str]:
        if hasattr(self.config, "get_funasr_hotwords"):
            return self.config.get_funasr_hotwords()

        raw = self.config.get("funasr_hotword_dictionaries", [])
        parts: list[str] = []
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            for dictionary_path in raw:
                path = Path(str(dictionary_path)).expanduser()
                if not path.is_absolute():
                    path = Path(__file__).resolve().parents[2] / path
                if not path.exists():
                    continue
                parts.extend(path.read_text(encoding="utf-8", errors="ignore").splitlines())

        hotwords: list[str] = []
        seen: set[str] = set()
        for item in parts:
            word = str(item or "").strip()
            if not word or word in seen:
                continue
            seen.add(word)
            hotwords.append(word)
        return hotwords

    def _apply_hotword_bias(self, text: str, hotwords: list[str]) -> str:
        """
        对当前 ONNX SenseVoice 路径做保守热词后处理。

        说明：
        - FunASR AutoModel 支持原生 hotword；当前 funasr_onnx SenseVoiceSmall
          不消费 hotword 参数，所以这里补一层高阈值近似替换。
        - 只替换与热词长度接近、相似度很高的连续片段，避免大范围误改。
        """
        if not text or not hotwords:
            return text

        result = text
        for word in sorted(hotwords, key=len, reverse=True):
            if not word or word in result:
                continue

            n = len(word)
            if n <= 1:
                continue

            best_score = 0.0
            best_span: tuple[int, int] | None = None
            min_len = n if n <= 4 else max(1, n - 1)
            max_len = n if n <= 4 else min(len(result), n + 2)

            for size in range(min_len, max_len + 1):
                for start in range(0, len(result) - size + 1):
                    candidate = result[start:start + size]
                    if not candidate.strip():
                        continue
                    if size == n and candidate[0] != word[0] and candidate[-1] != word[-1]:
                        continue
                    score = SequenceMatcher(None, candidate, word).ratio()
                    if size != n:
                        score -= 0.15
                    if score > best_score:
                        best_score = score
                        best_span = (start, start + size)

            threshold = 0.75 if n <= 4 else 0.72
            if best_span is not None and best_score >= threshold:
                start, end = best_span
                print(f"🔥 热词后处理: {result[start:end]} -> {word} (score={best_score:.2f})")
                result = result[:start] + word + result[end:]

        return result

    def _download_with_progress(self, model_id, target_dir, local_name):
        """实例方法保留以兼容旧调用，委托给模块级通用下载函数。"""
        download_model_with_progress(model_id, target_dir, local_name, revision='v1.0')

    def _download_model(self, model_id: str):
        """
        通用的模型下载与加载函数
        """
        # 1. 确定模型目录
        local_name = model_id.split("/")[-1]
        target_dir = _find_existing_model_dir(local_name)
        is_exist = target_dir is not None

        # 2. 如果不存在，则下载
        if not is_exist:
            target_dir = get_models_root() / local_name
            print(f"⬇️ 未检测到本地模型，开始下载: {model_id} -> {target_dir}")

            try:
                # 确保父目录存在
                target_dir.parent.mkdir(parents=True, exist_ok=True)

                self._download_with_progress(model_id, target_dir, local_name)

                print(f"✅ 模型 {local_name} 下载成功，正在整理文件结构...")

                # 刚下载完，执行清理逻辑（下文统一处理）

            except Exception as e:
                raise Exception(f"模型下载失败: {e}")

        # 3. 目录结构修复与加载
        # 无论是否刚下载，都尝试修复目录结构（解决 modelscope 下载到子目录或上次未完全修复的问题）
        # 确保关键文件 (.onnx, .model, .json, .yaml) 都在 target_dir 根目录下
        try:
            for root, dirs, files in os.walk(str(target_dir)):
                current_root = Path(root)
                if current_root == target_dir:
                    continue

                for file in files:
                    # 移动关键模型文件，增加 .model 后缀
                    if file.endswith(('.onnx', '.json', '.yaml', '.txt', '.bin', '.model')):
                        src_path = current_root / file
                        dst_path = target_dir / file

                        # 只有目标不存在时才移动，避免覆盖
                        if not dst_path.exists():
                            print(f"📂 [目录修复] 移动 {file} -> {target_dir}")
                            shutil.move(str(src_path), str(dst_path))

            # 尝试清理空的子目录
            for root, dirs, files in os.walk(str(target_dir), topdown=False):
                for d in dirs:
                    d_path = Path(root) / d
                    try:
                        if not any(d_path.iterdir()):
                            d_path.rmdir()
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ 目录结构检查警告: {e}")


    def _load_model(self, model_id: str, model_cls, **kwargs):
        """
        通用的模型下载与加载函数
        """
        # 1. 确定模型目录
        local_name = model_id.split("/")[-1]
        target_dir = _find_existing_model_dir(local_name)
        is_exist = target_dir is not None

        # 2. 如果不存在，则下载
        if not is_exist:
            self._download_model(model_id)
            target_dir = _find_existing_model_dir(local_name)
            if target_dir is None:
                raise FileNotFoundError(f"模型下载后仍未找到完整模型目录: {local_name}")

        # 自动检测量化配置
        if 'quantize' not in kwargs:
            is_quant = (target_dir / "model_quant.onnx").exists()
            kwargs['quantize'] = is_quant

        try:
            return model_cls(str(target_dir), **kwargs)
        except Exception as e:
            raise Exception(f"模型加载失败: {e}")

    def _init_stt_model(self):
        """
        初始化 FunASR ONNX STT 模型
        """
        try:
            from ..vendor.funasr_onnx import SenseVoiceSmall
        except ImportError as e:
            raise ImportError(f"请检查 vendored funasr_onnx 依赖是否完整: {e}")

        return self._load_model(
            model_id=self._stt_model_id,
            model_cls=SenseVoiceSmall,
            batch_size=1,
            # quantize 会自动检测
        )

    def _init_punc_model(self):
        """
        初始化标点模型
        """
        try:
            from ..vendor.funasr_onnx import CT_Transformer
        except ImportError:
            raise ImportError("请检查 vendored funasr_onnx 依赖是否完整")

        return self._load_model(
            model_id=self._punc_model_id,
            model_cls=CT_Transformer,
            device_id=-1,
            # quantize 会自动检测
        )

    def _load_recorded_audio(self, file_path: str) -> np.ndarray:
        """
        读取应用内录制的 16k WAV 音频，返回单声道 float32 ndarray。

        当前桌面应用只支持自身录制链路生成的 WAV：
        - sample rate 必须为 16000
        - 声道数必须为单声道，或可压平成单声道
        """
        audio_array, sample_rate = sf.read(file_path, dtype="float32", always_2d=False)

        if sample_rate != 16000:
            raise ValueError(f"仅支持 16k WAV，当前采样率: {sample_rate}")

        if isinstance(audio_array, np.ndarray) and audio_array.ndim == 2:
            if audio_array.shape[1] != 1:
                raise ValueError(f"仅支持单声道 WAV，当前声道数: {audio_array.shape[1]}")
            audio_array = audio_array[:, 0]

        audio_array = np.asarray(audio_array, dtype=np.float32)
        if audio_array.ndim != 1:
            raise ValueError(f"音频数据维度异常: {audio_array.shape}")

        return audio_array

    def rich_transcription_postprocess(self,text: str) -> str:
        """
        * 对 SenseVoiceSmall 的识别结果进行后处理
        * 主要是移除 <|zh|>, <|en|>, <|nospeech|>, <|HAPPY|> 等标签
        * @param text 原始识别文本
        * @returns 清理后的文本
        """
        if not text:
            return ""
        # 移除 <|...|> 格式的标签 (SenseVoice 的特殊标记)
        text = re.sub(r'<\|.*?\|>', '', text)
        # 移除两端空格
        return text.strip()

    def transcribe(self, file_path: str, audio_frames=None):
        """
         * 转录音频
         * @param audio_frames 音频帧数据
         * @returns 转录文本
        """
        import time as _time
        try:
            hotwords = self._get_hotwords()
            hotword_text = " ".join(hotwords)
            audio_array = self._load_recorded_audio(file_path)

            t_asr0 = _time.perf_counter()
            rst = self.model(audio_array, hotword=hotword_text) if hotword_text else self.model(audio_array)
            t_asr_ms = (_time.perf_counter() - t_asr0) * 1000.0
            print(f"[perf] stt: SenseVoice 推理: {t_asr_ms:.1f}ms")
            print(f"本地模型转录文本: {rst}")
            raw_text = self.rich_transcription_postprocess(rst[0])
            raw_text = self._apply_hotword_bias(raw_text, hotwords)
            print(f"本地模型转录文本: {raw_text}")
            if raw_text is None or len(raw_text.strip()) == 0:
                return ""
            if self.punc is None:
                print("⚠️标点模型未初始化，跳过标点恢复")
                return raw_text
            # 对转录文本进行标点恢复
            t_punc0 = _time.perf_counter()
            punctuated_text = self.punc(raw_text)
            t_punc_ms = (_time.perf_counter() - t_punc0) * 1000.0
            print(f"[perf] stt: 标点模型推理: {t_punc_ms:.1f}ms")
            final_text = self._apply_hotword_bias(punctuated_text[0], hotwords)
            print(f"本地模型标点恢复文本: {final_text}")
            return final_text
        except Exception as e:
            raise

    def warm_up(self) -> None:
        """
        预热 ONNX Runtime 首次推理路径，降低第一次真实录音的等待。

        关键背景（实测拆解）：
        - SenseVoice ONNX 是动态 shape，第一次拿到“真实长度 + 真实特征”
          的输入时，ORT 会触发算子图懒优化 / 内存重排，单次代价数百 ms ~ 数秒。
        - 当前真实转录链路是 `soundfile.read(file_path)` -> ndarray -> ONNX 推理。
          应用内录音固定写出 16k 单声道 wav，因此这里只需预热 ONNX 与标点模型，
          无需再为 librosa/numba 的懒加载单独预热。

        合成数据 vs 读固定文件的取舍：
        - 现场用 numpy 生成低幅高斯噪声：纯内存操作 < 1ms。
        - 读固定 wav 文件：~50KB，首次冷盘 I/O + WAV 解码大约 5~50ms，
          还要把样本文件随包发布、维护打包路径。
        - 合成数据零文件依赖、跨打包/沙盒环境最稳定，因此选合成数据。
        - 噪声而非纯零：纯零会让 fbank 走极端静音分支，可能跳过部分算子，
          导致预热不充分；低幅噪声更接近真实人声分布。

        预热长度：
        - 用户单次录音通常 2~15s。这里取 6s 覆盖最常见区间，让 ORT 在
          中等 shape 上完成图优化。
        """
        import time as _time
        try:
            print("🔥 开始预热 FunASR 本地模型...")

            # 6s 低幅高斯噪声（覆盖常见录音长度），固定 seed 便于复现
            rng = np.random.default_rng(0)
            synth = (rng.standard_normal(int(16000 * 6.0)) * 50.0).astype(np.float32)

            # 1) 触发 SenseVoice ONNX 算子图懒优化
            t0 = _time.perf_counter()
            _ = self.model(synth)
            print(
                f"[perf] stt:warm_up SenseVoice(synthetic 6s) "
                f"{(_time.perf_counter() - t0) * 1000.0:.1f}ms"
            )

            # 2) 触发标点模型首次推理
            if self.punc is not None:
                t0 = _time.perf_counter()
                _ = self.punc("今天我们一起来预热标点模型")
                print(
                    f"[perf] stt:warm_up CT-Transformer "
                    f"{(_time.perf_counter() - t0) * 1000.0:.1f}ms"
                )

            print("✅ FunASR 本地模型预热完成")
        except Exception as e:
            print(f"⚠️ FunASR 预热失败（不影响后续转写）: {e}")


if __name__ == "__main__":
    """
    /**
     * 本地 STT Processor 简易测试入口。
     *
     * 说明：
     * - 这里通过 data/audio 下的已有录音文件 mock 真实录音输入，
     *   验证“冷启动 -> warm_up -> 首次真实转录”这条链路的耗时分布。
     */
    """
    import time as _time
    from ..components.config_manager import get_config_manager

    config = get_config_manager()

    t0 = _time.perf_counter()
    processor = LocalSTTProcessor(config)
    print(f"[perf] init LocalSTTProcessor: {(_time.perf_counter() - t0):.2f}s")

    # 1) 预热（使用 data/audio 中已有真实音频）
    t0 = _time.perf_counter()
    processor.warm_up()
    print(f"[perf] warm_up total: {(_time.perf_counter() - t0):.2f}s")

    # 2) 模拟一次“真实录音 -> 转录”，看首次耗时是否被压下来
    project_root = Path(__file__).resolve().parents[2]
    audio_dir = project_root / "data" / "audio"
    test_dir = project_root / "test_data"

    pick_path = None
    for d in (audio_dir, test_dir):
        if d.exists():
            wavs = sorted(d.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
            if wavs:
                pick_path = str(wavs[0])
                break

    if pick_path is None:
        raise FileNotFoundError(f"未找到测试音频，请确认 {audio_dir} 或 {test_dir} 下有 .wav")

    print(f"开始 mock 真实转录: {pick_path}")
    t0 = _time.perf_counter()
    text = processor.transcribe(pick_path)
    print(f"[perf] transcribe(first real call after warm_up): {(_time.perf_counter() - t0):.2f}s")
    print(f"识别结果: {text}")
