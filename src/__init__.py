"""
MyVoiceTyping package init
"""
from .main import FlashInputApp
from typing import Any

__version__ = "1.0.0"
__author__ = "Rober"

__all__ = [
    "FlashInputApp"
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

    raise AttributeError(f"module 'src' has no attribute {name!r}")
