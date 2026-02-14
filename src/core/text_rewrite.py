"""
文本重写模块 - 更新以使用新的配置
"""
from langchain_openai import ChatOpenAI
from ..utils.config_manager import get_config_manager
from ..prompts import get_format_text_prompt_template
from langchain_core.messages import HumanMessage, SystemMessage

_instance = None

def get_rewriter():
    """
    获取 Rewrite 的全局唯一实例。

    :return: Rewrite 实例
    """
    global _instance
    if _instance is None:
        _instance = Rewrite()
    return _instance


class Rewrite:
    def __init__(self):
        self.config = get_config_manager()  # 使用新的配置管理器
        # 初始化时默认认为模型不可用
        self.rewrite_llm_client_status = False
        self.remote_llm_client = None
        self._init_remote_llm_client()


    def test_remote_llm(self):
        """测试所有远程LLM模型"""
        api_key_str = self.config.get("API_KEY")
        model_name = self.config.get("MODEL_NAME")
        try:
            test_client = ChatOpenAI(
                model=model_name,
                base_url=self.config.get("BASE_URL"),
                api_key=api_key_str,  # 确保是字符串类型
                temperature=0.6,
                timeout=10,  # 设置请求超时
            )
            response = test_client.invoke([
                SystemMessage(content="你是一个测试助手，请直接返回 'OK'。"),
                HumanMessage(content="测试连接")
            ])
            print(f"模型 {model_name} 测试响应: {response.content}")
            if "ok" in response.content.lower():
                # 测试成功，保存客户端
                self.rewrite_llm_client_status = True
                self.remote_llm_client = test_client
                return None  # 测试成功
            else:
                return f"模型返回非预期内容: {response.content}"
        except Exception as e:
            print(f"模型 {model_name} 测试失败: {e}")

            # 根据异常类型可以提供更具体的错误信息
            if "401" in str(e):
                return "API 密钥无效或已过期"
            elif "timed out" in str(e).lower():
                return "请求超时，请检查网络或代理设置"
            elif "error" in str(e).lower():
                return "测试失败"
            else:
                return f"连接失败: {e}"

    def _init_remote_llm_client(self):
        """初始化远程LLM提供者"""
        self.test_remote_llm()


    def _rewrite_with_cloud_llm_single_turn(self, raw_text):
        """
        使用远程LLM进行语义重构.会使用单个模型改写文本
        """
        messages = [
            SystemMessage(content=get_format_text_prompt_template()),
            HumanMessage(content=raw_text)
        ]
        response = self.remote_llm_client.invoke(messages)
        return response.content

    def rewrite(self, raw_text):
        """
        结构化改写文本
        """
        if not self.config.get("FORMAT_TEXT") or not self.rewrite_llm_client_status:
            print("⚠️未配置文本格式化模型或模型不可用")
            return raw_text

        provider = self.config.get("LLM_TEXT_PROVIDER")
        if provider == 'cloud_llm':
            return self._rewrite_with_cloud_llm_single_turn(raw_text)
        else:
            print(f"⚠️不支持未知的重写模式: {provider}")
            return raw_text


if __name__ == "__main__":
    rewriter = Rewrite()
    raw_text = "你好，我想购买一个商品括号占时。"
    result = rewriter.rewrite(raw_text)
    print(result)