"""
本地STT处理器 - 基于FunASR模型
"""
import os
import shutil
import sys
from pathlib import Path
from funasr.utils.postprocess_utils import rich_transcription_postprocess

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
        self.model = self._init_stt_model()
        self.punc = self._init_punc_model()

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
            enqueue_action('progress_start', None, {'title': '模型下载', 'label': f'正在下载 {local_name}...'})

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
                local_dir=str(target_dir)
            )
            print(f"✅ 模型 {local_name} 下载成功")

        except Exception as e:
            # 网络错误等会在这里被捕获
            print(f"❌ 模型下载异常: {e}")
            raise Exception(f"模型下载失败: {e}")
        finally:
            # 务必还原方法
            tqdm.tqdm.update = _orig_update
            if hasattr(tqdm, 'auto'):
                tqdm.auto.tqdm.update = _orig_update

            # 关闭进度条窗口
            enqueue_action('progress_end', None, None)

    def _download_and_load_model(self, model_id: str, local_name: str, model_cls, **kwargs):
        """
        通用的模型下载与加载函数
        """
        # 1. 确定模型目录
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

        print(f"✅ 加载模型: {target_dir}")

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
        except ImportError:
            raise ImportError("请安装 funasr_onnx")

        return self._download_and_load_model(
            # model_id="iic/SenseVoiceSmall-onnx",
            model_id="botaruibo/SenseVoiceSmall-onnx",
            local_name="SenseVoiceSmall-onnx",
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

        return self._download_and_load_model(
            model_id="botaruibo/punc_ct-onnx",
            local_name="punc_ct-onnx",
            model_cls=CT_Transformer,
            device_id=-1,
            # quantize 会自动检测
        )



    def transcribe(self, file_path: str, audio_frames=None):
        """
         * 转录音频
         * @param audio_frames 音频帧数据
         * @returns 转录文本
        """
        try:
            rst = self.model(file_path)
            print(f"本地模型转录文本: {rst}")
            raw_text = rich_transcription_postprocess(rst[0])
            print(f"本地模型转录文本: {raw_text}")
            if raw_text is None or len(raw_text.strip()) == 0:
                return ""
            # 对转录文本进行标点恢复
            punctuated_text = self.punc(raw_text)
            print(f"本地模型标点恢复文本: {punctuated_text[0]}")
            return punctuated_text[0]
        except Exception as e:
            raise


if __name__ == "__main__":
    """
    /**
     * 本地 STT Processor 简易测试入口。
     *
     * 说明：
     * - `LocalSTTProcessor.transcribe()` 的入参是录音得到的 `bytes`（int16 PCM），不是文件路径字符串。
     * - 这里将 `test_data/output0.wav` 读取为 `bytes` 后再调用转录，避免类型错误。
     */
    """
    from ..components.config_manager import get_config_manager

    config = get_config_manager()
    processor = LocalSTTProcessor(config)

    project_root = Path(__file__).resolve().parents[2]
    wav_path = project_root / "test_data" / "output0.wav"
    if not wav_path.exists():
        wav_path = project_root / "test_data" / "output1.wav"

    if not wav_path.exists():
        raise FileNotFoundError(
            "未找到测试音频文件，请确认存在："
            f"{project_root / 'test_data' / 'output0.wav'} 或 {project_root / 'test_data' / 'output1.wav'}"
        )

    print(f"开始读取测试音频: {wav_path}")

    """/**
     * funasr_onnx 的 `SenseVoiceSmall.__call__` 仅接受 [str, np.ndarray, list]。
     * 这里 `wav_path` 是 `Path`，需要显式转为 `str`。
     */"""

    try:
        result = processor.model(str(wav_path))
        print("✅ funasr_onnx 推理完成")
        print(result)
    except Exception as e:
        print(f"❌ funasr_onnx 推理失败: {e}")
        raise