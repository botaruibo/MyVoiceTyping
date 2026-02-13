"""
本地STT处理器 - 基于FunASR模型
"""
import sys
from pathlib import Path
from funasr.utils.postprocess_utils import rich_transcription_postprocess


class LocalSTTProcessor:
    """
     * 初始化本地STT处理器
     * @param config 配置对象
    """
    def __init__(self, config):
        self.config = config
        self.model = self._init_stt_model()
        self.punc = self._init_punc_model()

    def _init_stt_model(self):
        """
        /**
         * 初始化 FunASR ONNX 模型。
         *
         * 优化点：
         * - 先检查本地模型是否已存在（`data/models/SenseVoiceSmall-onnx`）。
         * - 若本地存在 `model.onnx` + `model.onnx.data`，则直接加载，不再调用 `snapshot_download`。
         * - 若本地不存在，才回退到 `snapshot_download('iic/SenseVoiceSmall-onnx')`。
         *
         * @returns 模型对象
         */
        """
        try:
            from funasr_onnx import SenseVoiceSmall

            """/**
             * 查找本地 ONNX 模型目录。
             *
             * 说明：
             * - 运行在源码环境时：优先使用项目根目录下 `data/models/SenseVoiceSmall-onnx`。
             * - 打包环境时：可能存在 `_MEIPASS`、Resources 等候选目录。
             */"""
            bundle_root_candidates = []
            if hasattr(sys, "_MEIPASS"):
                bundle_root_candidates.append(Path(sys._MEIPASS))

            exe_path = Path(sys.executable).resolve()
            exe_dir = exe_path.parent
            contents_dir = exe_path.parent.parent
            bundle_root_candidates.extend(
                [
                    exe_dir,
                    contents_dir,
                    contents_dir / "Frameworks",
                    contents_dir / "Resources",
                ]
            )

            # 项目根目录（src/core -> src -> project_root）
            bundle_root_candidates.append(Path(__file__).resolve().parents[2])

            required_files = ["model_quant.onnx", "config.yaml"]
            local_model_path = None
            for bundle_root in bundle_root_candidates:
                model_path = bundle_root / "data" / "models" / "SenseVoiceSmall-onnx"
                if not model_path.exists():
                    continue
                if all((model_path / f).exists() for f in required_files):
                    local_model_path = str(model_path)
                    break

            if local_model_path is not None:
                print(f"✅ 检测到本地 ONNX 模型，直接加载: {local_model_path}")
                model = SenseVoiceSmall(local_model_path, batch_size=1, quantize=True)
                print("✅ 本地 ONNX 模型加载成功")
                return model

            print(
                "⚠️ 未检测到本地 ONNX 模型文件（model.onnx/model.onnx.data），将尝试从 ModelScope 下载: iic/SenseVoiceSmall-onnx"
            )

            from modelscope import snapshot_download

            model_dir = snapshot_download("iic/SenseVoiceSmall-onnx")
            model = SenseVoiceSmall(model_dir,
                                    batch_size=1,
                                    quantize=False,
                                    postprocess=True)
            print("✅ ONNX 模型下载并加载成功")
            return model

        except ImportError as e:
            raise ImportError(f"请安装所需依赖: pip install funasr onnxruntime: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"本地模型文件缺失: {e}")
        except Exception as e:
            raise Exception(f"初始化本地ONNX模型失败: {e}")

    def _init_punc_model(self):
        """
        /**
         * 初始化标点模型。
         *
         * 优化点：
         * - 先检查本地模型是否已存在（`data/models/punc_ct-transformer_zh-cn-common-vocab272727-onnx`）。
         * - 若本地存在 ONNX 模型文件（`model.onnx` 或 `model_quant.onnx`）以及 `config.yaml`、`tokens.json`，
         *   则直接加载，不再调用 `snapshot_download`。
         * - 若本地不存在，才回退到 `snapshot_download('iic/punc_ct-transformer_zh-cn-common-vocab272727-onnx')`。
         *
         * @returns 模型对象
         */
        """
        try:
            from funasr_onnx import CT_Transformer
        except Exception as e:
            raise ImportError(f"无法导入 funasr_onnx.CT_Transformer: {e}")

        """/**
         * 查找本地标点模型目录：兼容源码运行/打包运行。
         */"""
        bundle_root_candidates = []
        if hasattr(sys, "_MEIPASS"):
            bundle_root_candidates.append(Path(sys._MEIPASS))

        exe_path = Path(sys.executable).resolve()
        exe_dir = exe_path.parent
        contents_dir = exe_path.parent.parent
        bundle_root_candidates.extend(
            [
                exe_dir,
                contents_dir,
                contents_dir / "Frameworks",
                contents_dir / "Resources",
            ]
        )
        bundle_root_candidates.append(Path(__file__).resolve().parents[2])

        local_dir = None
        quantize = True

        for bundle_root in bundle_root_candidates:
            model_dir = bundle_root / "data" / "models" / "punc_ct-transformer_zh-cn-common-vocab272727-onnx"
            if not model_dir.exists():
                continue

            config_ok = (model_dir / "config.yaml").exists()
            tokens_ok = (model_dir / "tokens.json").exists()
            model_onnx = model_dir / "model.onnx"
            model_quant_onnx = model_dir / "model_quant.onnx"

            if not (config_ok and tokens_ok):
                continue

            if model_onnx.exists():
                local_dir = model_dir
                quantize = False
                break
            if model_quant_onnx.exists():
                local_dir = model_dir
                quantize = True
                break

        if local_dir is not None:
            print(f"✅ 检测到本地标点模型，直接加载: {local_dir}")
            return CT_Transformer(str(local_dir), quantize=quantize, device_id=-1)

        print(
            "⚠️ 未检测到本地标点模型，将尝试从 ModelScope 下载: iic/punc_ct-transformer_zh-cn-common-vocab272727-onnx"
        )

        from modelscope import snapshot_download

        punc_model_dir = snapshot_download("iic/punc_ct-transformer_zh-cn-common-vocab272727-onnx")
        punc_model_dir_path = Path(punc_model_dir)

        if (punc_model_dir_path / "model.onnx").exists():
            quantize = False
        elif (punc_model_dir_path / "model_quant.onnx").exists():
            quantize = True
        else:
            raise FileNotFoundError(
                "标点模型目录中未找到 `model.onnx` 或 `model_quant.onnx`："
                f"\n- model_dir: {punc_model_dir_path}"
            )

        return CT_Transformer(str(punc_model_dir_path), quantize=quantize, device_id=-1)

        # 加载标点模型（支持中英）
        punc_model = CT_Transformer(punc_model_dir,
                                    quantize=True,
                                    device_id=-1)
        return punc_model


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

    # def extract_text_from_sensevoice(self, raw_output) -> str:
    #     """
    #     /**
    #      * 从 SenseVoice 输出中提取“真正的识别文本”。
    #      *
    #      * SenseVoice 的 decode 结果可能包含控制 token，例如：
    #      * - `<|zh|>` 语言标签
    #      * - `<|NEUTRAL|>` 情绪/风格标签
    #      * - `<|Speech|>` 任务类型标签
    #      * - `<|woitn|>` 文本归一化标签
    #      *
    #      * 目标：
    #      * - 移除所有 `<|...|>` 控制 token
    #      * - 对空白做归一化（去多余空格/换行）
    #      * - 处理常见“无语音”标记
    #      *
    #      * @param raw_output 模型原始输出（支持 `str` 或 `List[str]`）
    #      * @returns 清洗后的文本
    #      */
    #     """
    #     import re
    #
    #     if raw_output is None:
    #         return ""
    #
    #     # 兼容：如果传入的是列表，则拼接
    #     if isinstance(raw_output, list):
    #         raw_text = " ".join(str(x) for x in raw_output if x is not None)
    #     else:
    #         raw_text = str(raw_output)
    #
    #     if not raw_text:
    #         return ""
    #
    #     # 1) 移除所有 <|...|> 控制 token（非贪婪匹配）
    #     text = re.sub(r"<\|.*?\|>", "", raw_text)
    #
    #     # 2) 去掉常见的无语音标记（有些模型会直接输出 nospeech）
    #     text = re.sub(r"\bnospeech\b", "", text, flags=re.IGNORECASE)
    #
    #     # 3) 归一化空白：将连续空白压缩成一个空格
    #     text = re.sub(r"\s+", " ", text).strip()
    #
    #     return text

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

    from src.config import Config

    config = Config()
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