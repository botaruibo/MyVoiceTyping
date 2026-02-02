"""
文本重写模块 - 更新以使用新的配置
"""
from langchain_openai import ChatOpenAI
from ..config import Config
from ..prompts import get_fin_prompt_template


class Rewrite:
    def __init__(self):
        self.config = Config()  # 使用新的配置管理器
        self.remote_clients = self._init_remote_llm()

    def _init_remote_llm(self):
        """初始化远程LLM提供者"""
        try:
            api_key_str = self.config.API_KEY
            models = self.config.REMOTE_LLM_MODELS
            remote_clients = {}

            for model_name in models:
                client = ChatOpenAI(
                    model=model_name,
                    base_url=self.config.BASE_URL,
                    api_key=api_key_str,  # 确保是字符串类型
                    temperature=0.3
                )
                remote_clients[model_name] = client

            return remote_clients
        except ImportError as e:
            raise ValueError(f"链接远程LLM提供者失败: {e}")

    def _rewrite_with_remote_llm(self, raw_text):
        """使用远程LLM进行语义重构"""

        from langchain_core.messages import HumanMessage, SystemMessage
        import asyncio
        # 使用初始化好的客户端数组进行调用
        results = {}
        messages = [
            SystemMessage(content=get_fin_prompt_template()),
            HumanMessage(content=raw_text)
        ]

        for model_name, client in self.remote_clients.items():  # 修改这里，使用.items()

            print(f"正在调用远程LLM模型: {model_name}")
            try:
                response = client.invoke(messages)
                results[model_name] = response.content
                print(f"LLM模型 {model_name} 结果：{response.content}")
            except Exception as e:
                print(f"调用远程LLM模型 {model_name} 出错: {e}")

        # 如果有多个结果，评估选择最佳结果
        if len(results) > 1:
            best_result = self._evaluate_results(results, raw_text)
            return best_result
        elif len(results) == 1:
            return list(results.values())[0]
        else:
            return raw_text

    def _rewrite_with_ollama(self, raw_text):
        """使用Ollama进行语义重构"""
        try:
            import requests

            ollama_url = "http://localhost:11434/api/generate"
            payload = {
                "model": self.config.OLLAMA_MODEL,
                "prompt": f"请优化以下文本，使其更通顺、准确：\n\n{raw_text}",
                "stream": False
            }

            response = requests.post(ollama_url, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', raw_text)
            else:
                print(f"Ollama请求失败: {response.status_code}")
                return raw_text
        except ImportError:
            print("请安装requests: pip install requests")
            return raw_text
        except Exception as e:
            print(f"Ollama重写出错: {e}")
            return raw_text

    def rewrite(self, raw_text):
        """执行语义重构"""
        if not self.config.USE_REWRITE:
            return raw_text

        if self.config.REWRITE_MODE == 'ollama':
            return self._rewrite_with_ollama(raw_text)
        elif self.config.REWRITE_MODE == 'remote_llm':
            return self._rewrite_with_remote_llm(raw_text)
        else:
            print(f"未知的重写模式: {self.config.REWRITE_MODE}")
            return raw_text

    def _evaluate_results(self, results, original_text):
        """评估多个模型的重写结果"""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            # 构建评估内容
            eval_content = "{"
            for i, (model_name, result) in enumerate(results.items(), 1):
                eval_content += f'    "S{i}": "{result}",\n'
            eval_content = eval_content.rstrip(',\n') + "}"

            evaluation_prompt = f'你是一个语言专家,你需要对用户输入的内容进行评估，对以下重写结果S1, S2等，基于完整性和语法语义等选出最好的一个，最后只输出最好的一个，不需要其他任何解释。输出格式为：{{"S1": "xxx"}}或{{"S2": "xxx"}}'

            messages = [
                SystemMessage(content=evaluation_prompt),
                HumanMessage(content=eval_content)
            ]

            print("正在评估重写结果...")
            # 获取字典中的第一个模型客户端并调用invoke方法
            first_client = next(iter(self.remote_clients.values()))
            response = first_client.invoke(messages)

            # 解析返回结果，提取最佳结果
            eval_response = response.content.strip()
            for i, (model_name, result) in enumerate(results.items(), 1):
                if f'"S{i}"' in eval_response:
                    print(f"评估选择结果来自模型: {model_name}")
                    return result

            # 如果解析失败，返回第一个结果
            print("评估解析失败，返回第一个结果")
            return list(results.values())[0]
        except Exception as e:
            print(f"评估重写结果时出错: {e}")
            # 出错时返回第一个结果
            return list(results.values())[0]