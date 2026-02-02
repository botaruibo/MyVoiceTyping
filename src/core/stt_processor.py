"""
语音转文字处理器
"""
import tempfile
import os
import sys
import shutil
from pathlib import Path
from ..config import Config
from ..components.audio_recorder import AudioRecorder


class STTProcessor:
    def __init__(self):
        self.config = Config()  # 使用新的配置管理器
        self.provider = self._init_provider()

    def _init_provider(self):
        """根据配置初始化STT提供者"""
        if self.config.STT_PROVIDER == "openai_api":
            return self._init_openai_api()
        elif self.config.STT_PROVIDER == "funasr":
            return self._init_funasr()
        else:
            raise ValueError(f"不支持的STT提供者: {self.config.STT_PROVIDER}")

    def _init_openai_api(self):
        """初始化OpenAI API"""
        try:
            import openai
            openai.api_key = self.config.OPENAI_API_KEY
            return openai
        except ImportError:
            raise ImportError(
                "请安装openai: pip install openai"
            )

    def _init_funasr(self):
        """初始化FunASR（阿里听悟）

        打包后优先走离线：将随应用打包的模型文件拷贝到 ModelScope 默认缓存目录，
        再通过 model id (iic/SenseVoiceSmall) 初始化，避免联网下载/注册失败。
        """
        try:
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            device = self.config.FUNASR_DEVICE if hasattr(self.config, 'FUNASR_DEVICE') else "cpu"
            bundle_root_candidates = []
            if hasattr(sys, "_MEIPASS"):
                bundle_root_candidates.append(Path(sys._MEIPASS))

            exe_path = Path(sys.executable).resolve()
            exe_dir = exe_path.parent
            contents_dir = exe_dir.parent
            bundle_root_candidates.extend(
                [
                    exe_dir,
                    contents_dir,
                    contents_dir / "Frameworks",
                    contents_dir / "Resources",
                ]
            )

            bundle_root_candidates.append(Path(__file__).resolve().parents[2])

            bundle_root = next(
                (p for p in bundle_root_candidates if (p / "data").exists()),
                bundle_root_candidates[0],
            )

            bundled_model_dir = bundle_root / "data" / "models" / "SenseVoiceSmall"

            modelscope_cache_root = Path(
                os.environ.get("MODELSCOPE_CACHE", str(Path.home() / ".cache" / "modelscope"))
            ).expanduser()

            modelscope_target_dir = (
                modelscope_cache_root / "hub" / "models" / "iic" / "SenseVoiceSmall"
            )
            marker_files = [
                modelscope_target_dir / "configuration.json",
                modelscope_target_dir / "model.pt",
            ]

            try:
                if not bundled_model_dir.exists():
                    print(
                        f"⚠️ 未找到随应用打包的离线模型目录: {bundled_model_dir}（可能会触发联网下载）"
                    )
                else:
                    has_cached_model = all(p.exists() for p in marker_files)

                    if has_cached_model:
                        print(f"✅ 检测到本地模型缓存，跳过复制: {modelscope_target_dir}")
                    else:
                        modelscope_target_dir.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(bundled_model_dir, modelscope_target_dir, dirs_exist_ok=True)
                        print(f"✅ 已复制离线模型到缓存目录: {modelscope_target_dir}")
            except Exception as e:
                print(f"⚠️ 模型缓存准备失败（可能会触发联网下载）: {e}")

            # 完全离线：只允许使用本地缓存目录（必要时从 bundle 复制进来），不允许回退到模型ID联网下载。
            if all(p.exists() for p in marker_files):
                model_source = str(modelscope_target_dir)
            else:
                raise RuntimeError(
                    "SenseVoiceSmall 离线模型不可用（完全离线模式下禁止联网下载）。"
                    f"\n- bundled_model_dir: {bundled_model_dir}"
                    f"\n- modelscope_target_dir: {modelscope_target_dir}"
                    "\n请确认：打包时 `data/models/SenseVoiceSmall` 已包含并且运行时复制成功。"
                )

            # VAD：你之前写的 `iic/fsmn-vad` 在 ModelScope 上不存在（404），并且不会命中 FunASR 的 name_maps。
            # 正确的写法：
            # - 使用 shortcut：`fsmn-vad`（会映射到 `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`）
            # - 或直接使用本地缓存目录路径（离线包）
            vad_bundled_dir_candidates = [
                bundle_root / "data" / "models" / "speech_fsmn_vad_zh-cn-16k-common-pytorch",
                bundle_root / "data" / "models" / "fsmn-vad",
            ]
            vad_bundled_dir = next((p for p in vad_bundled_dir_candidates if p.exists()), None)

            vad_cache_dir = (
                Path.home()
                / ".cache"
                / "modelscope"
                / "hub"
                / "models"
                / "iic"
                / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
            )

            def _vad_cache_ready(p: Path) -> bool:
                if not p.exists():
                    return False
                if not (p / "configuration.json").exists():
                    return False
                return any(p.glob("*.pt"))

            try:
                if vad_bundled_dir is not None and not _vad_cache_ready(vad_cache_dir):
                    vad_cache_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(vad_bundled_dir, vad_cache_dir, dirs_exist_ok=True)
                    print(f"✅ 已复制离线VAD模型到缓存目录: {vad_cache_dir}")
            except Exception as e:
                print(f"⚠️ VAD模型缓存准备失败（可能会触发联网下载）: {e}")

            # 完全离线：只允许使用本地 VAD 目录路径；不允许用 shortcut/model id（会触发联网下载）。
            vad_source = str(vad_cache_dir) if _vad_cache_ready(vad_cache_dir) else None
            if vad_source is None:
                raise RuntimeError(
                    "VAD 离线模型不可用（完全离线模式下禁止联网下载）。"
                    f"\n- expected cache: {vad_cache_dir}"
                    f"\n- bundled candidates: {vad_bundled_dir_candidates}"
                    "\n请先把 VAD 模型放到 `data/models/speech_fsmn_vad_zh-cn-16k-common-pytorch/` 并重新打包。"
                )

            base_kwargs = dict(
                model=model_source,
                device=device,
                disable_update=True,
            )
            base_kwargs["vad_model"] = vad_source
            base_kwargs["vad_kwargs"] = {"max_single_segment_time": 30000}

            # 打包/离线场景：不要启用 trust_remote_code。
            try:
                print("初始化 FunASR 模型...")
                model = AutoModel(**base_kwargs, trust_remote_code=False)
                print("✅ FunASR 模型初始化成功")
            except TypeError as e:
                msg = str(e)
                if "trust_remote_code" in msg and (
                    "unexpected keyword argument" in msg
                    or "got an unexpected keyword argument" in msg
                ):
                    model = AutoModel(**base_kwargs)
                else:
                    raise
            except Exception as e:
                # VAD 下载/构建失败时允许降级：不启用 VAD 继续启动主模型
                msg = str(e)
                if "fsmn-vad" in msg or "speech_fsmn_vad" in msg or "VAD" in msg or "vad" in msg:
                    print(f"⚠️ VAD初始化失败，已降级为不启用VAD: {e}")
                    base_kwargs_no_vad = dict(base_kwargs)
                    base_kwargs_no_vad.pop("vad_model", None)
                    base_kwargs_no_vad.pop("vad_kwargs", None)
                    model = AutoModel(**base_kwargs_no_vad, trust_remote_code=False)
                else:
                    raise

            return model
        except ImportError:
            raise ImportError("请安装funasr: pip install funasr modelscope torchaudio")

    def transcribe(self, audio_frames):
        """转录音频"""
        if self.config.STT_PROVIDER == "openai_api":
            raw_text = self._transcribe_openai_api(audio_frames)
        elif self.config.STT_PROVIDER == "funasr":  # 添加阿里听悟转录支持
            raw_text = self._transcribe_funasr(audio_frames)
        else:
            raise ValueError(f"不支持的STT提供者: {self.config.STT_PROVIDER}")
        print(f"原始转录文本: {raw_text}")
        return raw_text

    def _transcribe_openai_api(self, audio_frames):
        """使用OpenAI API转录"""
        # 将音频帧保存为临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name

        try:
            # 保存音频数据到临时文件
            recorder = AudioRecorder()
            recorder.save_audio(audio_frames, temp_filename)

            # 使用OpenAI API转录
            with open(temp_filename, "rb") as audio_file:
                transcript = self.provider.Audio.transcribe(  # 修复：使用self.provider而不是openai
                    "whisper-1",
                    audio_file
                )

            return transcript.text

        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def _transcribe_funasr(self, audio_frames):
        """使用FunASR（阿里听悟）转录"""
        # 将音频帧保存为临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name

        try:
            # 保存音频数据到临时文件
            recorder = AudioRecorder()
            recorder.save_audio(audio_frames, temp_filename)

            # 使用已初始化的 FunASR 模型直接推理
            has_vad = bool(getattr(self.provider, "vad_model", None))

            res = self.provider.generate(
                input=temp_filename,
                language="auto",  # 自动检测语言
                use_itn=True,     # 启用文本归一化
                merge_vad=has_vad,  # 未启用 VAD 时不要强行 merge_vad
                merge_length_s=15,
                batch_size_s=60
            )
            # 后处理结果
            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            text = rich_transcription_postprocess(res[0]["text"])
            return text

        except ImportError:
            raise ImportError(
                "请安装funasr: pip install funasr modelscope torchaudio"
            )
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)