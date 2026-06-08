"""
文本重写模块 - 更新以使用新的配置

说明：
- 为了加速启动与 GUI 首次渲染，本模块默认不在 import/初始化阶段进行任何联网测试。
- 远程 LLM 客户端会在 GUI 就绪后的“后加载”阶段异步初始化，或在首次需要时懒加载。
"""

import argparse
import json
import os
import queue
import ssl
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
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

LOCAL_MLX_PROVIDERS = {"local_mlx_corrector", "local_mlx", "mlx"}


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

        self.rewrite_llm_client_status = False
        self.remote_llm_client = None
        self.local_llm_client = None

        self._remote_init_lock = threading.Lock()
        self._remote_init_started = False
        self._local_llama_cpp_init_lock = threading.Lock()
        self._local_llama_cpp_init_started = False
        self._local_mlx_corrector_init_lock = threading.Lock()
        self._local_mlx_corrector_init_started = False

    def init_remote_llm_async(self, reason: str = "") -> None:
        """
        /**
         * 异步初始化远程 LLM 客户端（不会阻塞调用方）。
         *
         * @param {string} reason - 触发原因（用于日志排查）。
         * @returns {void}
         */
        """
        print("====rewrite.0")
        with self._remote_init_lock:
            if self._remote_init_started:
                return
            self._remote_init_started = True

        def _worker() -> None:
            tag = f"reason={reason}" if reason else ""
            try:
                print(f"🌐 开始初始化远程文本改写模型 {tag}...")
                err = self.test_remote_llm()
                if err is None:
                    print("✅ 远程文本改写模型初始化完成")
                else:
                    print(f"⚠️ 远程文本改写模型初始化失败（将自动降级为不改写）: {err}")
            except Exception as e:
                print(f"⚠️ 远程文本改写模型初始化异常（将自动降级为不改写）: {e}")

            finally:
                # 重置初始化状态
                self._remote_init_started = False

        threading.Thread(target=_worker, daemon=True).start()

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
                if self.local_llm_client is None or not isinstance(
                    self.local_llm_client, LocalLlamaCppRewrite
                ):
                    self.local_llm_client = LocalLlamaCppRewrite()
                self.local_llm_client.warm_up()
                print("✅ 本地 llama.cpp 改写模型初始化完成")
            except Exception as e:
                # 失败不致命：rewrite() 时会再做懒加载
                print(f"⚠️ 本地 llama.cpp 改写模型初始化失败（运行期会重试）: {e}")
                with self._local_llama_cpp_init_lock:
                    self._local_llama_cpp_init_started = False

        threading.Thread(target=_worker, daemon=True).start()

    def init_local_mlx_corrector_async(self, reason: str = "") -> None:
        """异步初始化 LocalMLXCorrector 本地中文纠错模型。"""
        with self._local_mlx_corrector_init_lock:
            if self._local_mlx_corrector_init_started:
                return
            self._local_mlx_corrector_init_started = True

        def _worker() -> None:
            tag = f"reason={reason}" if reason else ""
            try:
                print(f"📝 开始初始化 LocalMLXCorrector 中文纠错模型 {tag}...")
                if self.local_llm_client is None or not isinstance(
                    self.local_llm_client, LocalMLXCorrector
                ):
                    self.local_llm_client = LocalMLXCorrector()
                self.local_llm_client.warm_up()
                print("✅ LocalMLXCorrector 中文纠错模型初始化完成")
            except Exception as e:
                print(f"⚠️ LocalMLXCorrector 中文纠错模型初始化失败（运行期会降级）: {e}")
                with self._local_mlx_corrector_init_lock:
                    self._local_mlx_corrector_init_started = False

        threading.Thread(target=_worker, daemon=True).start()

    def _create_chat_client(self):
        """创建 ChatOpenAI 客户端（延迟导入，避免启动时加载重型依赖）。"""
        from langchain_openai import ChatOpenAI

        api_key_str = self.config.get("API_KEY")
        model_name = self.config.get("MODEL_NAME")
        base_url = self.config.get("BASE_URL")
        temperature = _to_float(self.config.get("llm_temperature"), 0.2)
        timeout = _to_int(self.config.get("llm_timeout"), 15)
        max_tokens = _to_int(self.config.get("llm_max_tokens"), 1024)

        return ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key=api_key_str,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    def test_remote_llm(self) -> Optional[str]:
        """
        /**
         * 测试远程 LLM 是否可用；成功则缓存 client。
         *
         * 说明：
         * - 该方法会触发真实联网请求，适合在“用户点击测试”或“GUI 就绪后的后加载线程”调用。
         * - 不建议在应用启动早期（GUI 渲染前）调用。
         *
         * @returns {string | null} 失败原因；成功返回 null
         */
        """
        model_name = self.config.get("MODEL_NAME")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            test_client = self._create_chat_client()
            response = test_client.invoke(
                [
                    SystemMessage(content="你是一个测试助手，请直接返回 'OK'。"),
                    HumanMessage(content="测试连接"),
                ]
            )

            content = getattr(response, "content", "")
            print(f"模型 {model_name} 测试响应: {content}")

            if "ok" in str(content).lower():
                self.rewrite_llm_client_status = True
                self.remote_llm_client = test_client
                return None

            return f"模型返回非预期内容: {content}"
        except Exception as e:
            print(f"模型 {model_name} 测试失败: {e}")

            if "401" in str(e):
                return "API 密钥无效或已过期"
            if "timed out" in str(e).lower():
                return "请求超时，请检查网络或代理设置"
            if "error" in str(e).lower():
                return "测试失败"

            return f"连接失败: {e}"

    def test_llm(self) -> Optional[str]:
        """按当前 provider 测试文本改写模型。成功返回 None。"""
        provider = self.config.get("LLM_TEXT_PROVIDER")
        if provider == "cloud_llm":
            return self.test_remote_llm()

        if provider in {"ollama", "local_llm", "local_ollama"}:
            try:
                if self.local_llm_client is None:
                    self.local_llm_client = LocalLlamaRewrite()
                return self.local_llm_client.test_local_llama()
            except Exception as e:
                return str(e)

        if provider in {"llama_cpp", "local_llama_cpp", "gguf"}:
            try:
                if self.local_llm_client is None or not isinstance(
                    self.local_llm_client, LocalLlamaCppRewrite
                ):
                    self.local_llm_client = LocalLlamaCppRewrite()
                return self.local_llm_client.test()
            except Exception as e:
                return str(e)

        if provider in LOCAL_MLX_PROVIDERS:
            try:
                if self.local_llm_client is None or not isinstance(
                    self.local_llm_client, LocalMLXCorrector
                ):
                    self.local_llm_client = LocalMLXCorrector()
                return self.local_llm_client.test()
            except Exception as e:
                return str(e)

        return f"未知文本改写 provider: {provider}"

    def _rewrite_with_cloud_llm_single_turn(self, raw_text: str) -> str:
        """使用远程 LLM 进行单轮改写（要求 remote_llm_client 已就绪）。"""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=self.config.main_prompt),
            HumanMessage(content=raw_text),
        ]
        response = self.remote_llm_client.invoke(messages)
        return getattr(response, "content", "")

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
        if provider == "cloud_llm":
            if not self.rewrite_llm_client_status or self.remote_llm_client is None:
                print("⚠️ 远程文本格式化模型未就绪，本次直接返回原文")
                self.init_remote_llm_async(reason="rewrite")
                return raw_text

            try:
                return self._rewrite_with_cloud_llm_single_turn(raw_text)
            except Exception as e:
                print(f"⚠️ 文本改写失败（将降级返回原文）: {e}")
                return raw_text

        if provider in {"ollama", "local_llm", "local_ollama"}:
            try:
                if self.local_llm_client is None:
                    self.local_llm_client = LocalLlamaRewrite()
                return self.local_llm_client.rewrite(raw_text)
            except Exception as e:
                print(f"⚠️ 本地 Ollama 文本改写失败（将降级返回原文）: {e}")
                return raw_text

        if provider in {"llama_cpp", "local_llama_cpp", "gguf"}:
            try:
                if self.local_llm_client is None or not isinstance(
                    self.local_llm_client, LocalLlamaCppRewrite
                ):
                    self.local_llm_client = LocalLlamaCppRewrite()
                return self.local_llm_client.rewrite(raw_text)
            except Exception as e:
                print(f"⚠️ 本地 llama.cpp 文本改写失败（将降级返回原文）: {e}")
                return raw_text

        if provider in LOCAL_MLX_PROVIDERS:
            try:
                if self.local_llm_client is None or not isinstance(
                    self.local_llm_client, LocalMLXCorrector
                ):
                    self.local_llm_client = LocalMLXCorrector()
                return self.local_llm_client.rewrite(raw_text)
            except Exception as e:
                print(f"⚠️ LocalMLXCorrector 中文纠错失败（将降级返回原文）: {e}")
                return raw_text

        print(f"⚠️ 未知文本改写 provider: {provider}，直接返回原文")
        return raw_text

