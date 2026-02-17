"""
MyVoiceInput package init
"""
from .main import FlashInputApp
from .gui_tk import VoiceInputGUI
from .utils.config_manager import get_config_manager
from typing import Any

__version__ = "1.0.0"
__author__ = "Rober"

__all__ = [
    "FlashInputApp",
    "VoiceInputGUI", 
    "get_config_manager"
]

def __getattr__(name: str) -> Any:
    """/**
     * 惰性导入导出符号，避免包初始化产生副作用。
     *
     * @param {string} name - 属性名
     * @returns {any} 对应对象
     */"""

    if name == "FlashInputApp":
        from .main import FlashInputApp
        return FlashInputApp

    if name == "VoiceInputGUI":
        from .gui_tk import VoiceInputGUI
        return VoiceInputGUI

    if name == "get_config_manager":
        from .utils.config_manager import get_config_manager
        return get_config_manager

    raise AttributeError(f"module 'src' has no attribute {name!r}")