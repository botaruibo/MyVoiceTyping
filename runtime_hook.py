import os
import sys
import inspect
from pathlib import Path

def _setup_modelscope_cache():
    """设置 modelscope 的缓存路径，避免打包后找不到模型"""
    if os.environ.get("MODELSCOPE_CACHE"):
        return
    # 默认使用用户目录下的 .cache/modelscope
    cache_root = Path.home() / ".cache" / "modelscope"
    os.environ["MODELSCOPE_CACHE"] = str(cache_root)

def _patch_inspect_for_frozen_sources():
    """
    修复 inspect.getsourcefile 在 PyInstaller 环境下的行为。
    某些库（如 modelscope）内部可能会调用它，如果不修复可能会报错。
    """
    orig_getsourcefile = inspect.getsourcefile
    def patched_getsourcefile(obj):
        filename = orig_getsourcefile(obj)
        if filename and not os.path.isabs(filename):
            if hasattr(sys, "_MEIPASS"):
                candidate = Path(sys._MEIPASS) / filename
                if candidate.exists():
                    return str(candidate)
        return filename
    inspect.getsourcefile = patched_getsourcefile

# 执行必要的初始化，不再包含任何 torch 或 funasr 的引用
_setup_modelscope_cache()
_patch_inspect_for_frozen_sources()

print("[runtime_hook] Minimal environment setup complete (Torch/FunASR patches removed)")