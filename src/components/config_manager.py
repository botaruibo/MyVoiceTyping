import json
import shutil
import sys
from pathlib import Path
import tempfile
from typing import Optional

_instance = None
_APP_NAME = "MyVoiceTyping"
_LEGACY_APP_NAME = "MyVoiceInput"

def get_config_manager():
    """
    获取 ConfigManager 的全局唯一实例。

    :return: ConfigManager 实例
    """
    global _instance
    if _instance is None:
        _instance = ConfigManager()
    return _instance

def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")

def get_common_root_dir() -> Path:
    if hasattr(sys, "_MEIPASS") or bool(getattr(sys, "frozen", False)):
        exe_path = Path(sys.executable).resolve()
        return exe_path.parent.parent / "Resources"
    return Path(__file__).resolve().parents[2]

def _macos_app_support_root(app_name: str) -> Path:
    return Path.home() / "Library" / "Application Support" / app_name


def _migrate_legacy_app_support_root(new_root: Path) -> None:
    old_root = _macos_app_support_root(_LEGACY_APP_NAME)
    try:
        if new_root.exists() or not old_root.exists():
            return
        shutil.copytree(old_root, new_root)
        print(f"✅ 已迁移旧配置目录: {old_root} -> {new_root}")
    except Exception as e:
        print(f"⚠️ 迁移旧配置目录失败（将使用新目录默认配置）: {e}")


def _guess_bundled_data_dir() -> Optional[Path]:
    candidates: list[Path] = []

    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS))

    try:
        exe = Path(sys.executable).resolve()
        exe_dir = exe.parent
        contents_dir = exe_dir.parent
        candidates.extend(
            [
                exe_dir,
                contents_dir,
                contents_dir / "Resources",
                contents_dir / "Frameworks",
            ]
        )
    except Exception:
        pass

    try:
        candidates.append(Path(__file__).resolve().parents[2])
    except Exception:
        candidates.append(Path.cwd().resolve())

    seen: set[Path] = set()
    for root in candidates:
        if root in seen:
            continue
        seen.add(root)

        probe_dirs = [
            root / "data",
            root / "Resources" / "data",
            root / "_internal" / "data",
            root.parent / "Resources" / "data",
            root.parent / "data",
        ]
        for d in probe_dirs:
            try:
                if d.exists() and d.is_dir():
                    return d
            except Exception:
                continue

    return None

