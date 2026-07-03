"""本地 llama.cpp/GGUF 文本重写模块。"""

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

try:
    from ..components.config_manager import get_config_manager
except ImportError:
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.components.config_manager import get_config_manager

_instance = None
_instance_lock = threading.Lock()

LOCAL_LLAMA_CPP_PROVIDERS = {"llama_cpp", "local_llama_cpp", "gguf"}
DEFAULT_LLAMA_CPP_MODEL_ID = "botaruibo/MyVoiceTyping-1.5b-q4"
DEFAULT_LLAMA_CPP_MODEL_REVISION = "master"
DEFAULT_LLAMA_CPP_MODEL_FILE = ""
DEFAULT_LLAMA_CPP_LOCAL_NAME = "MyVoiceTyping-1.5b-q4"
ASR_POST_TAGS = "<ASR_POST><MIN_EDIT><CORRECT><NO_NEW_LINKS><PRESERVE_EXISTING_LINKS>"
DEFAULT_ASR_POST_SCENE = "general"
SYSTEM_PROMPT_FALLBACK = "你是中文文本纠错助手。"
APP_SCENE_BY_BUNDLE_ID = {
    "com.apple.MobileSMS": "chat",
    "com.tencent.xinWeChat": "chat",
    "com.tencent.WeWorkMac": "chat",
    "com.tinyspeck.slackmacgap": "chat",
    "us.zoom.xos": "meeting",
    "com.microsoft.teams2": "meeting",
    "com.apple.Safari": "browser",
    "com.google.Chrome": "browser",
    "com.microsoft.edgemac": "browser",
    "org.mozilla.firefox": "browser",
    "com.apple.mail": "email",
    "com.microsoft.Outlook": "email",
    "com.apple.Notes": "note",
    "com.youdao.note.YoudaoNoteMac": "note",
    "com.apple.TextEdit": "document",
    "com.microsoft.Word": "document",
    "com.apple.iWork.Pages": "document",
    "com.microsoft.Excel": "spreadsheet",
    "com.apple.iWork.Numbers": "spreadsheet",
    "com.microsoft.Powerpoint": "presentation",
    "com.apple.iWork.Keynote": "presentation",
    "com.apple.Terminal": "terminal",
    "com.googlecode.iterm2": "terminal",
    "com.microsoft.VSCode": "code",
    "com.jetbrains.pycharm": "code",
    "com.apple.dt.Xcode": "code",
}


def _resolve_system_prompt(prompt: Optional[str]) -> str:
    text = (prompt or "").strip()
    return text or SYSTEM_PROMPT_FALLBACK


def _frontmost_app_identity() -> tuple[str, str]:
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return "", ""
        name = str(app.localizedName() or "")
        bundle_id = str(app.bundleIdentifier() or "")
        return name, bundle_id
    except Exception:
        return "", ""


def _running_app_identity_for_pid(pid: Any) -> tuple[str, str]:
    try:
        from AppKit import NSRunningApplication

        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(int(pid))
        if app is None:
            return "", ""
        name = str(app.localizedName() or "")
        bundle_id = str(app.bundleIdentifier() or "")
        return name, bundle_id
    except Exception:
        return "", ""


def _accessibility_api() -> Any:
    try:
        import ApplicationServices  # type: ignore

        return ApplicationServices
    except Exception:
        import Quartz  # type: ignore

        return Quartz


def _ax_copy_attribute(element: Any, attribute: str) -> Any:
    try:
        ax = _accessibility_api()
        result = ax.AXUIElementCopyAttributeValue(element, attribute, None)
        if isinstance(result, tuple):
            err = result[0] if len(result) > 0 else -1
            value = result[1] if len(result) > 1 else None
            if int(err) == 0:
                return value
    except Exception:
        return None
    return None


def _ax_element_pid(element: Any) -> Optional[int]:
    if element is None:
        return None

    try:
        ax = _accessibility_api()
        result = ax.AXUIElementGetPid(element, None)
        if isinstance(result, tuple):
            err = result[0] if len(result) > 0 else -1
            pid = result[1] if len(result) > 1 else None
            if int(err) == 0 and pid is not None:
                return int(pid)
    except Exception:
        pass

    pid_value = _ax_copy_attribute(element, "AXPID")
    try:
        return int(pid_value) if pid_value is not None else None
    except Exception:
        return None