systemPrompt = (
    "文本纠错：\n"
)


class LocalMLXCorrector:
    """
    使用 mlx-lm 直接加载本地 MLX 量化模型做 ASR 后文本纠错。

    默认模型来自 `shibing624/chinese-text-correction-1.5b`，使用本项目生成的
    MLX 4bit 模型目录。
    """

    def __init__(self):
        self.config = get_config_manager()
        self.model_id = (
            self.config.get("local_mlx_corrector_model_id")
            or "shibing624/chinese-text-correction-1.5b"
        )
        quantized_path = self.config.get("local_mlx_corrector_model_path")
        self.quantized_model_path = (
            self._resolve_project_path(quantized_path) if quantized_path else None
        )
        self.max_new_tokens = _to_int(
            self.config.get("local_mlx_corrector_max_new_tokens"),
            96,
        )
        self.temperature = _to_float(
            self.config.get("local_mlx_corrector_temperature"),
            0.0,
        )
        self.top_p = _to_float(
            self.config.get("local_mlx_corrector_top_p"),
            1.0,
        )
        self.top_k = _to_int(
            self.config.get("local_mlx_corrector_top_k"),
            0,
        )
        self.require_quantized = bool(
            self.config.get("local_mlx_corrector_require_quantized")
            or False
        )
        self.prompt = str(
            self.config.get("local_mlx_corrector_prefix_prompt")
            or systemPrompt
        )
        self.prefetch_model = bool(
            self.config.get("local_mlx_corrector_prefetch_model_on_load")
            or True
        )

        self._model = None
        self._tokenizer = None
        self._load_lock = threading.Lock()
        self._warm_done = False
        self._mlx_queue: queue.Queue | None = None
        self._mlx_worker_thread: threading.Thread | None = None
        self._mlx_worker_ident: int | None = None
        self._mlx_worker_lock = threading.Lock()
        self._chat_template_warned = False

    @staticmethod
    def _resolve_project_path(raw_path: str) -> Path:
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

    def _ensure_quantized_path(self) -> Path:
        path = self.quantized_model_path
        if path is not None and path.exists() and path.is_dir():
            return path
        if self.require_quantized:
            raise FileNotFoundError(
                "未找到 LocalMLXCorrector 量化模型目录: "
                f"{path}。请先运行 "
                "`python scripts/quantize_chinese_error_corrector_4bit.py`。"
            )
        return Path(self.model_id)

    def _resolve_model_path(self) -> str:
        model_path = self._ensure_quantized_path()
        if model_path.exists():
            return str(model_path)

        if not self.prefetch_model:
            return self.model_id

        import time as _time

        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            return self.model_id

        t0 = _time.perf_counter()
        print(f"📦 检查/下载 LocalMLXCorrector 模型缓存: {self.model_id}")
        snapshot_path = snapshot_download(repo_id=self.model_id)
        print(
            f"📦 LocalMLXCorrector 模型缓存就绪，耗时 {(_time.perf_counter() - t0):.2f}s: "
            f"{snapshot_path}"
        )
        return snapshot_path

    def _ensure_mlx_worker(self) -> None:
        with self._mlx_worker_lock:
            if self._mlx_worker_thread is not None and self._mlx_worker_thread.is_alive():
                return

            self._mlx_queue = queue.Queue()

            def _worker() -> None:
                self._mlx_worker_ident = threading.get_ident()
                while True:
                    item = self._mlx_queue.get()
                    if item is None:
                        return
                    func, args, kwargs, done, result = item
                    try:
                        result["value"] = func(*args, **kwargs)
                    except Exception as e:
                        result["error"] = e
                    finally:
                        done.set()

            self._mlx_worker_thread = threading.Thread(
                target=_worker,
                name="LocalMLXCorrectorWorker",
                daemon=True,
            )
            self._mlx_worker_thread.start()

    def _run_on_mlx_worker(self, func, *args, **kwargs):
        if threading.get_ident() == self._mlx_worker_ident:
            return func(*args, **kwargs)

        self._ensure_mlx_worker()
        if self._mlx_queue is None:
            raise RuntimeError("MLX worker 未初始化")

        done = threading.Event()
        result: dict[str, Any] = {}
        self._mlx_queue.put((func, args, kwargs, done, result))
        done.wait()
        if "error" in result:
            raise result["error"]
        return result.get("value")

    def ensure_loaded(self) -> None:
        self._run_on_mlx_worker(self._ensure_loaded_current_thread)

    def _ensure_loaded_current_thread(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return

            import time as _time
            t0 = _time.perf_counter()
            model_path = self._ensure_quantized_path()
            print(f"🔄 正在加载 LocalMLXCorrector 中文纠错模型 path={model_path}")

            try:
                from mlx_lm import load
            except ImportError as e:
                raise RuntimeError(
                    "未安装 mlx-lm。请先执行 `pip install -r requirements.txt`，"
                    "再运行 4bit 量化脚本。"
                ) from e
            self._model, self._tokenizer = load(str(model_path))

            print(
                f"✅ LocalMLXCorrector 中文纠错模型加载完成，"
                f"耗时 {(_time.perf_counter() - t0):.2f}s"
            )

    def _build_correction_query(self, raw_text: str) -> str:
        query = f"{self.prompt}{raw_text}"
        if "纠错后" not in query:
            query = f"{query}\n纠错后："
        return query

    def _build_prompt(self, raw_text: str) -> str:
        query = self._build_correction_query(raw_text)
        messages = [{"role": "user", "content": query}]
        apply_chat_template = getattr(self._tokenizer, "apply_chat_template", None)
        chat_template = getattr(self._tokenizer, "chat_template", None)
        if callable(apply_chat_template) and chat_template:
            try:
                return apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
            except TypeError:
                return apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception as e:
                if not self._chat_template_warned:
                    print(f"⚠️ tokenizer chat_template 不可用，改用 Qwen 兼容纠错模板: {e}")
                    self._chat_template_warned = True
        elif not self._chat_template_warned:
            print("ℹ️ tokenizer 未提供 chat_template，使用 Qwen 兼容纠错模板")
            self._chat_template_warned = True

        # Qwen-style chat fallback for MLX-converted local models without chat_template.
        # The empty think block mirrors enable_thinking=False and avoids wasting tokens.
        return (
            "<|im_start|>user\n"
            f"{query}<|im_end|>\n"
            "<|im_start|>assistant\n"
            "<think>\n\n</think>\n\n"
        )

    def _generation_max_tokens(self, raw_text: str) -> int:
        text_len = len((raw_text or "").strip())
        if text_len <= 0:
            return 1
        dynamic_limit = max(24, int(text_len * 1.4) + 8)
        return max(8, min(self.max_new_tokens, dynamic_limit))

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

    def _rewrite_with_mlx(self, raw_text: str) -> str:
        import time as _time

        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        self._ensure_loaded_current_thread()
        t0 = _time.perf_counter()
        prompt = self._build_prompt(raw_text)
        max_tokens = self._generation_max_tokens(raw_text)
        output = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=make_sampler(
                temp=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
            ),
            verbose=False,
        )
        rewritten = self._clean_output(output, raw_text)
        print(
            f"🧹 LocalMLXCorrector 纠错耗时 {(_time.perf_counter() - t0):.2f}s "
            f"(max_tokens={max_tokens}, input_len={len(raw_text)})"
        )
        return rewritten

    def rewrite(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            return raw_text
        import time as _time
        t0 = _time.perf_counter()
        result = self._run_on_mlx_worker(self._rewrite_with_mlx, raw_text)
        print(f"🧹 LocalMLXCorrector 总耗时 {(_time.perf_counter() - t0):.2f}s")
        return result

    def warm_up(self) -> None:
        if self._warm_done:
            return
        try:
            import time as _time
            t0 = _time.perf_counter()
            _ = self.rewrite("少先队员因该为老人让坐。")
            self._warm_done = True
            print(f"🔥 LocalMLXCorrector 中文纠错模型预热完成，耗时 {(_time.perf_counter() - t0):.2f}s")
        except Exception as e:
            print(f"⚠️ LocalMLXCorrector 中文纠错模型预热失败（可忽略）: {e}")

    def test(self) -> Optional[str]:
        try:
            out = self.rewrite("少先队员因该为老人让坐。")
            print(f"LocalMLXCorrector 中文纠错测试响应: {out}")
            if out:
                return None
            return "模型返回空结果"
        except Exception as e:
            return str(e)


class LocalLlamaRewrite:
    """通过本地 OpenAI 兼容接口调用 Llama 模型进行文本改写。"""


    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        main_prompt: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ):
        self.config = get_config_manager()
        self.system_prompt = (
            main_prompt
            or self.config.main_prompt
            or systemPrompt
        )

        self.base_url = (
            base_url
            or self.config.get("ollama_base_url")
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("LOCAL_LLAMA_BASE_URL")
            or "http://127.0.0.1:11434"
        )
        self.model_name = (
            model_name
            or self.config.get("ollama_model")
            or self.config.get("local_llama_model")
            or os.getenv("OLLAMA_MODEL")
            or os.getenv("LOCAL_LLAMA_MODEL")
            or "qwen2.5:1.5b"
        )
        self.api_key = api_key
        if self.api_key is None:
            self.api_key = (
                self.config.get("ollama_api_key")
                or self.config.get("local_llama_api_key")
                or os.getenv("LOCAL_LLAMA_API_KEY")
                or "EMPTY"
            )

        self.timeout = timeout or _to_int(self.config.get("ollama_timeout"), 15)
        self.temperature = _to_float(self.config.get("ollama_temperature"), 0.2)
        self.num_predict = _to_int(self.config.get("ollama_num_predict"), 512)
        self.top_p = _to_float(self.config.get("ollama_top_p"), 1.0)
        self.top_k = _to_int(self.config.get("ollama_top_k"), 0)
        self.repeat_penalty = _to_float(self.config.get("ollama_repeat_penalty"), 1.0)
        configured_prefix = self.config.get("ollama_prefix_prompt")
        if configured_prefix is None and "chinese-text-correction" in str(self.model_name):
            configured_prefix = systemPrompt
        self.prefix_prompt = str(configured_prefix or "")
        self.chat_completion_url = self._normalize_chat_completion_url(self.base_url)
        self.tags_url = self._normalize_tags_url(self.base_url)
        self.verify_ssl = self._resolve_verify_ssl(verify_ssl)

        if not self.model_name:
            raise ValueError("未配置本地 Llama 模型名称，请通过 --model 或配置文件提供")

    @staticmethod
    def _to_bool(value: Any) -> Optional[bool]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return None

    @staticmethod
    def _is_local_host(hostname: Optional[str]) -> bool:
        if not hostname:
            return False
        return hostname.lower() in {"localhost", "127.0.0.1", "::1"}

    def _resolve_verify_ssl(self, verify_ssl: Optional[bool]) -> bool:
        cli_value = self._to_bool(verify_ssl)
        if cli_value is not None:
            return cli_value

        config_value = self._to_bool(
            self.config.get("LOCAL_LLAMA_VERIFY_SSL")
            or os.getenv("LOCAL_LLAMA_VERIFY_SSL")
        )
        if config_value is not None:
            return config_value

        parsed_url = urlparse(self.chat_completion_url)
        if parsed_url.scheme == "https" and self._is_local_host(parsed_url.hostname):
            return False
        return True

    def _build_ssl_context(self) -> Optional[ssl.SSLContext]:
        parsed_url = urlparse(self.chat_completion_url)
        if parsed_url.scheme != "https":
            return None

        if self.verify_ssl:
            return ssl.create_default_context()

        context = ssl._create_unverified_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    @staticmethod
    def _normalize_chat_completion_url(base_url: str) -> str:
        """将基础地址标准化为 Ollama 的 `/api/chat` 接口。"""
        normalized = base_url.rstrip("/")
        if normalized.endswith("/api/chat"):
            return normalized
        if normalized.endswith("/api/generate"):
            return f"{normalized[:-len('/api/generate')]}/api/chat"
        if normalized.endswith("/v1"):
            return f"{normalized[:-len('/v1')]}/api/chat"
        return f"{normalized}/api/chat"

    @staticmethod
    def _normalize_tags_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        for suffix in ("/api/chat", "/api/generate", "/v1"):
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        return f"{normalized}/api/tags"

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "LOCAL_LLAMA_VERIFY_SSL": "false",
        }
        if self.api_key and self.api_key != "EMPTY":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return {str(key): str(value) for key, value in headers.items()}

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        message = payload.get("message") or {}
        ollama_content = message.get("content")
        if isinstance(ollama_content, str):
            return ollama_content.strip()

        choices = payload.get("choices") or []
        if not choices:
            response_text = payload.get("response")
            if isinstance(response_text, str):
                return response_text.strip()
            raise ValueError(f"模型返回数据缺少可识别的消息字段: {payload}")

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts).strip()

        text = choices[0].get("text")
        if isinstance(text, str):
            return text.strip()

        raise ValueError(f"无法从模型返回中解析文本内容: {payload}")

    def _post_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        num_predict: Optional[int] = None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": self.temperature if temperature is None else temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
        }
        predict_limit = self.num_predict if num_predict is None else num_predict
        if predict_limit > 0:
            options["num_predict"] = predict_limit

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        request = urllib.request.Request(
            self.chat_completion_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._build_headers(),
            method="POST",
        )

        try:
            ssl_context = self._build_ssl_context()
            with urllib.request.urlopen(request, timeout=self.timeout, context=ssl_context) as response:
                response_text = response.read().decode("utf-8")
            print(f"本地 Llama 响应: {response_text}")
            return json.loads(response_text)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"本地 Llama 接口请求失败，HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", None)
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise RuntimeError(
                    "HTTPS 证书校验失败；如果这是本地自签名证书，请添加 `--insecure`，"
                    "或将 `LOCAL_LLAMA_VERIFY_SSL=false` 后重试"
                ) from e
            raise RuntimeError(f"无法连接到本地 Llama 接口: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"本地 Llama 接口返回了无法解析的 JSON: {e}") from e

    def _get_model_tags(self) -> list[str]:
        request = urllib.request.Request(
            self.tags_url,
            headers=self._build_headers(),
            method="GET",
        )
        try:
            ssl_context = self._build_ssl_context()
            with urllib.request.urlopen(request, timeout=self.timeout, context=ssl_context) as response:
                response_text = response.read().decode("utf-8")
            payload = json.loads(response_text)
        except urllib.error.URLError as e:
            raise RuntimeError(f"无法连接到本地 Ollama 服务: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Ollama 模型列表返回了无法解析的 JSON: {e}") from e

        models = payload.get("models") or []
        names: list[str] = []
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        return names

    def _ensure_model_available(self) -> Optional[str]:
        names = self._get_model_tags()
        if self.model_name in names:
            return None
        return (
            f"本地 Ollama 模型不存在: {self.model_name}。"
            f"请先执行 `ollama pull {self.model_name}`。"
        )

    def _build_user_prompt(self, raw_text: str) -> str:
        if self.prefix_prompt and not raw_text.startswith(self.prefix_prompt):
            return f"{self.prefix_prompt}{raw_text}\n纠错后："
        return raw_text

    def _generation_max_tokens(self, raw_text: str) -> int:
        text_len = len((raw_text or "").strip())
        if text_len <= 0:
            return 1
        dynamic_limit = max(24, int(text_len * 1.4) + 8)
        return max(8, min(self.num_predict, dynamic_limit))

    @staticmethod
    def _clean_correction_output(text: str, raw_text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return cleaned

        raw_text = (raw_text or "").strip()
        max_len = max(len(raw_text) * 2 + 20, 80) if raw_text else 120
        banned = (
            "输入", "输出", "答案", "故答案", "所以", "根据", "请", "只输出",
            "不要其他内容", "修改是", "改为", "判断对错",
        )

        candidates: list[str] = []
        for line in cleaned.replace("\r", "\n").split("\n"):
            line = line.strip(" \t-：:，,")
            if not line or any(mark in line for mark in banned):
                continue
            candidates.append(line)
            for mark in ("。", "！", "？", ".", "!", "?"):
                if mark in line:
                    first = line.split(mark, 1)[0].strip()
                    if first:
                        candidates.append(first + mark)
                    break

        if not candidates:
            candidates = [cleaned.split("\n", 1)[0].strip()]

        raw_chars = set(raw_text)

        def score(candidate: str) -> float:
            candidate = candidate.strip()
            if not candidate:
                return -1e9
            overlap = sum(1 for ch in candidate if ch in raw_chars)
            length_penalty = abs(len(candidate) - len(raw_text)) * 0.35
            instruction_penalty = 20 if any(mark in candidate for mark in banned) else 0
            long_penalty = max(0, len(candidate) - max_len) * 0.5
            return overlap - length_penalty - instruction_penalty - long_penalty

        best = max(candidates, key=score).strip()
        if len(best) > max_len:
            best = best[:max_len].strip()
        return best

    def test_local_llama(self) -> Optional[str]:
        """测试本地 Llama 接口是否可用。成功返回 `None`，失败返回错误信息。"""
        try:
            model_error = self._ensure_model_available()
            if model_error is not None:
                return model_error

            if self.prefix_prompt:
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self._build_user_prompt("少先队员因该为老人让坐。")},
                ]
            else:
                messages = [
                    {"role": "system", "content": "你是一个连接测试助手，请只返回 OK。"},
                    {"role": "user", "content": "测试连接"},
                ]

            payload = self._post_chat_completion(messages, temperature=0)
            content = self._extract_message_content(payload)
            if self.prefix_prompt:
                content = self._clean_correction_output(content, "少先队员因该为老人让坐。")
            print(f"本地 Llama 测试响应: {content}")
            if self.prefix_prompt and content:
                return None
            if "ok" in content.lower():
                return None
            return f"模型返回非预期内容: {content}"
        except Exception as e:
            return str(e)

    def rewrite(self, raw_text: str) -> str:
        """使用本地 Llama 对文本进行一次改写。"""
        if not raw_text.strip():
            return raw_text

        payload = self._post_chat_completion(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._build_user_prompt(raw_text)},
            ],
            num_predict=self._generation_max_tokens(raw_text),
        )
        content = self._extract_message_content(payload)
        if self.prefix_prompt:
            return self._clean_correction_output(content, raw_text)
        return content