class ConfigManager:
    """
    配置管理器，将配置数据存储到本地JSON文件中
    """

    def __init__(self, config_file_path=None):
        self._writable_root: Optional[Path] = None
        self._bundled_data_dir: Optional[Path] = _guess_bundled_data_dir()

        if config_file_path is None:
            if sys.platform == "darwin" and _is_frozen():
                self._writable_root = _macos_app_support_root(_APP_NAME)
                _migrate_legacy_app_support_root(self._writable_root)
                config_dir = self._writable_root / "config"
                try:
                    config_dir.mkdir(parents=True, exist_ok=True)
                except Exception:
                    config_dir = Path(tempfile.gettempdir()) / _APP_NAME / "config"
                    config_dir.mkdir(parents=True, exist_ok=True)
                    self._writable_root = config_dir.parent

                self.config_dir = config_dir
                self.config_file_path = self.config_dir / "app_config.json"
                self.prompt_file_path = self.config_dir / "main_prompt.md"
            else:
                # 从项目根目录开始计算路径
                project_root = Path(__file__).resolve().parents[2]
                self.config_dir = project_root / "data" / "config"
                self.config_dir.mkdir(parents=True, exist_ok=True)
                self.config_file_path = self.config_dir / "app_config.json"
                self.prompt_file_path = self.config_dir / "main_prompt.md"
        else:
            self.config_file_path = Path(config_file_path)
            self.config_dir = self.config_file_path.parent

        if self._writable_root is not None:
            audio_dir_default = "audio"
            transcripts_dir_default = "transcripts"
        else:
            audio_dir_default = "data/audio"
            transcripts_dir_default = "data/transcripts"

        self.default_config = {
            "press_hotkey": "fn",
            "sample_rate": 16000,
            "chunk_size": 1024,
            "stt_provider": "funasr",
            "format_text": False,
            "llm_text_provider": "llama_cpp",
            "funasr_hotwords": [],
            "preload_stt_on_startup": True,
            "stt_warmup_on_startup": True,
            "preload_llama_cpp_on_startup": True,
            "llama_cpp_model_path": "data/models/chinese_text_correction_1.5b",
            "llama_cpp_model_id": "botaruibo/chinese_text_correction_1.5b_gguf",
            "llama_cpp_model_revision": "master",
            "llama_cpp_model_file": "chinese_text_correction_1.5b-q4_k_m.gguf",
            "llama_cpp_n_ctx": 4096,
            "llama_cpp_n_threads": 0,
            "llama_cpp_temperature": 0.0,
            "llama_cpp_max_tokens": 96,
            "llama_cpp_top_p": 1.0,
            "llama_cpp_top_k": 0,
            "llama_cpp_prefix_prompt": "文本纠错：\n",
            "llama_cpp_n_gpu_layers": -1,
            "llama_cpp_n_batch": 512,
            "llama_cpp_verbose": False,
            "audio_dir": audio_dir_default,
            "transcripts_dir": transcripts_dir_default,
            "models_dir": "data/models",
            "mute_speaker": True,
            "min_audio_duration_ms": 400,
        }
        self.main_prompt = ""

        self.config = self.default_config.copy()
        self.config = self.load_config()
        self.main_prompt = self.load_prompt()

    def _try_seed_from_bundled_config(self) -> bool:
        if self._bundled_data_dir is None:
            return False

        bundled_config_path = self._bundled_data_dir / "config" / "app_config.json"
        if not bundled_config_path.exists():
            return False

        try:
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                if bundled_config_path.resolve() == self.config_file_path.resolve():
                    return True
            except Exception:
                pass

            shutil.copy2(bundled_config_path, self.config_file_path)
            return True
        except Exception as e:
            print(f"复制默认配置文件失败: {e}")
            return False

    def _try_seed_from_bundled_prompt(self) -> bool:
        if self._bundled_data_dir is None:
            return False

        bundled_prompt_path = self._bundled_data_dir / "config" / "main_prompt.md"
        if not bundled_prompt_path.exists():
            return False

        try:
            self.prompt_file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                if bundled_prompt_path.resolve() == self.prompt_file_path.resolve():
                    return True
            except Exception:
                pass

            if not self.prompt_file_path.exists():
                shutil.copy2(bundled_prompt_path, self.prompt_file_path)
            return True
        except Exception as e:
            print(f"复制默认提示文件失败: {e}")
            return False

    def load_prompt(self) -> Optional[str]:
        try:
            if not self.prompt_file_path.exists():
                self._try_seed_from_bundled_prompt()
            with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"加载提示文件时出错: {e}")
            return None

    def load_config(self):
        """从文件加载配置，如果文件不存在或损坏则使用默认配置"""
        if not self.config_file_path.exists():
            if self._try_seed_from_bundled_config() and self.config_file_path.exists():
                return self.load_config()

            self.config = self.default_config.copy()
            self.save_config()
            return self.config

        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            if not isinstance(loaded_config, dict):
                raise ValueError("配置文件格式错误（顶层必须为 object）")

            final_config = self.default_config.copy()
            final_config.update(loaded_config)
            return final_config
        except Exception as e:
            print(f"加载配置文件时出错: {e}，尝试恢复默认配置文件")

            if self._try_seed_from_bundled_config() and self.config_file_path.exists():
                try:
                    with open(self.config_file_path, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    if isinstance(loaded_config, dict):
                        final_config = self.default_config.copy()
                        final_config.update(loaded_config)
                        return final_config
                except Exception:
                    pass

            self.config = self.default_config.copy()
            self.save_config()
            return self.config

    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            return False

    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key.lower(), default)

    def set(self, key, value):
        """设置配置值"""
        self.config[str(key).lower()] = value
        self.save_config()

    def _resolve_writable_path(self, raw_value, default_value: str) -> Path:
        raw = raw_value if raw_value else default_value
        p = Path(raw)

        if p.is_absolute():
            return p

        if self._writable_root is None:
            return p

        try:
            if p.parts and p.parts[0] == "data":
                p = Path(*p.parts[1:])
        except Exception:
            pass

        return self._writable_root / p

    def _resolve_models_path(self, raw_value, default_value: str) -> Path:
        raw = raw_value if raw_value else default_value
        p = Path(raw)

        if p.is_absolute():
            return p

        if self._bundled_data_dir is not None:
            q = p
            try:
                if q.parts and q.parts[0] == "data":
                    q = Path(*q.parts[1:])
            except Exception:
                pass

            candidate = self._bundled_data_dir / q
            if candidate.exists():
                return candidate

        return self._resolve_writable_path(raw_value, default_value)

    def get_audio_dir(self):
        audio_dir = self._resolve_writable_path(self.config.get("audio_dir"), "data/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    def get_transcripts_dir(self):
        transcripts_dir = self._resolve_writable_path(
            self.config.get("transcripts_dir"),
            "data/transcripts",
        )
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        return transcripts_dir

    def get_models_dir(self):
        models_dir = self._resolve_models_path(self.config.get("models_dir"), "data/models")

        if self._bundled_data_dir is not None:
            try:
                if models_dir.resolve().is_relative_to(self._bundled_data_dir.resolve()):
                    return models_dir
            except Exception:
                pass

        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir
