"""
语音转文字处理器
"""
from datetime import datetime
from pathlib import Path

from ..components.config_manager import get_config_manager
from ..components.audio_recorder import AudioRecorder


class STTProcessor:
    def __init__(self):
        self.config = get_config_manager()  # 使用新的配置管理器
        self.provider = self._init_provider()
        self.last_audio_path: str | None = None

    def _init_provider(self):
        """根据配置初始化STT提供者"""
        stt_provider = self.config.get("STT_PROVIDER")
        if stt_provider == "openai_api":
            from .stt_cloud_processor import CloudSTTProcessor
            return CloudSTTProcessor(self.config)
        elif stt_provider == "funasr":
            from .stt_local_processor import LocalSTTProcessor
            return LocalSTTProcessor(self.config)
        else:
            raise ValueError(f"不支持的STT提供者: {stt_provider}")

    def transcribe(self, audio_frames):
        """
        /**
         * 转录音频（保持对外接口不变）。
         *
         * 新增行为：
         * 1) 先将音频帧落盘保存到 `data/audio/`，文件名使用“年月日时分秒”。
         * 2) 调用 `provider.transcribe()` 时同时传入：保存后的文件路径 + audio_frames。
         *
         * @param audio_frames 录音得到的 PCM bytes（int16）
         * @returns 转录文本
         * @throws Exception 转录失败时抛出异常
         */
        """

        if audio_frames is None:
            return ""
            # raise ValueError("audio_frames 不能为空")
        if isinstance(audio_frames, str):
            raise TypeError(
                "audio_frames 应该是录音得到的 bytes（int16 PCM），不应传入文件路径字符串"
            )

        audio_dir = self.config.get_audio_dir()
        audio_dir.mkdir(parents=True, exist_ok=True)

        base_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_path = audio_dir / f"{base_name}.wav"

        # 同一秒多次调用时避免覆盖
        if wav_path.exists():
            suffix = 1
            while True:
                candidate = audio_dir / f"{base_name}_{suffix}.wav"
                if not candidate.exists():
                    wav_path = candidate
                    break
                suffix += 1

        try:
            recorder = AudioRecorder()
            recorder.save_audio(audio_frames, str(wav_path))
            self.last_audio_path = str(wav_path)
            print(f"✅ 已保存音频到本地: {wav_path}")
        except Exception as e:
            print(f"❌ 保存音频失败: {e}")
            raise

        try:
            raw_text = self.provider.transcribe(str(wav_path), audio_frames)
            return raw_text
        except Exception as e:
            print(f"❌ 转录失败: {e}")
            raise

    def warm_up(self) -> None:
        warm_up = getattr(self.provider, "warm_up", None)
        if callable(warm_up):
            warm_up()
