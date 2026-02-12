"""
云端STT处理器 - 基于API接口
"""
import tempfile
import os
from ..components.audio_recorder import AudioRecorder


class CloudSTTProcessor:
    """
     * 初始化云端STT处理器
     * @param config 配置对象
    """
    def __init__(self, config):
        self.config = config
        self.client = self._init_client()

    def _init_client(self):
        """
         * 初始化API客户端
         * @returns 客户端对象
        """
        if self.config.STT_PROVIDER == 'openai_api':
            try:
                import openai
                openai.api_key = self.config.OPENAI_API_KEY
                return openai
            except ImportError:
                raise ImportError('请安装openai: pip install openai')
        else:
            raise ValueError(f'不支持的云端STT提供者: {self.config.STT_PROVIDER}')

    def transcribe(self, audio_frames):
        """
         * 转录音频
         * @param audio_frames 音频帧数据
         * @returns 转录文本
        """
        if self.config.STT_PROVIDER == 'openai_api':
            raw_text = self._transcribe_openai_api(audio_frames)
        else:
            raise ValueError(f'不支持的云端STT提供者: {self.config.STT_PROVIDER}')
        
        print(f'云端API转录文本: {raw_text}')
        return raw_text

    def _transcribe_openai_api(self, audio_frames):
        """
         * 使用OpenAI API转录
         * @param audio_frames 音频帧数据
         * @returns 转录文本
        """
        # 将音频帧保存为临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name

        try:
            # 保存音频数据到临时文件
            recorder = AudioRecorder()
            recorder.save_audio(audio_frames, temp_filename)

            # 使用OpenAI API转录
            with open(temp_filename, 'rb') as audio_file:
                transcript = self.client.Audio.transcribe(
                    'whisper-1',
                    audio_file
                )

            return transcript.text

        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)