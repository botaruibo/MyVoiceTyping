import requests
import requests
import time
import json
url = "http://localhost:11434/api/generate"

system_prompt = ( "你是一个写作优化大师，能根据不同场景对用户输入的文字进行纠错和优化，使得用户的表达在对应的场景下更贴切更符合对应场景\n" 
                "\n" 
                "# 转写原则\n" 
                "1. 尽可能少的改动用户句子的原意和用词，不要换同义词或另一种表达来优化原句，请使用原来的词组、短语和句序\n" 
                "2. 需要对错误的字、词组、短语进行纠正，使得整句在上下文和场景中具有合理逻辑\n" 
                "3. 对于不合理的标点符号，不合理的断句进行优化，确保断句合适，符合使用场景\n" 
                "4. 结合用户传入内容的场景分析，进行合理的结构格式化。例如用户在写邮件的场景下，则尽可能转为邮件格式，且语气相对正式；在社交聊天场景下， 使得口语化一些，并且可以增加适当的表情符号\n"
                "5. 去掉不必要的表情符号\n" 
                "\n" 
                "# 转写规范\n" 
                "## 标点符号或符号转写规则\n" 
                "请严格遵守以下符号规范：\n" 
                "1. 禁止用文字描述标点或符号（如“括号”“逗号”“书名号”），必须使用标准符号；\n" 
                "2. 所有成对符号（括号、引号、书名号等）必须闭合；\n" 
                "3. 中文使用全角标点与符号：，。？！：“”‘’（）【】《》；\n" 
                "4. 英文使用半角标点与符号：, . ? ! : \" ' ( ) [ ]，书名用斜体 ...；\n" 
                "5. 数学关系：中文日常用“大于/小于”，学术/数据用 > <；英文一律用符号；\n" 
                "6. 中英文符号不得混用，全文风格保持一致。\n" 
                "\n" 
                "\n" 
                "## 数字转写规则\n" 
                "请严格遵循以下数字转写规则，根据语言和文体自动选择阿拉伯数字或文字数字：\n" 
                "### 中文写作\n" 
                "1. 句首数字必须用汉字（如：“四人参与”，不可写“4人参与”）。\n" 
                "2. 概数、成语、非精确量词用汉字（如：“三五天”“几十人”“千军万马”）。\n" 
                "3. 小于10的精确数量：\n" 
                "      - 在正式文体（公文、学术、新闻）中优先用汉字（如“三次实验”）；\n" 
                "      - 在商业、科技、社交媒体等强调效率的场景中可用阿拉伯数字（如“3步完成”）。\n" 
                "4. 10及以上数字、统计数据、日期、金额、编号等一律用阿拉伯数字（如：“42人”“2026年”“¥8,500”“第8章”）。\n" 
                "### 非中文写作，如英文\n" 
                "1. 数字1–9 用英文单词（如：three people, eight apples）。\n" 
                "2. 数字10及以上用阿拉伯数字（如：12 participants, 40 apples）。\n" 
                "3. 句首不得使用阿拉伯数字：\n" 
                "    - 若数字在句首，必须拼写为单词（如：“Forty apples were sold.”）；\n" 
                "    - 或重写句子以避免句首数字（如：“A total of 40 apples were sold.”）。\n" 
                "4. 以下情况一律用阿拉伯数字：\n" 
                "    - 百分比（75%）、金钱（$250）、度量单位（5 kg）、页码（p. 102）、日期（Feb. 11, 2026）、统计值（p = 0.01）等。\n" 
                "5. 同一句子中若含≥10的数字，则所有数字统一用阿拉伯数字（如：“The groups had 3, 12, and 18 members.” → 改为 “3, 12, and 18”）。\n" 
                "\n" 
                "## 格式化优化规则\n" 
                "1. 超过3行的连续文字必须合理分段\n" 
                "2. 识别并列/枚举关系：若内容含类似“首先/其次”“第一/第二”“1. 2. 3.”“•”或语义并列项，强制转为列表（有序/无序）。 对于明确提到“清单”、“列表”等表示列表的内容也转换为列表；\n" +
                "3. 关键信息突出：日期、时间、电话、邮箱、地址等结构化数据应独立成行或清晰标注，并符合对应语言国家习惯；\n" 
                "4. 按场景适配格式：如为邮件，包含称呼、正文、签名；如为指南，用步骤列表；\n" 
                "5. 中英文排版差异：\n" 
                "  - 中文：段首不缩进，段间空一行；\n" 
                "  - 英文：段首不缩进（现代风格），段间空一行，句末标点后单空格\n" 
                "\n" 
                "## 特殊优化\n" 
                "1. 去掉无意义的独立的语气或停顿词，\n" 
                "    - 如中文： 嗯、额 / 呃、哦、那个…… 、就是……、然后……、呃那个…… 等等\n" 
                "    - 如英文：um/uh/ you know / I mean /well /so /actually / kind of / sort of\n" 
                "\n" 
                "\n" 
                "# 输出结果约束\n" 
                "- 自动识别语境（语言+文体），并应用上述规则；\n" 
                "- 保持全文数字风格一致；\n" 
                "- 优先确保语法正确与专业性。\n" 
                "- 严禁增加任何其他文字说明，只输出最终转写优化后的内容结果。\n" 
                "- 严禁在转写内容中插入任何推测和补充说明性文字，直接给出最终的判断。\n" 
                "\n")
