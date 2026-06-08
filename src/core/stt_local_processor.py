"""
本地STT处理器 - 基于FunASR模型
"""
import os
import shutil
import sys
from pathlib import Path
import re
from difflib import SequenceMatcher
import numpy as np

try:
    from ..components.gui_tk import enqueue_action
except ImportError:
    # 兼容性处理：如果没有 event_bus，定义一个空函数防止报错
    def enqueue_action(*args, **kwargs):
        pass

def get_models_root() -> Path:
    """
    获取模型根目录
    - 开发时：工程项目根目录下 data/models
    - 安装应用后：应用根目录对象下的 data/models (通常位于 .app/Contents/Resources/data/models)
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后的运行环境
        exe_path = Path(sys.executable).resolve()
        # 假设结构为 .../MyApp.app/Contents/MacOS/MyApp
        # exe_path.parent -> MacOS
        # exe_path.parent.parent -> Contents
        return exe_path.parent.parent / "Resources" / "data" / "models"

    # 开发环境：当前文件在 src/core/stt_local_processor.py -> ... -> ProjectRoot
    return Path(__file__).resolve().parents[2] / "data" / "models"

class LocalSTTProcessor:
    """
     * 初始化本地STT处理器
     * @param config 配置对象
    """
    def __init__(self, config):
        self.config = config
        self._stt_model_id = "botaruibo/SenseVoiceSmall-onnx"
        self._punc_model_id = "botaruibo/punc_ct-onnx"
        self._download_model(model_id=self._stt_model_id)
        self._download_model(model_id=self._punc_model_id)
        self.model = self._init_stt_model()
        self.punc = self._init_punc_model()

    def _get_hotwords(self) -> list[str]:
        raw = self.config.get("funasr_hotwords", [])
        if isinstance(raw, str):
            parts = re.split(r"[,，\n\r\t ]+", raw)
        elif isinstance(raw, list):
            parts = raw
        else:
            parts = []

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
        """
        使用 tqdm hook 实现带 GUI 进度的下载
        通过直接修改 tqdm.tqdm.update 方法，确保补丁对所有已导入 tqdm 的模块生效
        """
        import tqdm
        import time

        # 记录原始方法以便恢复
        _orig_update = tqdm.tqdm.update
        _last_report_time = [0]  # 使用列表以便在闭包中修改

        def patched_update(self, n=1):
            # 执行原始更新
            res = _orig_update(self, n)

            try:
                now = time.time()
                # 限制上报频率 (每 100ms 一次)
                if now - _last_report_time[0] < 0.1:
                    # 如果不是最后一次更新，则跳过
                    if not (self.total and self.n >= self.total):
                        return

                _last_report_time[0] = now

                if self.total:
                    percentage = (self.n / self.total) * 100
                    desc = self.desc or "下载中..."
                    print(f"==进度上报: {percentage:.2f}% - {desc}")
                    enqueue_action('progress_update', None, {'progress': percentage, 'desc': desc})
                else:
                    # 未知总大小，仅更新描述
                    enqueue_action('progress_update', None, {'progress': -1, 'desc': self.desc or "正在下载..."})
            except Exception as e:
                print(f"⚠️ 进度上报失败: {e}")

            return res

        try:
            print(f"⬇️ [GUI] 开始下载: {model_id}")
            # 发送开始信号
            enqueue_action('progress_start', None, {'title': '模型初始化下载', 'label': f'正在下载 {local_name}...'})

            # 应用补丁：直接修改类方法，这比替换类更彻底
            tqdm.tqdm.update = patched_update
            # 同时确保 auto 模块也指向同一个类（通常已经是这样了）
            if hasattr(tqdm, 'auto'):
                tqdm.auto.tqdm.update = patched_update

            # 确保父目录存在
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # 延迟加载 modelscope 确保补丁已就绪
            from modelscope import snapshot_download

            # 开始下载
            snapshot_download(
                model_id,
                local_dir=str(target_dir),
                revision='v1.0'
            )
            print(f"✅ 模型 {local_name} 下载成功")

        except Exception as e:
            # 网络错误等会在这里被捕获
            raise Exception(f"❌ 模型下载失败: {e}")
        finally:
            # 务必还原方法
            tqdm.tqdm.update = _orig_update
            if hasattr(tqdm, 'auto'):
                tqdm.auto.tqdm.update = _orig_update

            # 关闭进度条窗口
            enqueue_action('progress_end', None, None)

    def _download_model(self, model_id: str):
        """
        通用的模型下载与加载函数
        """
        # 1. 确定模型目录
        local_name = model_id.split("/")[-1]
        models_root = get_models_root()
        target_dir = models_root / local_name

        # 检查是否已存在（简单的检查规则：目录存在且包含关键配置文件）
        is_exist = False
        if target_dir.exists():
            if (target_dir / "config.yaml").exists() or (target_dir / "configuration.json").exists():
                # 进一步检查核心模型文件是否存在
                if (target_dir / "model.onnx").exists() or (target_dir / "model_quant.onnx").exists():
                    is_exist = True

        # 兼容性查找逻辑
        if not is_exist:
            bundle_root_candidates = []
            if hasattr(sys, "_MEIPASS"):
                bundle_root_candidates.append(Path(sys._MEIPASS))
            exe_path = Path(sys.executable).resolve()
            bundle_root_candidates.extend([
                exe_path.parent,
                exe_path.parent.parent,
                exe_path.parent.parent / "Resources"
            ])
            bundle_root_candidates.append(Path(__file__).resolve().parents[2])

            for root in bundle_root_candidates:
                candidate = root / "data" / "models" / local_name
                if candidate.exists() and (
                        (candidate / "config.yaml").exists() or (candidate / "configuration.json").exists()):
                    target_dir = candidate
                    is_exist = True
                    break

        # 2. 如果不存在，则下载
        if not is_exist:
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
        models_root = get_models_root()
        target_dir = models_root / local_name

        # 检查是否已存在（简单的检查规则：目录存在且包含关键配置文件）
        is_exist = False
        if target_dir.exists():
            if (target_dir / "config.yaml").exists() or (target_dir / "configuration.json").exists():
                # 进一步检查核心模型文件是否存在
                if (target_dir / "model.onnx").exists() or (target_dir / "model_quant.onnx").exists():
                    is_exist = True

        # 兼容性查找逻辑
        if not is_exist:
            bundle_root_candidates = []
            if hasattr(sys, "_MEIPASS"):
                bundle_root_candidates.append(Path(sys._MEIPASS))
            exe_path = Path(sys.executable).resolve()
            bundle_root_candidates.extend([
                exe_path.parent,
                exe_path.parent.parent,
                exe_path.parent.parent / "Resources"
            ])
            bundle_root_candidates.append(Path(__file__).resolve().parents[2])

            for root in bundle_root_candidates:
                candidate = root / "data" / "models" / local_name
                if candidate.exists() and (
                        (candidate / "config.yaml").exists() or (candidate / "configuration.json").exists()):
                    target_dir = candidate
                    is_exist = True
                    break

        # 2. 如果不存在，则下载
        if not is_exist:
            self._download_model(model_id, local_name)

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
            from funasr_onnx import SenseVoiceSmall
        except ImportError as e:
            raise ImportError(f"请安装 funasr_onnx: {e}")

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
            from funasr_onnx import CT_Transformer
        except ImportError:
            raise ImportError("请安装 funasr_onnx")

        return self._load_model(
            model_id=self._punc_model_id,
            model_cls=CT_Transformer,
            device_id=-1,
            # quantize 会自动检测
        )

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

            t_asr0 = _time.perf_counter()
            rst = self.model(file_path, hotword=hotword_text) if hotword_text else self.model(file_path)
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
        - 真实转录链路是 `librosa.load(file_path)` -> ndarray -> ONNX 推理。
          其中 `librosa.load` 首次调用会懒加载 numba/soundfile/audioread 等
          子库，单次代价 ~1s 左右，下次几乎 0ms。
        - 所以 warm_up 必须同时覆盖两条路径，否则用户首次录音仍要等 ~1s。

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

            # 1) 触发 librosa 子库懒加载（真实链路会先经过 librosa.load）。
            #    用一段极短的内存信号，强制走完 librosa 内部 import 路径。
            try:
                t0 = _time.perf_counter()
                import librosa  # 顶层 import 不算，关键是首次 .load 才加载子库
                # librosa.load 不接受 ndarray，我们用 librosa.resample 触发它
                # 的 numba/audio I/O 子模块加载（实测能等价于一次 .load 的预热）
                _ = librosa.resample(synth[:1600], orig_sr=16000, target_sr=16000)
                print(
                    f"[perf] stt:warm_up librosa "
                    f"{(_time.perf_counter() - t0) * 1000.0:.1f}ms"
                )
            except Exception as e:
                print(f"⚠️ librosa 预热失败（可忽略）: {e}")

            # 2) 触发 SenseVoice ONNX 算子图懒优化
            t0 = _time.perf_counter()
            _ = self.model(synth)
            print(
                f"[perf] stt:warm_up SenseVoice(synthetic 6s) "
                f"{(_time.perf_counter() - t0) * 1000.0:.1f}ms"
            )

            # 3) 触发标点模型首次推理
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