def _focused_app_identity_from_accessibility() -> tuple[str, str]:
    try:
        ax = _accessibility_api()
        system_wide = ax.AXUIElementCreateSystemWide()
        if system_wide is None:
            return "", ""

        focused_element_attr = getattr(
            ax,
            "kAXFocusedUIElementAttribute",
            "AXFocusedUIElement",
        )
        focused_element = _ax_copy_attribute(system_wide, focused_element_attr)
        pid = _ax_element_pid(focused_element)
        if pid is not None:
            identity = _running_app_identity_for_pid(pid)
            if identity[1]:
                return identity

        focused_app_attr = getattr(
            ax,
            "kAXFocusedApplicationAttribute",
            "AXFocusedApplication",
        )
        focused_app = _ax_copy_attribute(system_wide, focused_app_attr)
        pid = _ax_element_pid(focused_app)
        if pid is not None:
            identity = _running_app_identity_for_pid(pid)
            if identity[1]:
                return identity
    except Exception:
        return "", ""

    return "", ""


def _focused_or_frontmost_app_identity() -> tuple[str, str]:
    identity = _focused_app_identity_from_accessibility()
    if identity[1]:
        return identity
    return _frontmost_app_identity()


def _infer_asr_post_scene() -> str:
    app_name, bundle_id = _focused_or_frontmost_app_identity()

    def _log_scene(scene: str, source: str) -> str:
        logging.info(
            "ASR 后处理场景识别: scene=%s, bundle_id=%s, app_name=%s, source=%s",
            scene,
            bundle_id or "<empty>",
            app_name or "<empty>",
            source,
        )
        return scene

    if bundle_id == "com.myvoicetyping.desktop" or app_name == "MyVoiceTyping":
        return _log_scene(DEFAULT_ASR_POST_SCENE, "self_app")

    scene = APP_SCENE_BY_BUNDLE_ID.get(bundle_id)
    if scene:
        return _log_scene(scene, "bundle_id")

    normalized = f"{app_name} {bundle_id}".lower()
    keyword_scenes = (
        ("browser", ("browser", "chrome", "safari", "firefox", "edge")),
        ("chat", ("wechat", "微信", "slack", "telegram", "discord", "messages", "飞书", "lark")),
        ("meeting", ("zoom", "teams", "meeting", "会议")),
        ("email", ("mail", "outlook", "邮箱", "邮件")),
        ("code", ("code", "xcode", "pycharm", "intellij", "cursor", "trae", "terminal", "iterm")),
        ("document", ("word", "pages", "textedit", "docs", "文档")),
        ("spreadsheet", ("excel", "numbers", "sheet", "表格")),
        ("presentation", ("powerpoint", "keynote", "slides", "演示")),
        ("note", ("note", "notes", "notion", "obsidian", "备忘录", "笔记")),
    )
    for scene_name, keywords in keyword_scenes:
        if any(keyword in normalized for keyword in keywords):
            return _log_scene(scene_name, "keyword")
    return _log_scene(DEFAULT_ASR_POST_SCENE, "default")


def _build_asr_post_user_prompt(raw_text: str, scene: Optional[str] = None) -> str:
    scene = (scene or _infer_asr_post_scene() or DEFAULT_ASR_POST_SCENE).strip()
    if scene:
        logging.info("ASR 后处理最终 prompt 场景: scene=%s", scene)
    return f"{ASR_POST_TAGS}\n场景：{scene}\n原文：{(raw_text or '').strip()}"


def _to_int(value: Any, default: int) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def get_rewriter():
    """
    /**
     * 获取 Rewrite 的全局唯一实例（懒加载）。
     *
     * 设计目标：
     * - 返回必须足够快：不做任何联网测试、不做重型依赖导入。
     * - 重型初始化交由 GUI 就绪后的后加载线程处理。
     *
     * @returns {Rewrite} Rewrite 实例
     */
    """
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = Rewrite()
    return _instance


