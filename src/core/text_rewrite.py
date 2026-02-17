"""
文本重写模块 - 更新以使用新的配置

说明：
- 为了加速启动与 GUI 首次渲染，本模块默认不在 import/初始化阶段进行任何联网测试。
- 远程 LLM 客户端会在 GUI 就绪后的“后加载”阶段异步初始化，或在首次需要时懒加载。
"""

import threading
from typing import Optional

from ..utils.config_manager import get_config_manager
from ..prompts import get_format_text_prompt_template

_instance = None
_instance_lock = threading.Lock()


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

        threading.Thread(target=_worker, daemon=True).start()

    def _create_chat_client(self):
        """创建 ChatOpenAI 客户端（延迟导入，避免启动时加载重型依赖）。"""
        from langchain_openai import ChatOpenAI

        api_key_str = self.config.get("API_KEY")
        model_name = self.config.get("MODEL_NAME")
        base_url = self.config.get("BASE_URL")

        return ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key=api_key_str,
            temperature=0.6,
            timeout=10,
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

    def _rewrite_with_cloud_llm_single_turn(self, raw_text: str) -> str:
        """使用远程 LLM 进行单轮改写（要求 remote_llm_client 已就绪）。"""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=get_format_text_prompt_template()),
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
            return raw_text

        if not self.rewrite_llm_client_status or self.remote_llm_client is None:
            print("⚠️ 文本格式化模型未就绪，本次直接返回原文")
            self.init_remote_llm_async(reason="rewrite")
            return raw_text

        provider = self.config.get("LLM_TEXT_PROVIDER")
        if provider == "cloud_llm":
            try:
                return self._rewrite_with_cloud_llm_single_turn(raw_text)
            except Exception as e:
                print(f"⚠️ 文本改写失败（将降级返回原文）: {e}")
                return raw_text

        print(f"⚠️ 不支持未知的重写模式: {provider}（将降级返回原文）")
        return raw_text