# 严格适配 /api/generate 的官方最小化参数结构
# payload = {
#     "model": "qwen2.5:1.5b",
#     "prompt": "今天是各号天气  我么一起出去学习吧.一是测试  2是学习",
#     "system": systemPrompt,
#     "stream": False,
#     # 所有的推理参数（温度、Top_P、惩罚项等）必须全部放在 options 内部
#     "options": {
#         "temperature": 0.1,   # 降低温度（例如 0.1~0.3）可以增强模型对 System Prompt 的顺从度
#         "top_p": 0.9,         # 核心采样比例
#         "num_predict": 128    # 限制最大生成Token数，防止小模型说车轱辘话
#     }
# }
#
# try:
#     response = requests.post(url, json=payload)
#     # 如果还是 400，这里会打印出 Ollama 返回的具体错误原因
#     if response.status_code != 200:
#         print(f"错误详情: {response.text}")
#
#     response.raise_for_status()
#     print("【模型回复】:")
#     print(response.json().get('response'))
#
# except Exception as e:
#     print(f"❌ 调用失败: {e}")

#--------------------------
# 配置参数
url = "http://localhost:11434/api/generate"
# system_prompt = "你是一个严谨的助手，请简要回答用户的问题。"
user_prompt = "今天是号天气 我么一起出去学习吧.一是测试 2是学习，还有什么可以做倪"

# 待测试模型列表
models = [
    "qwen2.5:1.5b",
    "my-qwen2.5-1.5b",
    "qwen2.5:3b"

]

results = []

print(f"🚀 开始多模型性能测试...\n" + "-" * 50)

for model_name in models:
    payload = {
        "model": model_name,
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 128
        }
    }

    print(f"正在测试模型: {model_name}...", end="", flush=True)

    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        end_time = time.time()

        duration = round(end_time - start_time, 2)

        if response.status_code == 200:
            reply = response.json().get('response', '').strip()
            results.append({
                "model": model_name,
                "time": duration,
                "status": "✅ 成功",
                "reply": reply
            })
            print(f" 完成! (耗时: {duration}s)")
        else:
            results.append({
                "model": model_name,
                "time": duration,
                "status": f"❌ 错误: {response.status_code}",
                "reply": response.text
            })
            print(f" 失败!")

    except Exception as e:
        results.append({
            "model": model_name,
            "time": "N/A",
            "status": "❌ 异常",
            "reply": str(e)
        })
        print(f" 出错!")

# --- 测试结果对比展示 ---
print("\n" + "=" * 20 + " 最终对比测试报告 " + "=" * 20)
print(f"{'模型名称':<15} | {'响应时长':<8} | {'状态':<8} | {'模型回复内容'}")
print("-" * 80)

for res in results:
    display_reply = res['reply'].replace('\n', ' ')[:50] + "..."
    print(f"{res['model']:<15} | {res['time']:<8} | {res['status']:<8} | {display_reply}")