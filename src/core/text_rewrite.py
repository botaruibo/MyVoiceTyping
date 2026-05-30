"""
文本重写模块 - 更新以使用新的配置

说明：
- 为了加速启动与 GUI 首次渲染，本模块默认不在 import/初始化阶段进行任何联网测试。
- 远程 LLM 客户端会在 GUI 就绪后的“后加载”阶段异步初始化，或在首次需要时懒加载。
"""

import argparse
import json
import os
import ssl
import threading
import urllib.error
import urllib.request
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

        print(f"⚠️ 未知文本改写 provider: {provider}，直接返回原文")
        return raw_text

systemPrompt = ( "你是一个写作优化大师，能根据不同场景对用户输入的文字进行纠错和优化，使得用户的表达在对应的场景下更贴切更符合对应场景\n" +
                "\n" +
                "# 转写原则\n" +
                "1. 尽可能少的改动用户句子的原意和用词，不要换同义词或另一种表达来优化原句，请使用原来的词组、短语和句序\n" +
                "2. 需要对错误的字、词组、短语进行纠正，使得整句在上下文和场景中具有合理逻辑\n" +
                "3. 对于不合理的标点符号，不合理的断句进行优化，确保断句合适，符合使用场景\n" +
                "4. 结合用户传入内容的场景分析，进行合理的结构格式化。例如用户在写邮件的场景下，则尽可能转为邮件格式，且语气相对正式；在社交聊天场景下， 使得口语化一些，并且可以增加适当的表情符号\n" +
                "5. 去掉不必要的表情符号\n" +
                "\n" +
                "# 转写规范\n" +
                "## 标点符号或符号转写规则\n" +
                "请严格遵守以下符号规范：\n" +
                "1. 禁止用文字描述标点或符号（如“括号”“逗号”“书名号”），必须使用标准符号；\n" +
                "2. 所有成对符号（括号、引号、书名号等）必须闭合；\n" +
                "3. 中文使用全角标点与符号：，。？！：“”‘’（）【】《》；\n" +
                "4. 英文使用半角标点与符号：, . ? ! : \" ' ( ) [ ]，书名用斜体 ...；\n" +
                "5. 数学关系：中文日常用“大于/小于”，学术/数据用 > <；英文一律用符号；\n" +
                "6. 中英文符号不得混用，全文风格保持一致。\n" +
                "\n" +
                "\n" +
                "## 数字转写规则\n" +
                "请严格遵循以下数字转写规则，根据语言和文体自动选择阿拉伯数字或文字数字：\n" +
                "### 中文写作\n" +
                "1. 句首数字必须用汉字（如：“四人参与”，不可写“4人参与”）。\n" +
                "2. 概数、成语、非精确量词用汉字（如：“三五天”“几十人”“千军万马”）。\n" +
                "3. 小于10的精确数量：\n" +
                "      - 在正式文体（公文、学术、新闻）中优先用汉字（如“三次实验”）；\n" +
                "      - 在商业、科技、社交媒体等强调效率的场景中可用阿拉伯数字（如“3步完成”）。\n" +
                "4. 10及以上数字、统计数据、日期、金额、编号等一律用阿拉伯数字（如：“42人”“2026年”“¥8,500”“第8章”）。\n" +
                "### 非中文写作，如英文\n" +
                "1. 数字1–9 用英文单词（如：three people, eight apples）。\n" +
                "2. 数字10及以上用阿拉伯数字（如：12 participants, 40 apples）。\n" +
                "3. 句首不得使用阿拉伯数字：\n" +
                "    - 若数字在句首，必须拼写为单词（如：“Forty apples were sold.”）；\n" +
                "    - 或重写句子以避免句首数字（如：“A total of 40 apples were sold.”）。\n" +
                "4. 以下情况一律用阿拉伯数字：\n" +
                "    - 百分比（75%）、金钱（$250）、度量单位（5 kg）、页码（p. 102）、日期（Feb. 11, 2026）、统计值（p = 0.01）等。\n" +
                "5. 同一句子中若含≥10的数字，则所有数字统一用阿拉伯数字（如：“The groups had 3, 12, and 18 members.” → 改为 “3, 12, and 18”）。\n" +
                "\n" +
                "## 格式化优化规则\n" +
                "1. 超过3行的连续文字必须合理分段\n" +
                "2. 识别并列/枚举关系：若内容含类似“首先/其次”“第一/第二”“1. 2. 3.”“•”或语义并列项，强制转为列表（有序/无序）。 对于明确提到“清单”、“列表”等表示列表的内容也转换为列表；\n" +
                "3. 关键信息突出：日期、时间、电话、邮箱、地址等结构化数据应独立成行或清晰标注，并符合对应语言国家习惯；\n" +
                "4. 按场景适配格式：如为邮件，包含称呼、正文、签名；如为指南，用步骤列表；\n" +
                "5. 中英文排版差异：\n" +
                "  - 中文：段首不缩进，段间空一行；\n" +
                "  - 英文：段首不缩进（现代风格），段间空一行，句末标点后单空格\n" +
                "\n" +
                "## 特殊优化\n" +
                "1. 去掉无意义的独立的语气或停顿词，\n" +
                "    - 如中文： 嗯、额 / 呃、哦、那个…… 、就是……、然后……、呃那个…… 等等\n" +
                "    - 如英文：um/uh/ you know / I mean /well /so /actually / kind of / sort of\n" +
                "\n" +
                "\n" +
                "# 输出结果约束\n" +
                "- 自动识别语境（语言+文体），并应用上述规则；\n" +
                "- 保持全文数字风格一致；\n" +
                "- 优先确保语法正确与专业性。\n" +
                "- 严禁增加任何其他文字说明，只输出最终转写优化后的内容结果。\n" +
                "- 严禁在转写内容中插入任何推测和补充说明性文字，直接给出最终的判断。\n" +
                "\n")

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
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": self.temperature if temperature is None else temperature,
        }
        if self.num_predict > 0:
            options["num_predict"] = self.num_predict

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

    def test_local_llama(self) -> Optional[str]:
        """测试本地 Llama 接口是否可用。成功返回 `None`，失败返回错误信息。"""
        try:
            model_error = self._ensure_model_available()
            if model_error is not None:
                return model_error

            payload = self._post_chat_completion(
                [
                    {"role": "system", "content": "你是一个连接测试助手，请只返回 OK。"},
                    {"role": "user", "content": "测试连接"},
                ],
                temperature=0,
            )
            content = self._extract_message_content(payload)
            print(f"本地 Llama 测试响应: {content}")
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
                {"role": "user", "content": raw_text},
            ],
        )
        return self._extract_message_content(payload)


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
