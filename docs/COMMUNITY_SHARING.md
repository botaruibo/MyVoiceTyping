# Community sharing / 社区讨论回复素材

这页用于在真实相关的社区讨论里介绍 MyVoiceTyping。适用场景包括：

- 有人在比较 Typeless、闪电说、Typeoff、Wispr Flow 等语音输入工具；
- 有人在讨论 macOS 中文语音输入、本地听写、AI Coding prompt 输入；
- 有人在关心语音输入的隐私、费用、开源可审查或本地模型调优。

原则：透明、克制、相关。不要伪装成第三方用户，不要在无关帖子里只贴链接。

## 统一一句话

```text
MyVoiceTyping 是一个面向 macOS 中文 / 中英混合输入的开源、本地优先语音输入项目：按住快捷键说话，松开后转写、补标点、轻量纠错/润写，并粘贴到当前输入框。
```

## 评论区短回复：Typeless / 闪电说 / Typeoff 对比

```text
我自己也在折腾这个方向，感觉语音输入真正有价值的地方不只是“识别成文字”，而是能不能在任何输入框里把口语快速变成可用文本。

顺手补充一个开源方案：我在维护 MyVoiceTyping，定位更像 Typeless / 闪电说之外的本地优先选择。它主要面向 macOS 中文和中英混合输入，按住快捷键说话，松开后转写、补标点、轻量纠错/润写，再粘贴到当前输入框。

它现在还不是商业成熟产品，但适合在意 0 费用、开源可审查、本地数据安全、可自己改的人。

项目：https://github.com/botaruibo/MyVoiceTyping
3 分钟 Beta 反馈：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
```

## 问答平台长一点的回答

```text
如果你是在找 Typeless / 闪电说这类工具的“开源、本地优先”方向，可以看看 MyVoiceTyping。

它的目标不是替代所有商业产品。商业产品通常体验更完整、跨平台和云端能力更强。MyVoiceTyping 更偏开发者和隐私敏感用户：macOS 上按住快捷键说话，松开后自动转写、补标点、轻量纠错/润写，然后粘贴到当前输入位置。

我比较看重三点：

1. 本地优先：尽量让音频、原始转写和润写后的文本留在本机；
2. 开源可审查：应用、润写模型、数据集都公开；
3. 本地自进化方向：用户确认后的改写结果，可以作为本地偏好样本，后续用于评估、偏好词表或本地轻量调优，让模型更贴近自己的表达习惯。

自进化的数据边界我也单独写清楚了，不是默认上传用户隐私数据：
https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/SELF_EVALUATION.md

项目地址：
https://github.com/botaruibo/MyVoiceTyping
```

## 开发者 / AI Coding 语音输入讨论

```text
AI Coding 里我觉得语音输入挺适合作为 prompt 入口：Bug 复现、重构需求、PR 描述、测试用例这些内容，用说的往往比打字更快。

我在维护一个开源项目 MyVoiceTyping，思路是先把语音变成可编辑文本，再由用户确认后粘贴到 Claude Code / Codex / Cursor / Copilot 这类工具里，而不是识别完直接 auto-send。

这样对技术词、项目名、接口名识别错的时候，还有机会改，比较适合写长 prompt。

方向是 macOS 中文 / 中英混合输入、本地优先、0 费用、开源可审查：
https://github.com/botaruibo/MyVoiceTyping

如果你愿意帮忙试一条虚构 prompt，最希望收到的是技术词、文件名、变量名或错误信息有没有被误改：
https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
```

## 隐私 / 数据安全讨论

```text
语音输入我最担心的是“每句话到底去了哪里”。工作需求、代码 prompt、客户上下文、私人消息都可能被口述进去，所以我更偏向本地优先方案。

MyVoiceTyping 的方向是：macOS 中文语音输入，尽量让音频、原始转写和润写后的文本留在本机；应用代码、润写模型和数据集都公开，方便审查和二次开发。

它不宣传“绝对 100% 隐私”，因为模型下载、用户手动打开外部链接等场景仍可能联网；但默认处理链路会尽量减少敏感内容外传。

隐私边界：
https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/PRIVACY.md

项目：
https://github.com/botaruibo/MyVoiceTyping
```

## Self-evaluation / 本地自进化讨论

```text
MyVoiceTyping 后续想做的一个方向是本地 self-evaluation：用户语音输入后，系统先给一个初始结果；用户最后怎么修改、确认，这个“初始输出 → 用户确认文本”可以成为本地偏好样本。

这些样本可以先用于评估、热词、规则和 prompt 偏好；在用户明确授权后，再探索本地小模型轻量调优。目标是让模型越来越懂你的项目名、常用词、语气和写作习惯。

这个方向最关键的是数据边界：默认不上传，不自动进公开数据集，不偷偷用于云端训练。

说明文档：
https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/SELF_EVALUATION.md
```

## 什么时候不要回复？

- 帖子和语音输入、隐私、本地模型、AI Coding prompt 完全无关；
- 只是竞品官方公告，没有用户讨论或提问；
- 同一个帖子已经回复过一次，且没有人追问；
- 需要伪装成普通用户才能自然出现；
- 只能贴链接，无法提供上下文价值；
- 对方明确不欢迎自荐或项目推广。

## 推荐链接组合

普通用户：

1. Website：https://botaruibo.github.io/MyVoiceTyping/
2. Quickstart：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/QUICKSTART.zh-CN.md
3. Beta testing / 3 分钟反馈：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
4. Releases：https://github.com/botaruibo/MyVoiceTyping/releases

开发者：

1. Repo：https://github.com/botaruibo/MyVoiceTyping
2. Model：https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4
3. Dataset：https://github.com/botaruibo/MyVoiceTyping-Dataset
4. Beta testing / AI Coding 反馈：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
5. Self-evaluation：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/SELF_EVALUATION.md

对比选型：

1. 中文对比页：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/ALTERNATIVES.zh-CN.md
2. Privacy：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/PRIVACY.md
3. Beta testing / 不 Star 阻碍反馈：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
4. FAQ：https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/FAQ.md
