"""
配置管理模块 - 使用本地配置文件存储
"""
import os
from pathlib import Path
from .utils.config_manager import ConfigManager


class Config:
    """
    配置类，使用ConfigManager从本地文件加载和保存配置
    """
    
    def __init__(self):
        self._config_manager = ConfigManager()
    
    @property
    def RECORD_HOTKEY(self):
        return self._config_manager.get("record_hotkey", "<alt_r>")
    
    @RECORD_HOTKEY.setter
    def RECORD_HOTKEY(self, value):
        self._config_manager.set("record_hotkey", value)
    
    @property
    def SAMPLE_RATE(self):
        return self._config_manager.get("sample_rate", 16000)
    
    @property
    def CHUNK_SIZE(self):
        return self._config_manager.get("chunk_size", 1024)
    
    @property
    def FORMAT(self):
        return self._config_manager.get("audio_format", "int16")
    
    @property
    def STT_PROVIDER(self):
        return self._config_manager.get("stt_provider", "funasr")
    
    @STT_PROVIDER.setter
    def STT_PROVIDER(self, value):
        self._config_manager.set("stt_provider", value)
    
    @property
    def OPENAI_API_KEY(self):
        return self._config_manager.get("openai_api_key", "")
    
    @property
    def DEEPGRAM_API_KEY(self):
        return self._config_manager.get("deepgram_api_key", "")
    
    @property
    def TEMP_AUDIO_PATH(self):
        return str(self._config_manager.get_temp_audio_path())
    
    @property
    def FORMAT_TEXT(self):
        return self._config_manager.get("format_text", False)
    
    @FORMAT_TEXT.setter
    def FORMAT_TEXT(self, value):
        self._config_manager.set("format_text", value)
    
    @property
    def LLM_TEXT_PROVIDER(self):
        return self._config_manager.get("llm_text_provider", "cloud_llm")

    @LLM_TEXT_PROVIDER.setter
    def LLM_TEXT_PROVIDER(self, value):
        self._config_manager.set("llm_text_provider", value)
    
    @property
    def OLLAMA_MODEL(self):
        return self._config_manager.get("ollama_model", "qwen3:8b")
    
    @OLLAMA_MODEL.setter
    def OLLAMA_MODEL(self, value):
        self._config_manager.set("ollama_model", value)
    
    @property
    def API_KEY(self):
        return self._config_manager.get("api_key", "")
    
    @API_KEY.setter
    def API_KEY(self, value):
        self._config_manager.set("api_key", value)
    
    @property
    def BASE_URL(self):
        return self._config_manager.get("base_url", "")
    
    @BASE_URL.setter
    def BASE_URL(self, value):
        self._config_manager.set("base_url", value)
    
    @property
    def MODEL_NAME(self):
        return self._config_manager.get("model_name", "moonshotai/Kimi-K2-Instruct-0905")
    
    @MODEL_NAME.setter
    def MODEL_NAME(self, value):
        self._config_manager.set("model_name", value)
    
    @property
    def FUNASR_DEVICE(self):
        return self._config_manager.get("funasr_device", "cpu")
    
    @FUNASR_DEVICE.setter
    def FUNASR_DEVICE(self, value):
        self._config_manager.set("funasr_device", value)
    
    @property
    def REMOTE_LLM_MODELS(self):
        return self._config_manager.get("remote_llm_models", [
            "moonshotai/Kimi-K2-Instruct-0905",
            "Qwen/Qwen3-30B-A3B-Instruct-2507"
        ])
    
    @REMOTE_LLM_MODELS.setter
    def REMOTE_LLM_MODELS(self, value):
        self._config_manager.set("remote_llm_models", value)
    
    def get_audio_dir(self):
        """获取音频文件目录"""
        return self._config_manager.get_audio_dir()
    
    def get_transcripts_dir(self):
        """获取转录文件目录"""
        return self._config_manager.get_transcripts_dir()
    
    def get_models_dir(self):
        """获取模型文件目录"""
        return self._config_manager.get_models_dir()
    
    def get_temp_audio_path(self):
        """获取临时音频文件路径"""
        return self._config_manager.get_temp_audio_path()
    
    @property
    def MUTE_SPEAKER(self) -> bool:
        """是否在录音期间静音系统外放。
    
        /**
         * 配置项：`mute_speaker`
         *
         * 说明：
         * - `true`：在录音开始前静音系统外放，录音结束后恢复原状态
         * - `false`：不做任何处理
         *
         * @returns {boolean} 是否启用录音期间静音外放
         */
        """
    
        return bool(self._config_manager.get("mute_speaker", False))
    
    @MUTE_SPEAKER.setter
    def MUTE_SPEAKER(self, value: bool) -> None:
        """设置是否在录音期间静音系统外放。
    
        /**
         * @param value 是否启用
         * @returns {void}
         */
        """
    
        self._config_manager.set("mute_speaker", bool(value))