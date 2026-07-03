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
    _OBSOLETE_CONFIG_KEYS = {
        "toggle_hotkey",
        "funasr_device",
        "funasr_hotwords",
        "base_url",
        "api_key",
        "model_name",
        "llm_temperature",
        "llm_timeout",
        "llm_max_tokens",
        "llama_cpp_prefix_prompt",
        "asr_post_scene",
    }
    _LEGACY_LLAMA_CPP_MODEL_VALUES = {
        "llama_cpp_model_path": {
            "data/models/chinese_text_correction_1.5b",
        },
        "llama_cpp_model_id": {
            "botaruibo/chinese_text_correction_1.5b_gguf",
        },
        "llama_cpp_model_file": {
            "chinese_text_correction_1.5b-q4_k_m.gguf",
        },
    }
    _HOTWORD_DICTIONARY_DISPLAY_NAMES = {
        "custom_hotwords": "自定义词库",
        "software_development": "软件研发",
    }

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
            self.prompt_file_path = self.config_dir / "main_prompt.md"

        if self._writable_root is not None:
            audio_dir_default = "audio"
            transcripts_dir_default = "transcripts"
            hotword_dict_default = [
                "config/hotwords/custom_hotwords.txt",
            ]
        else:
            audio_dir_default = "data/audio"
            transcripts_dir_default = "data/transcripts"
            hotword_dict_default = [
                "config/hotwords/custom_hotwords.txt",
            ]

        self.default_config = {
            "press_hotkey": "fn",
            "sample_rate": 16000,
            "chunk_size": 1024,
            "stt_provider": "funasr",
            "format_text": True,
            "llm_text_provider": "llama_cpp",
            "funasr_hotword_dictionaries": hotword_dict_default,
            "preload_stt_on_startup": True,
            "stt_warmup_on_startup": True,
            "preload_llama_cpp_on_startup": True,
            "llama_cpp_model_path": "data/models/MyVoiceTyping-1.5b-q4",
            "llama_cpp_model_id": "botaruibo/MyVoiceTyping-1.5b-q4",
            "llama_cpp_model_revision": "master",
            "llama_cpp_model_file": "",
            "llama_cpp_n_ctx": 4096,
            "llama_cpp_n_threads": 0,
            "llama_cpp_temperature": 0.0,
            "llama_cpp_max_tokens": 96,
            "llama_cpp_top_p": 1.0,
            "llama_cpp_top_k": 0,
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
        self._try_seed_from_bundled_hotword_dictionaries()
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

    def _try_seed_from_bundled_hotword_dictionaries(self) -> bool:
        if self._writable_root is None or self._bundled_data_dir is None:
            return False

        bundled_dir = self._bundled_data_dir / "config" / "hotwords"
        if not bundled_dir.exists():
            return False

        target_dir = self.get_hotword_dictionaries_dir()
        copied = False
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            for src_path in sorted(bundled_dir.glob("*.txt")):
                dst_path = target_dir / src_path.name
                if not dst_path.exists():
                    shutil.copy2(src_path, dst_path)
                    copied = True
            return copied
        except Exception as e:
            print(f"复制默认热词词典失败: {e}")
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
            return self._normalize_loaded_config(final_config)
        except Exception as e:
            print(f"加载配置文件时出错: {e}，尝试恢复默认配置文件")

            if self._try_seed_from_bundled_config() and self.config_file_path.exists():
                try:
                    with open(self.config_file_path, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    if isinstance(loaded_config, dict):
                        final_config = self.default_config.copy()
                        final_config.update(loaded_config)
                        return self._normalize_loaded_config(final_config)
                except Exception:
                    pass

            self.config = self.default_config.copy()
            self.save_config()
            return self.config

    def _normalize_loaded_config(self, config: dict) -> dict:
        """迁移旧配置并移除不再暴露的历史配置项。"""
        normalized = dict(config)
        changed = False

        legacy_hotwords = normalized.get("funasr_hotwords")
        if legacy_hotwords:
            try:
                self._write_legacy_hotwords_to_custom_dictionary(legacy_hotwords)
                selected = normalized.get("funasr_hotword_dictionaries") or self.default_config.get(
                    "funasr_hotword_dictionaries",
                    [],
                )
                custom_path = "config/hotwords/custom_hotwords.txt" if self._writable_root else "data/config/hotwords/custom_hotwords.txt"
                if custom_path not in selected:
                    selected = list(selected) + [custom_path]
                normalized["funasr_hotword_dictionaries"] = selected
                changed = True
            except Exception as e:
                print(f"迁移旧热词配置失败: {e}")

        for key in self._OBSOLETE_CONFIG_KEYS:
            if key in normalized:
                normalized.pop(key, None)
                changed = True

        for key, legacy_values in self._LEGACY_LLAMA_CPP_MODEL_VALUES.items():
            current_value = normalized.get(key)
            if current_value in legacy_values:
                normalized[key] = self.default_config.get(key)
                changed = True

        if changed:
            self.config = normalized.copy()
            self.save_config()

        return normalized

    @staticmethod
    def _normalize_hotword(word: str) -> str:
        return "".join(str(word or "").split()).strip()

    def _write_legacy_hotwords_to_custom_dictionary(self, raw_hotwords) -> None:
        if isinstance(raw_hotwords, str):
            parts = raw_hotwords.replace("，", ",").replace("\n", ",").split(",")
        elif isinstance(raw_hotwords, list):
            parts = raw_hotwords
        else:
            parts = []

        existing = self.load_hotword_dictionary("custom_hotwords.txt")
        seen = set(existing)
        words = list(existing)
        for item in parts:
            word = self._normalize_hotword(str(item or ""))
            if word and word not in seen:
                seen.add(word)
                words.append(word)
        if words:
            self.save_hotword_dictionary("custom_hotwords.txt", words)

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

    def get_hotword_dictionaries_dir(self) -> Path:
        if self._writable_root is not None:
            path = self._writable_root / "config" / "hotwords"
        else:
            path = Path(__file__).resolve().parents[2] / "data" / "config" / "hotwords"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _resolve_hotword_dictionary_path(self, raw_path: str | Path) -> Path:
        path = Path(str(raw_path or "")).expanduser()
        if path.is_absolute():
            return path
        if path.parts and path.parts[0] == "data":
            path = Path(*path.parts[1:])
        if len(path.parts) >= 2 and path.parts[0] == "config" and path.parts[1] == "hotwords":
            return self.get_hotword_dictionaries_dir() / Path(*path.parts[2:])
        if len(path.parts) == 1:
            return self.get_hotword_dictionaries_dir() / path
        return self.get_hotword_dictionaries_dir() / path.name

    def _hotword_dictionary_config_path(self, path: Path) -> str:
        try:
            relative = path.resolve().relative_to(self.get_hotword_dictionaries_dir().resolve())
            return str(Path("config") / "hotwords" / relative)
        except Exception:
            return str(path)

    def list_hotword_dictionaries(self) -> list[dict]:
        self._try_seed_from_bundled_hotword_dictionaries()
        dictionaries: list[dict] = []
        for path in sorted(self.get_hotword_dictionaries_dir().glob("*.txt")):
            words = self.load_hotword_dictionary(path)
            dictionaries.append({
                "name": self._HOTWORD_DICTIONARY_DISPLAY_NAMES.get(path.stem, path.stem),
                "filename": path.name,
                "path": self._hotword_dictionary_config_path(path),
                "word_count": len(words),
            })
        return dictionaries

    def load_hotword_dictionary(self, path_or_name) -> list[str]:
        path = self._resolve_hotword_dictionary_path(path_or_name)
        if not path.exists():
            return []
        seen: set[str] = set()
        words: list[str] = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            word = self._normalize_hotword(line.split("#", 1)[0])
            if word and word not in seen:
                seen.add(word)
                words.append(word)
        return words

    def save_hotword_dictionary(self, path_or_name, words: list[str]) -> None:
        path = self._resolve_hotword_dictionary_path(path_or_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        seen: set[str] = set()
        clean_words: list[str] = []
        for item in words:
            word = self._normalize_hotword(str(item or ""))
            if word and word not in seen:
                seen.add(word)
                clean_words.append(word)
        path.write_text("\n".join(clean_words) + ("\n" if clean_words else ""), encoding="utf-8")

    def get_selected_hotword_dictionary_paths(self) -> list[str]:
        raw = self.config.get("funasr_hotword_dictionaries", [])
        if isinstance(raw, str):
            parts = [item.strip() for item in raw.replace("，", ",").split(",")]
        elif isinstance(raw, list):
            parts = raw
        else:
            parts = []
        selected: list[str] = []
        seen: set[str] = set()
        for item in parts:
            path = str(item or "").strip()
            if path and path not in seen:
                seen.add(path)
                selected.append(path)
        return selected

    def set_selected_hotword_dictionary_paths(self, paths: list[str]) -> None:
        seen: set[str] = set()
        selected: list[str] = []
        for item in paths:
            path = str(item or "").strip()
            if path and path not in seen:
                seen.add(path)
                selected.append(path)
        self.set("funasr_hotword_dictionaries", selected)

    def get_funasr_hotwords(self) -> list[str]:
        seen: set[str] = set()
        hotwords: list[str] = []
        for dictionary_path in self.get_selected_hotword_dictionary_paths():
            for word in self.load_hotword_dictionary(dictionary_path):
                if word not in seen:
                    seen.add(word)
                    hotwords.append(word)
        return hotwords
