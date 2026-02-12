"""
MyVoiceInput package init
"""
from .main import FlashInputApp
from .gui_tk import VoiceInputGUI
from .config import Config

__version__ = "1.0.0"
__author__ = "Rober"

__all__ = [
    "FlashInputApp",
    "VoiceInputGUI", 
    "Config"
]