import logging
import sys, os
import threading
import traceback
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from ..components.config_manager import get_common_root_dir


class _LineBufferingLoggerWriter:
    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level = level
        self._buf = ""
        self.encoding = "utf-8"

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buf += str(s)
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip()
            if line:
                self._logger.log(self._level, line)
        return len(s)

    def flush(self) -> None:
        if self._buf.strip():
            self._logger.log(self._level, self._buf.rstrip())
        self._buf = ""

    def isatty(self) -> bool:
        return False

class _TeeLoggerWriter(_LineBufferingLoggerWriter):
    def __init__(self, logger: logging.Logger, level: int, stream):
        super().__init__(logger, level)
        self._stream = stream

    def write(self, s: str) -> int:
        if self._stream is not None:
            try:
                self._stream.write(s)
                self._stream.flush()
            except Exception:
                pass
        return super().write(s)

    def flush(self) -> None:
        if self._stream is not None:
            try:
                self._stream.flush()
            except Exception:
                pass
        super().flush()

class _DailyFileHandler(logging.Handler):
    def __init__(self, logs_dir: Path, prefix: str = "runtime_", encoding: str = "utf-8"):
        super().__init__()
        self._logs_dir = logs_dir
        self._prefix = prefix
        self._encoding = encoding
        self._lock = threading.Lock()
        self._current_day: Optional[date] = None
        self._stream = None

    def _path_for_day(self, d: date) -> Path:
        return self._logs_dir / f"{self._prefix}{d.strftime('%Y-%m-%d')}.log"

    def _ensure_stream(self) -> None:
        today = date.today()
        if self._current_day == today and self._stream is not None:
            return
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self._logs_dir.mkdir(parents=True, exist_ok=True)
        p = self._path_for_day(today)
        self._stream = open(p, "a", encoding=self._encoding)
        self._current_day = today

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            return

        with self._lock:
            try:
                self._ensure_stream()
                if self._stream is None:
                    return
                self._stream.write(msg + "\n")
                self._stream.flush()
            except Exception:
                pass

    def close(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._current_day = None
        super().close()


class AppLogger:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is not None:
            return cls._instance
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def instance(cls) -> "AppLogger":
        return cls()

    _inited = False
    _startup_log_path: Optional[Path] = None
    _logs_dir: Optional[Path] = None

    _startup_handler: Optional[logging.Handler] = None
    _runtime_handler: Optional[logging.Handler] = None

    _orig_stdout = None
    _orig_stderr = None

    @classmethod
    def _resolve_logs_dir(cls) -> Path:
        is_frozen = hasattr(sys, "_MEIPASS") or bool(getattr(sys, "frozen", False))
        if sys.platform == "darwin" and is_frozen:
            candidate = Path.home() / "Library" / "Application Support" / "MyVoiceTyping" / "logs"
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate

        root = get_common_root_dir()
        candidate = root / "logs"
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            fallback = Path.home() / "Library" / "Logs" / "MyVoiceTyping"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    @classmethod
    def get_log_dir(cls) -> Path:
        if cls._logs_dir:
            return cls._logs_dir
        return cls._resolve_logs_dir()

    @classmethod
    def setup_startup(cls, level: int = logging.INFO) -> None:
        if cls._inited:
            return

        cls._logs_dir = cls._resolve_logs_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls._startup_log_path = cls._logs_dir / f"startup_{ts}.log"

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        handler = logging.FileHandler(cls._startup_log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root_logger.addHandler(handler)
        cls._startup_handler = handler

        cls._orig_stdout = sys.stdout
        cls._orig_stderr = sys.stderr

        cls.set_writer(root_logger)

        root_logger.info("startup_log=%s", str(cls._startup_log_path))
        cls._inited = True

    @classmethod
    def set_writer(cls, root_logger):
        is_frozen = hasattr(sys, "_MEIPASS") or bool(getattr(sys, "frozen", False))
        also_to_console = not is_frozen

        env = (
            os.environ.get("MYVOICETYPING_LOG_TO_CONSOLE")
            or os.environ.get("MYVOICEINPUT_LOG_TO_CONSOLE")
            or ""
        ).strip()
        if env != "":
            also_to_console = env not in ("0", "false", "False", "no", "NO")

        if also_to_console:
            sys.stdout = _TeeLoggerWriter(root_logger, logging.INFO, cls._orig_stdout)
            sys.stderr = _TeeLoggerWriter(root_logger, logging.ERROR, cls._orig_stderr)
        else:
            sys.stdout = _LineBufferingLoggerWriter(root_logger, logging.INFO)
            sys.stderr = _LineBufferingLoggerWriter(root_logger, logging.ERROR)

    @classmethod
    def switch_to_runtime(cls, level: int = logging.INFO) -> None:
        if not cls._inited:
            cls.setup_startup(level=level)

        logs_dir = cls._logs_dir or cls._resolve_logs_dir()
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        if cls._startup_handler is not None:
            try:
                root_logger.removeHandler(cls._startup_handler)
            except Exception:
                pass

        if cls._runtime_handler is None:
            runtime_handler = _DailyFileHandler(logs_dir=logs_dir)
            runtime_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            root_logger.addHandler(runtime_handler)
            cls._runtime_handler = runtime_handler

        root_logger.info("runtime_logs_dir=%s", str(logs_dir))

    @classmethod
    def write_startup_crash(cls, exc: BaseException) -> None:
        try:
            if not cls._inited:
                cls.setup_startup()

            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            logs_dir = cls._logs_dir or cls._resolve_logs_dir()

            crash_path = logs_dir / "startup_crash.log"
            try:
                crash_path.parent.mkdir(parents=True, exist_ok=True)
                with open(crash_path, "a", encoding="utf-8") as f:
                    f.write(tb)
                    if not tb.endswith("\n"):
                        f.write("\n")
            except Exception:
                pass

            try:
                logging.getLogger().error("startup_crash", exc_info=exc)
            except Exception:
                pass
        except Exception:
            pass