class Rewrite:
    def __init__(self):
        """
        /**
         * Rewrite 初始化（轻量）。
         *
         * 注意：这里不进行任何远程模型连通性测试，避免阻塞 GUI 显示。
         */
        """
        self.config = get_config_manager()

        self.local_llama_cpp_client = None
        self._local_llama_cpp_init_lock = threading.Lock()
        self._local_llama_cpp_init_started = False

    def init_local_llama_cpp_async(self, reason: str = "") -> None:
        """
        异步初始化本地 llama.cpp GGUF 模型并预热（不会阻塞调用方）。

        - 适合 GUI 就绪后的"后加载"线程调用，把模型加载 + 首次 prompt eval
          的代价吸收到启动期，用户首次按热键改写时就不必再等。
        - 加锁防止并发重复加载，加载/预热失败时静默降级（运行期会再做懒加载）。
        """
        with self._local_llama_cpp_init_lock:
            if self._local_llama_cpp_init_started:
                return
            self._local_llama_cpp_init_started = True

        def _worker() -> None:
            tag = f"reason={reason}" if reason else ""
            try:
                print(f"🌐 开始初始化本地 llama.cpp 改写模型 {tag}...")
                if self.local_llama_cpp_client is None or not isinstance(
                    self.local_llama_cpp_client, LocalLlamaCppRewrite
                ):
                    self.local_llama_cpp_client = LocalLlamaCppRewrite()
                # 先确认/下载 GGUF 模型文件（带 GUI 进度），再加载与预热。
                self.local_llama_cpp_client.ensure_model_downloaded()
                self.local_llama_cpp_client.warm_up()
                print("✅ 本地 llama.cpp 改写模型初始化完成")
            except Exception as e:
                # 失败不致命：rewrite() 时会再做懒加载
                print(f"⚠️ 本地 llama.cpp 改写模型初始化失败（运行期会重试）: {e}")
                with self._local_llama_cpp_init_lock:
                    self._local_llama_cpp_init_started = False

        threading.Thread(target=_worker, daemon=True).start()

    def test_llm(self) -> Optional[str]:
        """测试当前本地 llama.cpp 文本改写模型。成功返回 None。"""
        provider = self.config.get("LLM_TEXT_PROVIDER")
        if provider not in LOCAL_LLAMA_CPP_PROVIDERS:
            return f"未知文本改写 provider: {provider}"
        try:
            if self.local_llama_cpp_client is None or not isinstance(
                self.local_llama_cpp_client, LocalLlamaCppRewrite
            ):
                self.local_llama_cpp_client = LocalLlamaCppRewrite()
            return self.local_llama_cpp_client.test()
        except Exception as e:
            return str(e)

    def rewrite(self, raw_text: str) -> str:
        """
        /**
         * 结构化改写文本。
         *
         * 规则：
         * - 若未开启格式化或模型未就绪：直接返回原文（不阻塞）。
         * - 若开启格式化但模型未初始化：触发一次异步初始化后立即降级返回原文。
         *
         * @param {string} raw_text - 原始文本
         * @returns {string} 改写后的文本（或原文）
         */
        """
        if not self.config.get("FORMAT_TEXT"):
            print("⚠️ 系统未开启文本格式化功能，直接返回原文")
            return raw_text

        provider = self.config.get("LLM_TEXT_PROVIDER")
        if provider not in LOCAL_LLAMA_CPP_PROVIDERS:
            print(f"⚠️ 未知文本改写 provider: {provider}，直接返回原文")
            return raw_text
        try:
            if self.local_llama_cpp_client is None or not isinstance(
                self.local_llama_cpp_client, LocalLlamaCppRewrite
            ):
                self.local_llama_cpp_client = LocalLlamaCppRewrite()
            return self.local_llama_cpp_client.rewrite(raw_text)
        except Exception as e:
            print(f"⚠️ 本地 llama.cpp 文本改写失败（将降级返回原文）: {e}")
            return raw_text


# ---------------------------------------------------------------------------
# LocalLlamaCppRewrite: 直接通过 llama-cpp-python 加载本地 GGUF 模型做文本改写/纠错。
#
# 设计目标：
# - 不依赖外部本地服务，进程内直接 mmap GGUF 权重做推理。
# - 模型权重默认取自 data/models/<name> 目录下的 *.gguf；也兼容直接指定文件。
# - 与现有 Rewrite 分发解耦：通过 `llm_text_provider="llama_cpp"` 选用。
# - 重型加载放到首次调用时懒执行，启动期不阻塞。
# ---------------------------------------------------------------------------


