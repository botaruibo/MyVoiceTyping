#!/usr/bin/env python3
"""
项目入口文件
"""

from pathlib import Path
import traceback

from src.main import TypelessApp


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
        app = TypelessApp()
        app.run()
    except Exception as e:
        _write_startup_crash_log(e)
        raise