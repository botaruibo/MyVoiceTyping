from pathlib import Path

from langchain_openai.chat_models import ChatOpenAI

import os


DOUBAO_API_KEY_LX = os.getenv("DOUBAO_API_KEY_LX")
DOUBAO_API_KEY_SENTRY = os.getenv("DOUBAO_API_KEY_SENTRY")

DOUBAO_URL = "https://ark-cn-beijing.bytedance.net/api/v3"

# 豆包体验账号
def doubao_reason_ty():
    return ChatOpenAI(
        model="bi-20251204160006-8d9cn",
        base_url=DOUBAO_URL,
        api_key="0db290bb-b681-4479-a5e3-a94202fac69b",
        temperature=0
    )

# 豆包 sentry账号
def doubao_reason_full():
    return ChatOpenAI(
        model="ep_20251210120313_s6zqt",
        base_url=DOUBAO_URL,
        api_key="39d5bdf1-9ad4-47ce-a0c4-ca6be862723f",
        temperature=0
    )

#豆包thinking模型，Doubao-Seed-1.5-thinking-pro-250415（立项）
def doubao_thinking():
    return ChatOpenAI(
        model="ep-20250707121510-cwx7h",
        base_url=DOUBAO_URL,
        api_key=DOUBAO_API_KEY_LX,
        temperature=0
    )

#豆包flash模型，Doubao-Seed-1.6-flash-250715（立项）
def doubao_flash():
    return ChatOpenAI(
        model="ep-20250812164048-pwfgk",
        base_url=DOUBAO_URL,
        api_key=DOUBAO_API_KEY_LX,
        temperature=0
    )

# 主函数，测试模型调用
if __name__ == "__main__":
    model = doubao_flash()
    response = model.invoke("今年几号")
    print(response.content)
#
#     # model2 = doubao_reason_full()
#     # response = model2.invoke("今年10月有哪些节日")
#     # print(response.content)
#     # print(response.content)