class LocalLlamaCppRewrite:
    """
    通过 llama-cpp-python 直接加载本地 GGUF 模型做中文文本纠错。

    默认从 data/models/<llama_cpp_model_path 目录名> 下查找 *.gguf 权重。
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: Optional[int] = None,
        n_threads: Optional[int] = None,
        main_prompt: Optional[str] = None,
    ):
        self.config = get_config_manager()
        self.system_prompt = _resolve_system_prompt(
            main_prompt
            or self.config.main_prompt
        )

        # 优先级：显式传参 > 配置 llama_cpp_model_path > 环境变量
        self.model_path: Optional[str] = (
            model_path
            or self.config.get("llama_cpp_model_path")
            or os.getenv("LLAMA_CPP_MODEL_PATH")
        )
        self.model_id = (
            self.config.get("llama_cpp_model_id")
            or os.getenv("LLAMA_CPP_MODEL_ID")
            or DEFAULT_LLAMA_CPP_MODEL_ID
        )
        self.model_revision = (
            self.config.get("llama_cpp_model_revision")
            or os.getenv("LLAMA_CPP_MODEL_REVISION")
            or DEFAULT_LLAMA_CPP_MODEL_REVISION
        )
        self.model_file = (
            self.config.get("llama_cpp_model_file")
            or os.getenv("LLAMA_CPP_MODEL_FILE")
            or DEFAULT_LLAMA_CPP_MODEL_FILE
        )

        self.n_ctx = _to_int(n_ctx or self.config.get("llama_cpp_n_ctx"), 4096)
        self.n_threads = _to_int(n_threads or self.config.get("llama_cpp_n_threads"), 0) or None
        self.temperature = _to_float(self.config.get("llama_cpp_temperature"), 0.0)
        self.max_tokens = _to_int(self.config.get("llama_cpp_max_tokens"), 96)
        self.top_p = _to_float(self.config.get("llama_cpp_top_p"), 1.0)
        self.top_k = _to_int(self.config.get("llama_cpp_top_k"), 0)
        self.verbose = bool(self.config.get("llama_cpp_verbose"))

        # Metal GPU 加速：默认 -1 表示尽可能多的层放到 Metal 上；
        # 0 表示纯 CPU；正整数表示放在 GPU 上的层数。
        n_gpu_layers_raw = self.config.get("llama_cpp_n_gpu_layers")
        self.n_gpu_layers = _to_int(n_gpu_layers_raw, -1)
        # n_batch 影响 prompt eval 的吞吐，512 在 M 系列上是较优默认。
        self.n_batch = _to_int(self.config.get("llama_cpp_n_batch"), 512)

        self._llm = None
        self._init_lock = threading.Lock()
        self._warm_done = False

    # ---------- 模型路径解析 ----------

    @staticmethod
    def _resolve_project_path(raw_path: str) -> Path:
        """将相对 data/models/* 路径解析为开发目录或打包目录下的真实路径。"""
        path = Path(str(raw_path)).expanduser()
        if path.is_absolute():
            return path

        try:
            parts = path.parts
            if len(parts) >= 2 and parts[0] == "data" and parts[1] == "models":
                models_root = get_config_manager().get_models_dir()
                candidate = models_root.joinpath(*parts[2:])
                if candidate.exists():
                    return candidate
                try:
                    from .stt_local_processor import get_models_root

                    writable_candidate = get_models_root().joinpath(*parts[2:])
                    if writable_candidate.exists():
                        return writable_candidate
                except Exception:
                    pass
        except Exception:
            pass

        if hasattr(sys, "_MEIPASS"):
            candidate = Path(sys._MEIPASS) / path
            if candidate.exists():
                return candidate

        try:
            exe_path = Path(sys.executable).resolve()
            resources_dir = exe_path.parent.parent / "Resources"
            candidate = resources_dir / path
            if candidate.exists():
                return candidate
        except Exception:
            pass

        return Path(__file__).resolve().parents[2] / path

    @staticmethod
    def _find_gguf_in_dir(directory: Path, preferred_name: str = "") -> Optional[Path]:
        """在目录中查找 *.gguf 权重文件；优先选配置文件名，其次选体积最大的。"""
        try:
            if not (directory.exists() and directory.is_dir()):
                return None
            if preferred_name:
                preferred = directory / preferred_name
                if preferred.exists() and preferred.is_file():
                    return preferred
            ggufs = sorted(
                directory.glob("*.gguf"),
                key=lambda p: p.stat().st_size,
                reverse=True,
            )
            return ggufs[0] if ggufs else None
        except Exception:
            return None

    def _resolve_model_path(self) -> str:
        """定位本地 GGUF 权重文件。

        查找顺序：
        1. 配置/传参 model_path：可直接是 .gguf 文件，或是包含 .gguf 的目录。
        2. 将相对 data/models/* 路径解析到开发/打包目录后再按文件或目录处理。
        """
        if self.model_path:
            raw = Path(self.model_path).expanduser()
            # 1a. 直接指向 .gguf 文件
            if raw.suffix == ".gguf" and raw.exists():
                return str(raw)
            # 1b. 指向目录
            found = self._find_gguf_in_dir(raw, str(self.model_file or ""))
            if found is not None:
                return str(found)

            # 2. 解析相对路径到真实目录/文件
            resolved = self._resolve_project_path(self.model_path)
            if resolved.suffix == ".gguf" and resolved.exists():
                return str(resolved)
            found = self._find_gguf_in_dir(resolved, str(self.model_file or ""))
            if found is not None:
                return str(found)

        raise FileNotFoundError(
            f"未找到 GGUF 模型文件：请将 *.gguf 放入 {self.model_path or 'data/models/<模型目录>'}"
        )

    def _download_target_dir(self) -> Path:
        """返回 GGUF 模型下载目标目录，打包后固定使用用户可写模型目录。"""
        model_path = Path(str(self.model_path or "")).expanduser()
        if model_path.suffix == ".gguf":
            local_name = model_path.parent.name or DEFAULT_LLAMA_CPP_LOCAL_NAME
        elif model_path.name:
            local_name = model_path.name
        else:
            local_name = DEFAULT_LLAMA_CPP_LOCAL_NAME

        try:
            from .stt_local_processor import get_models_root

            return get_models_root() / local_name
        except Exception:
            models_root = get_config_manager().get_models_dir()
            return models_root / local_name

    @staticmethod
    def _fix_gguf_download_layout(target_dir: Path) -> None:
        """整理 ModelScope 下载后的目录，确保 GGUF 权重位于目标目录根部。"""
        if not target_dir.exists():
            return
        for root, _dirs, files in os.walk(str(target_dir)):
            current_root = Path(root)
            if current_root == target_dir:
                continue
            for file in files:
                if file.endswith((".gguf", ".json", ".md", ".txt")):
                    src_path = current_root / file
                    dst_path = target_dir / file
                    if dst_path.exists():
                        continue
                    try:
                        import shutil

                        print(f"📂 [GGUF目录修复] 移动 {file} -> {target_dir}")
                        shutil.move(str(src_path), str(dst_path))
                    except Exception as e:
                        print(f"⚠️ GGUF目录修复失败: {src_path} -> {dst_path}: {e}")

    def ensure_model_downloaded(self) -> None:
        """供初始化阶段检查并按需下载 GGUF 中文纠错模型。"""
        try:
            path = self._resolve_model_path()
            print(f"✅ 本地 GGUF 纠错模型已就绪: {path}")
            return
        except Exception as e:
            print(f"⬇️ 未检测到本地 GGUF 纠错模型，准备下载: {e}")

        target_dir = self._download_target_dir()
        local_name = target_dir.name or DEFAULT_LLAMA_CPP_LOCAL_NAME
        try:
            from .stt_local_processor import download_model_with_progress

            target_dir.mkdir(parents=True, exist_ok=True)
            download_model_with_progress(
                str(self.model_id or DEFAULT_LLAMA_CPP_MODEL_ID),
                target_dir,
                local_name,
                revision=str(self.model_revision or DEFAULT_LLAMA_CPP_MODEL_REVISION),
            )
            self._fix_gguf_download_layout(target_dir)
            path = self._resolve_model_path()
            print(f"✅ 本地 GGUF 纠错模型下载完成: {path}")
        except Exception as e:
            raise RuntimeError(f"GGUF 中文纠错模型下载失败: {e}") from e

    # ---------- 模型加载 ----------

    def ensure_loaded(self) -> None:
        """懒加载模型；多线程安全。"""
        if self._llm is not None:
            return
        with self._init_lock:
            if self._llm is not None:
                return

            try:
                from llama_cpp import Llama
            except ImportError as e:
                raise RuntimeError(
                    "未安装 llama-cpp-python，请先 `pip install llama-cpp-python`"
                ) from e

            model_path = self._resolve_model_path()
            print(f"🔄 正在加载本地 GGUF 模型: {model_path}")
            kwargs: dict[str, Any] = {
                "model_path": model_path,
                "n_ctx": self.n_ctx,
                "n_gpu_layers": self.n_gpu_layers,
                "n_batch": self.n_batch,
                "verbose": self.verbose,
            }
            if self.n_threads:
                kwargs["n_threads"] = self.n_threads
            import time as _time
            _t0 = _time.perf_counter()
            self._llm = Llama(**kwargs)
            print(
                f"✅ 本地 GGUF 模型加载完成（n_gpu_layers={self.n_gpu_layers}, "
                f"n_batch={self.n_batch}, 耗时 {(_time.perf_counter() - _t0) * 1000:.0f}ms）"
            )

    def warm_up(self) -> None:
        """
        启动期预热：触发一次 dummy 推理，把首次 prompt eval 与 Metal pipeline 的代价
        吸收到启动期，避免用户第一次按热键改写时再等几秒。
        """
        if self._warm_done:
            return
        try:
            import time as _time
            _t0 = _time.perf_counter()
            self.ensure_loaded()
            _ = self.rewrite("少先队员因该为老人让坐。")
            self._warm_done = True
            print(
                f"🔥 本地 GGUF 模型预热完成，耗时 {(_time.perf_counter() - _t0):.2f}s"
            )
        except Exception as e:
            print(f"⚠️ 本地 GGUF 模型预热失败（可忽略）: {e}")

    # ---------- 业务方法 ----------

    def _build_user_prompt(self, raw_text: str) -> str:
        """构造与 MyVoiceTyping-1.5B 训练样本一致的 ASR 后处理输入。"""
        return _build_asr_post_user_prompt(raw_text)

    def _generation_max_tokens(self, raw_text: str) -> int:
        text_len = len((raw_text or "").strip())
        if text_len <= 0:
            return 1
        dynamic_limit = max(24, int(text_len * 1.4) + 8)
        return max(8, min(self.max_tokens, dynamic_limit))

    @staticmethod
    def _clean_output(text: str, raw_text: str = "") -> str:
        cleaned = (text or "").strip()
        for token in ("<|im_end|>", "<|endoftext|>"):
            if token in cleaned:
                cleaned = cleaned.split(token, 1)[0].strip()
        if cleaned.startswith("<think>"):
            end = cleaned.find("</think>")
            if end >= 0:
                cleaned = cleaned[end + len("</think>"):].strip()
        if not cleaned:
            return cleaned

        cleaned = cleaned.split("\n", 1)[0].strip()
        raw_text = (raw_text or "").strip()
        if raw_text:
            raw_pos = cleaned.find(raw_text)
            if raw_pos > 0:
                cleaned = cleaned[:raw_pos].strip()

        max_reasonable_len = max(len(raw_text) * 2 + 20, 120) if raw_text else 200
        if len(cleaned) > max_reasonable_len:
            for mark in ("。", "！", "？", ".", "!", "?"):
                pos = cleaned.find(mark)
                if 0 <= pos < max_reasonable_len:
                    cleaned = cleaned[:pos + 1].strip()
                    break
            else:
                cleaned = cleaned[:max_reasonable_len].strip()
        return cleaned

    def test(self) -> Optional[str]:
        """纠错连通性测试；成功返回 None。"""
        try:
            out = self.rewrite("少先队员因该为老人让坐。")
            print(f"本地 llama.cpp 纠错测试响应: {out}")
            if out:
                return None
            return "模型返回空结果"
        except Exception as e:
            return str(e)

    def rewrite(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            return raw_text
        import time as _time
        t0 = _time.perf_counter()
        self.ensure_loaded()
        max_tokens = self._generation_max_tokens(raw_text)
        out = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._build_user_prompt(raw_text)},
            ],
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            max_tokens=max_tokens,
        )
        content = out["choices"][0]["message"].get("content") or ""
        rewritten = self._clean_output(content, raw_text)
        print(
            f"🧹 本地 llama.cpp 纠错总耗时 {(_time.perf_counter() - t0):.2f}s "
            f"(max_tokens={max_tokens}, input_len={len(raw_text)})"
        )
        return rewritten
