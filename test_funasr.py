"""
FunASR 测试脚本 - 识别 data/output0.wav 文件
"""
import os, sys
from pathlib import Path
from funasr.utils.postprocess_utils import rich_transcription_postprocess

from langchain_openai import ChatOpenAI
audio_file = "test_data/output8.wav"

def test_whisiper_pytorch():
    from funasr import AutoModel
    model = AutoModel(
        model="iic/speech_whisper-small_asr_english",
        device="cpu",  # 或 "cuda"
    )

    # 转录
    for i in range(8):
        filename = "test_data/output" + str(i) + ".wav"

        result = model.generate(filename)
        print(result[0]["text"])

def test_funasr_onnx_recognize():
    from funasr_onnx import CT_Transformer
    from funasr_onnx import SenseVoiceSmall

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
    bundle_root_candidates.append(Path(__file__).resolve().parents[0])

    required_files = ["model_quant.onnx", "config.yaml"]
    local_model_path = None
    for bundle_root in bundle_root_candidates:
        model_path = bundle_root / "data" / "models" / "SenseVoiceSmall-onnx"
        if not model_path.exists():
            continue
        if all((model_path / f).exists() for f in required_files):
            local_model_path = str(model_path)
            break

    # if local_model_path is not None:
    #     print(f"✅ 检测到本地 ONNX 模型，直接加载: {local_model_path}")
    model = SenseVoiceSmall(str(local_model_path), batch_size=1, quantize=True)


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
    bundle_root_candidates.append(Path(__file__).resolve().parents[0])

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

    # if local_dir is not None:
    #     print(f"✅ 检测到本地标点模型，直接加载: {local_dir}")
    punc_model = CT_Transformer(str(local_dir), quantize=quantize, device_id=-1)

    tt = str(audio_file)
    rst = model(tt)
    print(f"本地模型转录文本: {rst}")
    raw_text = rich_transcription_postprocess(rst[0])
    print(f"本地模型转录文本: {raw_text}")
    # 对转录文本进行标点恢复
    punctuated_text = punc_model(raw_text)
    print(f"onnx=====识别结果: {punctuated_text[0]}")


def test_funasr_recognize():
    """测试FunASR识别指定音频文件"""
    try:
        from funasr import AutoModel

        # 检查音频文件是否存在
        if not os.path.exists(audio_file):
            print(f"音频文件不存在: {audio_file}")
            return

        # 初始化FunASR模型
        model_dir = "iic/SenseVoiceSmall"
        model = AutoModel(
            model=model_dir,
            # vad_model="fsmn-vad",
            # vad_kwargs={"max_single_segment_time": 30000},  # 最大分段时间
            device="cpu",
        )

        # 使用FunASR模型进行识别
        res = model.generate(
            input=audio_file,           # 输入音频文件路径
            language="auto",            # 自动检测语言（支持中文、英文、粤语等）
            use_itn=True,               # 启用反向文本标准化，将数字、符号等转换为标准格式
            # chunk_size=10,              # 分块大小，控制音频分段处理的时长
            # mode="2pass",               # 使用两遍解码模式，提高识别准确率
        )

        # 检查识别结果是否为空
        if res is None or len(res) == 0:
            print("FunASR识别结果为空")
            return None

        print(res)
        #后处理结果
        text = rich_transcription_postprocess(res[0]["text"])
        print(f"pytorch==识别结果: {text}")

        return text
    except ImportError:
        print("请安装funasr: pip install funasr modelscope torchaudio")
        return None
    except Exception as e:
        print(f"FunASR识别出错: {e}")
        return None

def test_funasr_export_onnx():
    """测试FunASR识别指定音频文件"""
    try:
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        # 检查音频文件是否存在
        if not os.path.exists(audio_file):
            print(f"音频文件不存在: {audio_file}")
            return

        # 初始化FunASR模型
        model_dir = "iic/SenseVoiceSmall"
        model = AutoModel(
            model=model_dir,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},  # 最大分段时间
            device="cpu",
        )

        export_dir = Path(__file__).resolve().parent / "data" / "models" / "SenseVoiceSmall-onnx"
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            print(f"开始导出 ONNX 模型到: {export_dir}")
            exported_to = model.export(
                input=audio_file,
                type="onnx",
                output_dir=str(export_dir),
                opset_version=18,
                device="cpu",
                quantize=False,
            )
            print(f"✅ ONNX 导出完成，导出目录: {exported_to}")

            try:
                onnx_files = sorted(p.name for p in export_dir.glob("*.onnx"))
                print(f"导出目录下的 ONNX 文件: {onnx_files}")
            except Exception as e:
                print(f"⚠️ 列出 ONNX 文件失败（可忽略）: {e}")
        except Exception as e:
            print(f"❌ ONNX 导出失败: {e}")
            raise

        print(f"开始识别音频文件: {audio_file}")

        # 使用FunASR模型进行识别
        res = model.generate(
            input=audio_file,           # 输入音频文件路径
            language="auto",            # 自动检测语言（支持中文、英文、粤语等）
            use_itn=True,               # 启用反向文本标准化，将数字、符号等转换为标准格式
            # chunk_size=10,              # 分块大小，控制音频分段处理的时长
            # mode="2pass",               # 使用两遍解码模式，提高识别准确率
        )

        # 检查识别结果是否为空
        if res is None or len(res) == 0:
            print("FunASR识别结果为空")
            return None

        #后处理结果
        text = rich_transcription_postprocess(res[0]["text"])
        print(f"识别结果: {text}")

        return text

    except ImportError:
        print("请安装funasr: pip install funasr modelscope torchaudio")
        return None
    except Exception as e:
        print(f"FunASR识别出错: {e}")
        return None

def test_llm():
    from src.core.text_rewrite import Rewrite
    rewriter = Rewrite()
    raw_text = "你好，我想购买一个商品括号占时。"
    result = rewriter.rewrite(raw_text)
    print(result)

if __name__ == '__main__':

    # test_funasr()
    # test_funasr_recognize()
    # test_funasr_onnx_recognize()
    # test_whisiper_pytorch()
    test_llm()