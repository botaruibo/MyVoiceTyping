# 同类工具对比 / 选型建议

这页用来说明 MyVoiceTyping 和 Typeless、闪电说、Typeoff、Wispr Flow、VoiceSnap、Handy、MacParakeet、OpenQuack、VocaMac、Turbo Whisper、OmniDictate 等语音输入 / AI 听写工具的定位差异。

它不是为了证明“谁一定更好”。这类工具本来就有不同取舍：商业成熟度、云端能力、本地隐私、中文体验、跨平台、订阅费用、是否开源、是否能自己改。

English version: [Alternatives / Comparison](./ALTERNATIVES.md)

## 一句话定位

MyVoiceTyping 是一个面向 macOS 的开源、本地优先中文语音输入项目。

你可以把它理解成 Typeless / Wispr Flow / 闪电说这类产品的开源本地优先方向，尤其适合更在意这些点的人：

- 中文和中英混合语音输入；
- 本地数据安全；
- 0 费用；
- 代码开源、可审查、可二开；
- 应用、润写模型、数据集都公开；
- ASR 之后还能做标点恢复、轻量纠错和文本润写；
- 后续通过 self-evaluation / 自进化，让本地模型逐渐贴合自己的表达习惯。

相关资产：

- App：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 本地文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- 数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

## 和 Typeless 相比

Typeless 是更成熟的商业 AI 语音输入产品。如果你想要立刻可用、打磨完整、跨平台或云端 AI 编辑体验，它通常会更合适。

MyVoiceTyping 的差异是：

- 开源；
- 更聚焦 macOS 中文 / 中英混合输入；
- 更强调本地优先的数据安全；
- 开源版本不需要订阅费用；
- 应用、润写模型和数据集都公开；
- 正在探索 self-evaluation：用户确认后的修改可以作为本地偏好数据，用来评估或调优本地模型。

如果你今天就要最成熟的商业体验，Typeless 可能更适合。  
如果你想要一个能审查、能改、能本地跑、能长期调成自己输入习惯的中文语音输入栈，MyVoiceTyping 更值得试试。

## 和闪电说 / Typeoff 相比

闪电说、Typeoff 这类工具通常更偏完整产品体验，可能包含更成熟的快捷键、跨平台、云端模型、账号体系、商业运营和客服支持。

MyVoiceTyping 当前更早期，重点不是“功能一定更多”，而是：

- 尽量让语音、转写文本、润写文本留在本机流程中；
- 让用户能看到代码、模型和数据集；
- 对中文和中英混合输入做更直接的优化；
- 适合开发者、写作者和隐私敏感用户自己折腾、改造、反馈。

如果你已经用闪电说 / Typeoff 很顺，不一定需要切换。  
如果你在意开源、本地优先、0 费用，或者想自己控制输入链路，可以把 MyVoiceTyping 作为补充选择。

## 和 Wispr Flow 相比

Wispr Flow 更偏英文和跨平台的商业 AI dictation 产品，优势是产品完成度和通用体验。

MyVoiceTyping 不打算复制所有 Wispr Flow 功能。当前重点更窄：

- macOS 桌面工作流；
- 中文优先；
- 本地 ASR + 标点恢复 + 轻量纠错 / 润写；
- 适合公司内容、代码 prompt、会议纪要、PR 描述等隐私敏感输入；
- 开源资产可审查、可复用。

英文长文和跨平台商业体验，Wispr Flow 可能更适合。  
中文开发者和 macOS 用户想要开源本地优先路线，可以看 MyVoiceTyping。

## 和 VoiceSnap / Handy / MacParakeet / OpenQuack / VocaMac / Turbo Whisper / OmniDictate 等本地听写工具相比

现在本地或低成本 dictation 工具越来越多，其中很多在英文听写、WhisperKit、本地模型、快捷键体验上做得很好。

例如 VoiceSnap 这类项目更强调纯离线、Typeless 替代和特定平台的本地语音输入体验。它们对“只想离线把声音变成文字”的用户很有价值。

MyVoiceTyping 的重点不只是“本地语音转文字”，而是完整中文输入闭环：

1. 按住快捷键说话；
2. 语音识别；
3. 恢复标点和句子边界；
4. 修正常见 ASR 错误；
5. 轻量润写文本；
6. 粘贴到当前输入框；
7. 未来把用户确认后的修改作为本地偏好数据，让模型逐步贴合个人表达。

原始转写通常不够用。日常输入真正需要的是能直接发到聊天、邮件、文档、Issue、PR、AI Coding prompt 里的可用文本。

如果你已经有一个英文听写、本地 Whisper、纯离线 Typeless 替代、菜单栏录音或快捷键转写工具，并且主要需求是“把语音变成原始文字”，这些工具可能已经足够。MyVoiceTyping 更适合下面这种需求：macOS 中文 / 中英混合输入较多，希望 ASR 之后自动补标点、修正常见错字、轻量润写，并且未来能把用户确认后的改写沉淀为本地偏好数据，让本地模型逐步贴合个人表达。

## 为什么本地优先重要？

语音输入经常包含敏感内容：

- 工作记录；
- 产品需求；
- bug 描述；
- 代码想法；
- 私人消息；
- 会议纪要；
- 个人表达习惯。

MyVoiceTyping 的原则是：在可行范围内，音频、转写文本、润写文本、用户确认后的修改，都应默认留在用户自己的机器上。

如果未来支持云同步、云端训练或共享样本，也应该是明确、可关闭、可理解的 opt-in 行为。

更多说明见：[Privacy / Data Safety](./PRIVACY.md)。

## self-evaluation / 自进化是什么意思？

通用模型不一定懂你的项目名、团队黑话、代码术语、写作风格和口头表达习惯。

MyVoiceTyping 的 self-evaluation 方向是：

- 应用先生成初始转写 / 润写结果；
- 用户修改并确认最终文本；
- “初始输出 → 用户确认文本” 可以成为本地偏好数据；
- 后续可用来评估或调优本地 LLM；
- 目标是越用越贴合你的表达方式。

这类数据可能很敏感，所以不应默认上传，也不应偷偷进入云端训练。

## 什么时候适合试 MyVoiceTyping？

你可以试试 MyVoiceTyping，如果你：

- 主要使用 macOS；
- 经常输入中文或中英混合文本；
- 想要 Typeless 类似的“说话直接落字”体验，但不想订阅；
- 在意本地数据安全；
- 想要一个可以审查和修改的开源项目；
- 经常用语音给 Codex、Claude Code、Cursor、Copilot 写长 prompt；
- 希望未来能通过本地偏好数据，让模型越来越懂自己的表达习惯。

## 什么时候应该选别的工具？

如果你需要下面这些，其他工具可能更合适：

- 立即可用的成熟商业体验；
- Windows / Linux / iOS / Android 支持；
- 英文长文听写为主；
- 云端 AI 编辑和账号同步；
- 不想处理本地模型、权限、安装和调试；
- 企业支持、团队管理、商业 SLA。

## 总结

MyVoiceTyping 不是“又一个转写工具”。

它想做的是一个本地优先、0 费用、开源、面向中文和中英混合输入的 macOS 语音输入层，并且长期走向本地自进化的个性化输入体验。

如果这个方向对你有用，欢迎试用、提 Issue，或者 Star 项目关注后续进展：

https://github.com/botaruibo/MyVoiceTyping
