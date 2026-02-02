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
    def USE_REWRITE(self):
        return self._config_manager.get("use_rewrite", False)
    
    @USE_REWRITE.setter
    def USE_REWRITE(self, value):
        self._config_manager.set("use_rewrite", value)
    
    @property
    def REWRITE_MODE(self):
        return self._config_manager.get("rewrite_mode", "remote_llm")
    
    @REWRITE_MODE.setter
    def REWRITE_MODE(self, value):
        self._config_manager.set("rewrite_mode", value)
    
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


# 创建全局配置实例
config_instance = Config()


# 为了保持向后兼容性，我们仍然暴露这些属性作为类级别的常量
RECORD_HOTKEY = config_instance.RECORD_HOTKEY
SAMPLE_RATE = config_instance.SAMPLE_RATE
CHUNK_SIZE = config_instance.CHUNK_SIZE
FORMAT = config_instance.FORMAT
STT_PROVIDER = config_instance.STT_PROVIDER
OPENAI_API_KEY = config_instance.OPENAI_API_KEY
DEEPGRAM_API_KEY = config_instance.DEEPGRAM_API_KEY
TEMP_AUDIO_PATH = config_instance.TEMP_AUDIO_PATH
USE_REWRITE = config_instance.USE_REWRITE
REWRITE_MODE = config_instance.REWRITE_MODE
OLLAMA_MODEL = config_instance.OLLAMA_MODEL
API_KEY = config_instance.API_KEY
BASE_URL = config_instance.BASE_URL
MODEL_NAME = config_instance.MODEL_NAME
FUNASR_DEVICE = config_instance.FUNASR_DEVICE
REMOTE_LLM_MODELS = config_instance.REMOTE_LLM_MODELS