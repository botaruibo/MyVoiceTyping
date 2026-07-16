# FAQ / Troubleshooting

这份文档用于帮助新用户快速排查 MyVoiceTyping 的常见问题。它也方便从社区文章、知乎/掘金评论、GitHub Discussions 进入项目的新用户判断：这个工具是否适合自己的使用场景。

## MyVoiceTyping 适合什么场景？

MyVoiceTyping 更适合 macOS 上的中文语音输入，例如：

- 写需求、PR 说明、技术文档；
- 回消息、写邮件、整理想法；
- 用语音给 AI Coding 工具描述需求、Bug 复现和改动计划；
- 需要本地优先、尽量不上传音频和文本的隐私敏感场景。

它不是会议转写 SaaS，也不是完整的云端 AI 助手。当前目标是把“说一段中文 → 得到可用输入文本”这条链路做稳。

## 和 Typeless / 闪电说 / Typeoff 有什么区别？

这些商业产品通常更成熟，云端能力、跨平台能力和高级 AI 编辑能力更完整。

MyVoiceTyping 当前更强调：

- 开源；
- 本地优先；
- 面向 macOS 中文输入；
- 音频和文本默认尽量留在本机；
- 应用、文本润写模型和后处理数据集都公开，便于复现和二次开发。

如果你只追求最成熟的商业体验，Typeless / 闪电说 / Typeoff 可能更合适。如果你更在意开源、本地隐私、可控和可二开，可以试试 MyVoiceTyping。

## 首次启动为什么要授予多个权限？

macOS 对语音输入类工具限制比较严格。MyVoiceTyping 通常需要：

- 麦克风：录音；
- 辅助功能：把结果粘贴到当前输入位置；
- 输入监控：监听快捷键；
- 通知或状态栏权限：显示状态、入口和提示。

如果权限没有授予完整，常见表现是：能启动但不能录音、录音后不能粘贴、快捷键没有反应。

## 模型为什么要首次下载？

为了保持安装包体积可控，语音识别、标点恢复和文本润写模型不会直接打包进应用，也不会提交到 Git 仓库。首次启动时应用会按需检查并下载模型。

如果下载失败，可以检查：

- 当前网络是否能访问模型源；
- 是否需要代理；
- 磁盘空间是否足够；
- 是否有公司网络或安全软件拦截。

如果仍然失败，请通过 [Bug report / 故障报告](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交错误信息。

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
- [Discussions 体验招募帖](https://github.com/botaruibo/MyVoiceTyping/discussions/2)：不确定是否算 bug 时，可以先在讨论区反馈。

请不要上传包含隐私、公司机密或敏感信息的音频/文本。

## 三个开源资产是什么关系？

- 应用：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- ASR 后纠错数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

简单理解：应用负责录音、调用模型和粘贴；模型负责 ASR 后的轻量纠错/润写；数据集用于持续改进中文语音输入后的文本整理效果。
