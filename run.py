#!/usr/bin/env python3
"""
项目入口文件
"""

import sys, os

import multiprocessing

os.environ['MP_FORCE_NO_RESOURCE_TRACKER'] = '1'  # 方法 B：强制禁用 tracker键，解决 Dock 双图标
os.environ["MODELSCOPE_DOWNLOAD_MAX_WORKERS"] = "1" # 控制模型下载并发数
# 必须在最开头，甚至在其他 import 之前
multiprocessing.freeze_support()

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
from src.util.app_logger import AppLogger

AppLogger.setup_startup()

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
        AppLogger.switch_to_runtime()
        app.run()
    except Exception as e:
        AppLogger.write_startup_crash(e)
        raise