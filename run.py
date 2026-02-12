#!/usr/bin/env python3
"""
项目入口文件
"""

import os
import time
from pathlib import Path
import traceback

"""/**
 * 记录应用启动时间戳（秒）。
 *
 * 说明：
 * - 放在尽可能靠前的位置，尽量覆盖 import + 初始化耗时。
 * - 使用环境变量是为了让 `src/main.py` 在不同启动方式下也能读取。
 */"""
os.environ.setdefault("MYVOICEINPUT_APP_START_TS", str(time.time()))

from src.main import FlashInputApp


def _write_startup_crash_log(exc: BaseException) -> None:
    try:
        log_dir = Path.home() / "Library" / "Logs" / "MyVoiceInput"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "startup_crash.log"
        log_file.write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        app = FlashInputApp()
        app.run()
    except Exception as e:
        _write_startup_crash_log(e)
        raise