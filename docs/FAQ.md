# FAQ / Troubleshooting

这份文档用于帮助新用户快速排查 MyVoiceTyping 的常见问题。它也方便从社区文章、知乎/掘金评论、GitHub Discussions 进入项目的新用户判断：这个工具是否适合自己的使用场景。

## 如果你是从 Typeless / 闪电说 / Typeoff 讨论过来的

可以先用下面 5 个问题快速判断 MyVoiceTyping 是否值得继续看：

1. 你主要在 macOS 上输入中文或中英混合内容吗？
2. 你想要 Typeless / 闪电说 / Typeoff 之外的开源、本地优先、0 费用选择吗？
3. 你会把语音输入用于 AI Coding prompt、工作消息、PR / Issue、需求描述或笔记吗？
4. 你是否在意公司内容、代码 prompt、会议纪要或私人消息尽量不要默认进入第三方云端链路？
5. 你是否愿意接受一个早期项目，并通过 Issue / Star 帮它把 Demo、License、稳定性和中文后处理继续补齐？

如果上面有 2–3 个问题命中，建议按这个顺序看：

- 先看 [30 秒试用任务](./TRIAL_TASKS.zh-CN.md)，用虚构文本测试 AI Coding、工作消息、中英混合和隐私输入；
- 再看 [同类工具对比 / 选型建议](./ALTERNATIVES.zh-CN.md)，了解它和 Typeless、OpenTypeless、OpenLess、SayIt、闪电说、Typeoff、Wispr Flow 等工具的边界；
- 如果你准备安装，按 [快速上手 / macOS 试用指南](./QUICKSTART.zh-CN.md) 走；
- 如果方向对你有用，欢迎给 [主仓库](https://github.com/botaruibo/MyVoiceTyping) 一个 Star，或在 [体验反馈入口](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 里告诉我你最关心的缺口。

如果你只是想要最成熟、最少折腾的商业产品体验，也可以继续使用 Typeless、闪电说、Typeoff 或其他商业语音输入工具。MyVoiceTyping 当前更适合愿意关注开源、本地优先、可审查和中文 / 中英混合输入的人。

## MyVoiceTyping 适合什么场景？

MyVoiceTyping 更适合 macOS 上的中文语音输入，例如：

- 写需求、PR 说明、技术文档；
- 回消息、写邮件、整理想法；
- 用语音给 AI Coding 工具描述需求、Bug 复现和改动计划；
- 需要本地优先、尽量不上传音频和文本的隐私敏感场景。

它不是会议转写 SaaS，也不是完整的云端 AI 助手。当前目标是把“说一段中文 → 得到可用输入文本”这条链路做稳。

## 它可以理解成 Typeless 的开源平替吗？

可以把 MyVoiceTyping 理解成 Typeless 的开源平替方向，但它们当前成熟度和产品边界不同。

Typeless 这类商业产品通常体验更完整，可能包含云端识别、跨平台同步、高级 AI 编辑、商业客服和持续运营能力。MyVoiceTyping 当前更早期，更强调：

- 开源；
- 0 费用；
- 本地优先；
- 面向 macOS 中文输入；
- 音频和文本默认尽量留在本机；
- 应用、文本润写模型和后处理数据集都公开，便于审查、复现和二次开发。

如果你只追求最成熟的商业体验，Typeless / 闪电说 / Typeoff 可能更合适。如果你更在意开源、本地隐私、可控、可二开，以及长期把工具调成自己的输入习惯，可以试试 MyVoiceTyping。

## 和 Typeless / 闪电说 / Typeoff 有什么区别？

这些商业产品通常更成熟，云端能力、跨平台能力和高级 AI 编辑能力更完整。

MyVoiceTyping 当前更强调：

- 开源；
- 本地优先；
- 面向 macOS 中文输入；
- 音频和文本默认尽量留在本机；
- 应用、文本润写模型和后处理数据集都公开，便于复现和二次开发。

一句话概括：商业工具更像“开箱即用的云端 AI 输入服务”，MyVoiceTyping 更像“本地优先、可审查、可自定义的开源语音输入层”。

## 0 费用是什么意思？会不会有隐藏订阅？

MyVoiceTyping 是开源项目，当前目标是让用户可以免费试用和自部署，不设置订阅门槛。

需要注意的是：

- 首次使用可能需要下载模型文件；
- 本地推理会占用一定磁盘、CPU / 内存资源；
- 如果你自己改造为云端推理或接入第三方 API，相关云服务费用由对应服务产生；
- 未来如果项目出现商业化能力，应当和开源、本地优先版本清晰区分，不应影响当前开源版本的基本使用。

也就是说，“0 费用”指当前开源项目本身不向用户收取订阅费；它不等于完全没有本地资源成本。

## 本地数据安全具体指什么？

MyVoiceTyping 的路线是本地优先：语音输入、标点恢复、轻量纠错/润写尽量在本机完成，默认尽量不把音频和文本上传到云端。

这对于下面场景会更安心：

- 公司需求、会议结论、PR 描述；
- AI Coding 时口述 Bug、代码思路、改动计划；
- 私人消息、邮件、笔记；
- 不希望语音输入内容进入第三方云服务的场景。

更完整的数据边界请看 [Privacy / Data Safety](./PRIVACY.md)。

## Self-evaluation / 自进化是什么？

Self-evaluation / 自进化是 MyVoiceTyping 从 alpha-0.03 开始重点推进的本地个性化能力：语音输入生成初稿后，用户最终如何改写、如何确认，可以沉淀为本机 `voice_history.jsonl` 里的本地偏好数据。后续这些样本可以先用于本地评估、热词和规则优化；在用户确认后，也可以参与本机 MLX LoRA 轻量调优，并转换为 GGUF Q4 模型替换本地文本改写模型。

它想解决的问题是：通用模型不一定懂你的常用词、写作语气、项目名、团队黑话和输入习惯。通过用户确认后的改写数据，本地模型可以逐步更贴合个人表达。

一个简单例子：

- 原始转写：这个接口这里感觉有点问题帮我改一下
- 用户确认文本：这个接口的错误处理逻辑可能有问题，帮我检查并补充异常分支。

后者就比前者更像用户真正想要的表达。这样的样例长期积累后，可以用于改进本地润写模型，让它逐步贴近你的术语、语气和输入习惯。

## 自进化数据会上传吗？

默认原则是：不自动上传。

用户确认后的改写文本往往比普通日志更敏感，因为它可能包含：

- 真实工作内容；
- 个人表达习惯；
- 公司项目名或业务术语；
- 私人消息和上下文。

因此，自进化相关数据应保留在用户本机，并由用户控制是否保存、删除、导出或参与本地训练。它不会自动进入公开数据集。未来如果新增云端同步、云端训练或共享样例能力，也应该明确标注数据去向，并提供显式开关。

## 自进化能力现在已经完成了吗？

当前它已经进入 alpha-0.03 的重点建设范围，但不应理解为所有自动训练能力都已经完整成熟。

现阶段更重要的是先把这些基础做好：

- 明确本地数据边界；
- 完善 `voice_history.jsonl` 本地样例格式；
- 收集真实中文语音输入场景；
- 避免润写模型改变用户原意；
- 让用户能控制哪些数据参与本机 MLX LoRA 调优；
- 完善 GGUF Q4 转换、完整性检查和模型回滚。

项目会优先把隐私边界和可控性做好，再逐步完善自动化训练和评估流程。

## 首次启动为什么要授予多个权限？

macOS 对语音输入类工具限制比较严格。MyVoiceTyping 通常需要：

- 麦克风：录音；
- 辅助功能：把结果粘贴到当前输入位置；
- 输入监控：监听快捷键；
- 通知或状态栏权限：显示状态、入口和提示。

如果权限没有授予完整，常见表现是：能启动但不能录音、录音后不能粘贴、快捷键没有反应。

如果你还没下载，只是想判断这些权限是否值得授予，可以先看 [Quickstart 的权限 / 模型下载检查表](./QUICKSTART.zh-CN.md#下载前先看会要哪些权限--会下载什么)。如果你因为权限而放弃下载，也欢迎直接提交 [没下载 / 安装卡点反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=download_install_blocker.md) 或 [3 分钟 Beta 反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=beta_3min_feedback.md)，只写阻碍原因即可。

## 模型为什么要首次下载？

为了保持安装包体积可控，语音识别、标点恢复和文本润写模型不会直接打包进应用，也不会提交到 Git 仓库。首次启动时应用会按需检查并下载模型。

如果下载失败，可以检查：

- 当前网络是否能访问模型源；
- 是否需要代理；
- 磁盘空间是否足够；
- 是否有公司网络或安全软件拦截。

如果仍然失败，请通过 [Bug report / 故障报告](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交错误信息。

需要提前说明：模型下载本身需要联网；“本地优先”指默认语音识别、标点恢复和文本润写链路尽量在本机完成，不等于应用永远不会访问网络。更完整的数据边界见 [Privacy / Data Safety](./PRIVACY.md)。

## 转写结果不理想怎么办？

请尽量提交一段可公开的样例，包括：

- 原始口述大意；
- 实际输出结果；
- 你期望的结果；
- 问题类型：错别字、标点、断句、润写过度、润写不足等。

可以使用 [体验反馈 / User feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 模板提交。

## 润写会不会改变我的原意？

当前润写模型的目标是“轻量纠错和整理”，不是重写用户表达。它主要用于：

- 修正常见 ASR 错词；
- 补足基础标点和断句；
- 清理少量口语重复；
- 尽量保留原始表达。

如果你发现它过度概括、改变原意或删掉重要信息，请提交样例。这样的反馈对模型后续微调很有价值。

## 如果输入内容涉及公司或隐私，应该怎么用？

建议遵循一个简单原则：不要把不适合公开的原始音频或文本提交到 issue、评论区或公开数据集。

如果你需要反馈隐私相关问题，可以：

- 用脱敏后的文本描述问题；
- 只描述错误类型，不贴真实内容；
- 用自造样例复现同类问题；
- 检查本地保存目录，确认是否符合你的安全要求；
- 参考 [Privacy / Data Safety](./PRIVACY.md) 里的说明。

## 为什么结果没有粘贴到当前输入框？

常见原因：

- 辅助功能权限未开启；
- 当前应用不允许外部粘贴；
- 焦点不在可输入区域；
- 快捷键冲突；
- 某些安全软件或企业管控策略阻止粘贴。

可以先在系统自带“备忘录”里测试。如果备忘录可用，而某个特定应用不可用，请在 issue 里说明具体应用名称和版本。

## 如何反馈问题最有效？

优先使用 GitHub Issue 模板：

- [Bug report / 故障报告](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose)：应用启动、权限、模型下载、录音、粘贴等故障；
- [体验反馈 / User feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose)：转写质量、润写质量、使用场景和改进建议；
- [使用场景反馈 / Use case feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose)：如果你不确定它是否适合 AI Coding、工作消息、隐私输入、中文长文本或本地自进化场景，可以从这里反馈；
- [Discussions 体验招募帖](https://github.com/botaruibo/MyVoiceTyping/discussions/2)：不确定是否算 bug 时，可以先在讨论区反馈。

请不要上传包含隐私、公司机密或敏感信息的音频/文本。

## 三个开源资产是什么关系？

- 应用：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- ASR 后纠错数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

简单理解：应用负责录音、调用模型和粘贴；模型负责 ASR 后的轻量纠错/润写；数据集用于持续改进中文语音输入后的文本整理效果。
