"""
MyVoiceInput package init
"""
from .main import FlashInputApp
from .gui_tk import VoiceInputGUI
from .utils.config_manager import get_config_manager

__version__ = "1.0.0"
__author__ = "Rober"

__all__ = [
    "FlashInputApp",
    "VoiceInputGUI", 
    "get_config_manager"
]