def main() -> int:
    """命令行测试入口：验证本地 Llama 接口连通性并输出改写结果。"""
    parser = argparse.ArgumentParser(description="测试本地 Llama 文本改写接口")
    parser.add_argument(
        "--text",
        default="今天下午的需求评审内容很多 我先记一下 晚点整理成正式纪要发给你",
        help="需要发送给本地 Llama 改写的原始文本",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LOCAL_LLAMA_BASE_URL"),
        help="本地 Llama 服务地址，例如 http://127.0.0.1:8000 或 http://127.0.0.1:11434/v1",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LOCAL_LLAMA_MODEL"),
        help="本地 Llama 模型名称，例如 llama-3.1-8b-instruct 或 qwen3:8b",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LOCAL_LLAMA_API_KEY"),
        help="OpenAI 兼容接口的鉴权信息；多数本地服务可留空",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="请求超时时间（秒）",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="关闭 HTTPS 证书校验，适合本地自签名证书服务",
    )
    args = parser.parse_args()

    rewriter = LocalLlamaRewrite(
        base_url=args.base_url,
        model_name=args.model,
        api_key=args.api_key,
        timeout=args.timeout,
        verify_ssl=False if args.insecure else None,
    )

    error = rewriter.test_local_llama()
    if error is not None:
        print(f"❌ 本地 Llama 连接测试失败: {error}")
        return 1

    rewritten_text = rewriter.rewrite(args.text)

    print("\n===== 本地 Llama 文本改写测试 =====")
    print(f"接口地址: {rewriter.chat_completion_url}")
    print(f"模型名称: {rewriter.model_name}")
    print(f"原始文本: {args.text}")
    print(f"改写结果: {rewritten_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# LocalLlamaCppRewrite: 直接通过 llama-cpp-python 加载本地 GGUF 模型做文本改写。
#
# 设计目标：
# - 不依赖 ollama HTTP daemon，进程内直接 mmap GGUF 权重做推理。
# - 模型权重复用 ~/.ollama/models 下已有 blob，无需重新下载。
# - 与现有 Rewrite 分发解耦：通过 `llm_text_provider="llama_cpp"` 选用。
# - 重型加载放到首次调用时懒执行，启动期不阻塞。
# ---------------------------------------------------------------------------


class LocalLlamaCppRewrite:
    """
    /**
     * 通过 llama-cpp-python 直接加载本地 GGUF 模型进行文本改写。
     *
     * 不通过 ollama HTTP 服务，自行解析 ollama manifest 拿到 GGUF blob 路径。
     */
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        ollama_model_tag: Optional[str] = None,
        n_ctx: Optional[int] = None,
        n_threads: Optional[int] = None,
        main_prompt: Optional[str] = None,
    ):
        self.config = get_config_manager()
        self.system_prompt = (
            main_prompt
            or self.config.main_prompt
            or systemPrompt
        )

        # 优先级：显式传参 > 配置 llama_cpp_model_path > 从 ollama 模型 tag 解析
        self.model_path: Optional[str] = (
            model_path
            or self.config.get("llama_cpp_model_path")
            or os.getenv("LLAMA_CPP_MODEL_PATH")
        )
        self.ollama_model_tag: Optional[str] = (
            ollama_model_tag
            or self.config.get("llama_cpp_ollama_tag")
            or self.config.get("ollama_model")
            or os.getenv("LLAMA_CPP_OLLAMA_TAG")
        )

        self.n_ctx = _to_int(n_ctx or self.config.get("llama_cpp_n_ctx"), 4096)
        self.n_threads = _to_int(n_threads or self.config.get("llama_cpp_n_threads"), 0) or None
        self.temperature = _to_float(self.config.get("llama_cpp_temperature"), 0.2)
        self.max_tokens = _to_int(self.config.get("llama_cpp_max_tokens"), 1024)
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
    def _parse_ollama_tag(tag: str) -> tuple[str, str]:
        """`name:variant` -> (`name`, `variant`)，缺省 variant 视为 `latest`。"""
        if ":" in tag:
            name, variant = tag.split(":", 1)
            return name.strip(), variant.strip() or "latest"
        return tag.strip(), "latest"

    def _resolve_gguf_from_ollama(self, tag: str) -> str:
        """
        /**
         * 从 ollama 本地 manifest 中找到 GGUF blob 路径。
         *
         * 目录约定：~/.ollama/models/manifests/registry.ollama.ai/library/<name>/<variant>
         * manifest 内 layers 中 mediaType 为 application/vnd.ollama.image.model 的层即模型文件。
         */
        """
        name, variant = self._parse_ollama_tag(tag)

        ollama_root = Path(os.getenv("OLLAMA_MODELS") or (Path.home() / ".ollama" / "models"))
        manifest = (
            ollama_root
            / "manifests"
            / "registry.ollama.ai"
            / "library"
            / name
            / variant
        )
        if not manifest.exists():
            raise FileNotFoundError(
                f"未找到 ollama manifest: {manifest}（tag={tag}）"
            )

        with manifest.open("r", encoding="utf-8") as fp:
            manifest_data = json.load(fp)

        layers = manifest_data.get("layers") or []
        model_layer = next(
            (l for l in layers if l.get("mediaType") == "application/vnd.ollama.image.model"),
            None,
        )
        if not model_layer:
            raise RuntimeError(f"manifest 中没有 model 层: {manifest}")

        digest = model_layer.get("digest") or ""
        if not digest.startswith("sha256:"):
            raise RuntimeError(f"无法识别的 digest: {digest}")

        blob_path = ollama_root / "blobs" / digest.replace(":", "-")
        if not blob_path.exists():
            raise FileNotFoundError(f"GGUF blob 不存在: {blob_path}")
        return str(blob_path)

    def _resolve_model_path(self) -> str:
        if self.model_path and Path(self.model_path).exists():
            return self.model_path
        if self.ollama_model_tag:
            return self._resolve_gguf_from_ollama(self.ollama_model_tag)
        raise FileNotFoundError(
            "未配置 llama_cpp_model_path 或 ollama 模型 tag，无法定位 GGUF 权重"
        )

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

        - 复用真实的 system_prompt，使首次 KV cache 与权重内存映射也被加载到 page cache。
        - max_tokens 设小（4），避免预热本身耗时过长。
        """
        if self._warm_done:
            return
        try:
            import time as _time
            _t0 = _time.perf_counter()
            self.ensure_loaded()
            _ = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "你好"},
                ],
                temperature=0,
                max_tokens=4,
            )
            self._warm_done = True
            print(
                f"🔥 本地 GGUF 模型预热完成，耗时 {(_time.perf_counter() - _t0):.2f}s"
            )
        except Exception as e:
            print(f"⚠️ 本地 GGUF 模型预热失败（可忽略）: {e}")

    # ---------- 业务方法 ----------

    def test(self) -> Optional[str]:
        """简单连通性测试；成功返回 None。"""
        try:
            self.ensure_loaded()
            out = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "你是连接测试助手，请只返回 OK。"},
                    {"role": "user", "content": "测试连接"},
                ],
                temperature=0,
                max_tokens=8,
            )
            content = (out["choices"][0]["message"].get("content") or "").strip()
            print(f"本地 llama.cpp 测试响应: {content}")
            if "ok" in content.lower():
                return None
            return f"模型返回非预期内容: {content}"
        except Exception as e:
            return str(e)

    def rewrite(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            return raw_text
        self.ensure_loaded()
        out = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": raw_text},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = out["choices"][0]["message"].get("content") or ""
        return content.strip()
