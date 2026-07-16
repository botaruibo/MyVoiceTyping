# Roadmap

MyVoiceTyping 的长期目标是：做一个本地优先、0 费用、适合中文表达、可持续自进化的 macOS 语音输入工具。

这份路线图用于说明当前优先级，也方便试用用户判断是否值得 Star 关注后续版本。路线图会根据真实反馈调整。

## 当前定位

MyVoiceTyping 当前聚焦一个明确场景：

> 在 macOS 上按住快捷键说中文，松开后得到可直接使用的输入文本，并尽量让音频和文本留在本机。

可以把它理解为 Typeless 的开源平替方向：同样关注“说话直接落字”的输入体验，但更强调本地数据安全、0 费用、可审查、可复现，以及后续通过 self-evaluation / 自进化逐步贴合个人表达习惯。

当前不是会议转写 SaaS，也不是完整 AI 助手。优先把“语音 → 中文文本 → 轻量纠错/润写 → 粘贴”这条输入链路做稳。

## 近期优先级：0 → 50 stars

这一阶段重点不是堆功能，而是让真实用户能顺利安装、试用和反馈。

- [ ] 收集 10 条以上 macOS 真实试用反馈；
- [ ] 完善首次启动、权限引导和模型下载失败提示；
- [ ] 优化转写后的标点、断句和轻量纠错效果；
- [ ] 减少文本润写过度改写原意的情况；
- [ ] 改进粘贴到当前输入框的稳定性；
- [ ] 增加更多可复现的测试样例；
- [ ] 持续完善 FAQ、Privacy、Security、Roadmap 和 Issue 模板；
- [ ] 明确 App 仓库项目级 License，并同步 README / landing / Release notes；
- [ ] 明确 self-evaluation 数据边界：本地保存、用户可控、默认不上传云端。

## 中期方向：50 → 200 stars

当有更多真实反馈后，重点转向稳定性、可配置性、开发者场景和个人化输入体验。

- [ ] 增加更清晰的模型下载/校验/重试机制；
- [ ] 支持更细粒度的润写开关和风格配置；
- [ ] 优化 AI Coding 场景：需求描述、Bug 复现、PR 说明；
- [ ] 改进热词词典，让项目名、技术术语、人名更稳定；
- [ ] 增加隐私敏感模式说明和本地路径管理；
- [ ] 制作 30–60 秒演示视频或 GIF；
- [ ] 根据反馈评估是否支持更多快捷键和输入模式；
- [ ] 设计“用户确认文本”的本地样例格式，用于后续个人化训练或轻量调优。

## Self-evaluation / 自进化方向

MyVoiceTyping 的一个核心长期差异点，是让本地 LLM 越用越贴合使用者。

初步路线：

1. 用户语音输入生成初稿；
2. 用户修改、确认最终文本；
3. 本地记录“原始转写 / 模型润写 / 用户确认文本”的对照样例；
4. 用户可预览、删除、导出这些样例；
5. 定期用这些样例调优本地 LLM 或生成个人偏好配置；
6. 让模型逐步适应个人词汇、语气、常用表达和工作场景。

隐私原则：

- 默认本地保存；
- 默认不上传云端；
- 用户可删除、关闭或导出；
- 普通日志、调试信息和崩溃报告不应保存原始听写文本、润写后文本或用户最终确认文本；
- 不把用户真实敏感文本提交到公开数据集；
- 如果未来支持云端同步或共享样例，必须显式说明数据去向并提供开关。

相关安全边界见 [Security Policy](SECURITY.md)。如果需要反馈日志、调试信息、模型下载、缓存目录或 self-evaluation 样例相关问题，请先提交脱敏后的最小复现信息。

## 长期方向：200 → 1000 stars

如果项目获得足够真实用户和维护反馈，再考虑更大的能力扩展。

- [ ] 更完整的多场景输入模式：聊天、文档、代码、会议摘要；
- [ ] 更系统的中文 ASR 后处理数据集建设；
- [ ] 更稳定的模型替换机制，方便用户使用自己的 GGUF 模型；
- [ ] 更完善的安装包签名、发布和升级流程；
- [ ] 根据社区需求评估 Windows / Linux 或其他平台可能性；
- [ ] 建立更清晰的贡献指南和开发文档；
- [ ] 在严格本地优先和用户授权前提下，探索个人化模型持续调优流程。

到 1000 stars 时，希望 MyVoiceTyping 不只是一个“能跑的语音输入 demo”，而是形成一个可持续维护的中文本地语音输入栈：

- App：稳定的 macOS 日常输入工具；
- Model：可替换、可量化、可本地运行的文本润写模型；
- Dataset：可审查、可追踪来源、能持续改进中文 ASR 后处理的数据集；
- Feedback：真实用户通过 30 秒试用任务、Issue 和 Discussions 持续提供脱敏样例；
- Self-evaluation：用户确认后的修改可以在本机沉淀为偏好样本，用于评估或调优本地模型；
- Community：形成一批关注中文 / 中英混合输入、本地隐私和 AI Coding prompt 的早期用户与贡献者。

这也是为什么 Star 对项目很重要：它既是传播信号，也是判断是否值得继续投入打磨安装、权限、模型、数据和本地个性化闭环的早期需求信号。

## 暂不优先做的事情

为了保持项目聚焦，以下方向暂时不是优先级：

- 大而全的会议转写平台；
- 云端账号体系和多端同步；
- 默认依赖云端大模型处理音频或文本；
- 复杂的团队协作管理功能；
- 在没有足够用户反馈前支持过多平台；
- 未经用户明确确认就收集、上传或公开训练样例。

## 如何参与

如果你愿意帮忙，最有价值的方式是：

1. 下载最新 [Release](https://github.com/botaruibo/MyVoiceTyping/releases) 真实试用；
2. 用 [体验反馈 / User feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交使用场景和输出样例；
3. 用 [Bug report / 故障报告](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交可复现问题；
4. 在 [Discussions](https://github.com/botaruibo/MyVoiceTyping/discussions/2) 里反馈你希望优先改进的场景；
5. 如果你愿意帮助 self-evaluation / 自进化方向，请优先提交可公开、脱敏后的“原始转写 → 期望文本”样例；
6. 如果项目解决了你的问题，欢迎 Star 关注后续版本。

## 相关资产

- 应用：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- ASR 后纠错数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)
- FAQ：[docs/FAQ.md](docs/FAQ.md)
- Privacy / Data Safety：[docs/PRIVACY.md](docs/PRIVACY.md)
- Security Policy：[SECURITY.md](SECURITY.md)
- License / Dataset usage boundary tracking：[Issue #7](https://github.com/botaruibo/MyVoiceTyping/issues/7)
- Dataset DATA_LICENSE：[botaruibo/MyVoiceTyping-Dataset/DATA_LICENSE.md](https://github.com/botaruibo/MyVoiceTyping-Dataset/blob/main/DATA_LICENSE.md)
- Dataset SOURCES：[botaruibo/MyVoiceTyping-Dataset/docs/SOURCES.md](https://github.com/botaruibo/MyVoiceTyping-Dataset/blob/main/docs/SOURCES.md)
