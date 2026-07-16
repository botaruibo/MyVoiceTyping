# Roadmap

MyVoiceTyping 的长期目标是：做一个本地优先、适合中文表达、可持续迭代的 macOS 语音输入工具。

这份路线图用于说明当前优先级，也方便试用用户判断是否值得 Star 关注后续版本。路线图会根据真实反馈调整。

## 当前定位

MyVoiceTyping 当前聚焦一个明确场景：

> 在 macOS 上按住快捷键说中文，松开后得到可直接使用的输入文本，并尽量让音频和文本留在本机。

当前不是会议转写 SaaS，也不是完整 AI 助手。优先把“语音 → 中文文本 → 轻量纠错/润写 → 粘贴”这条输入链路做稳。

## 近期优先级：0 → 50 stars

这一阶段重点不是堆功能，而是让真实用户能顺利安装、试用和反馈。

- [ ] 收集 10 条以上 macOS 真实试用反馈；
- [ ] 完善首次启动、权限引导和模型下载失败提示；
- [ ] 优化转写后的标点、断句和轻量纠错效果；
- [ ] 减少文本润写过度改写原意的情况；
- [ ] 改进粘贴到当前输入框的稳定性；
- [ ] 增加更多可复现的测试样例；
- [ ] 持续完善 FAQ、Privacy 和 Issue 模板。

## 中期方向：50 → 200 stars

当有更多真实反馈后，重点转向稳定性、可配置性和开发者场景。

- [ ] 增加更清晰的模型下载/校验/重试机制；
- [ ] 支持更细粒度的润写开关和风格配置；
- [ ] 优化 AI Coding 场景：需求描述、Bug 复现、PR 说明；
- [ ] 改进热词词典，让项目名、技术术语、人名更稳定；
- [ ] 增加隐私敏感模式说明和本地路径管理；
- [ ] 制作 30–60 秒演示视频或 GIF；
- [ ] 根据反馈评估是否支持更多快捷键和输入模式。

## 长期方向：200+ stars

如果项目获得足够真实用户和维护反馈，再考虑更大的能力扩展。

- [ ] 更完整的多场景输入模式：聊天、文档、代码、会议摘要；
- [ ] 更系统的中文 ASR 后处理数据集建设；
- [ ] 更稳定的模型替换机制，方便用户使用自己的 GGUF 模型；
- [ ] 更完善的安装包签名、发布和升级流程；
- [ ] 根据社区需求评估 Windows / Linux 或其他平台可能性；
- [ ] 建立更清晰的贡献指南和开发文档。

## 暂不优先做的事情

为了保持项目聚焦，以下方向暂时不是优先级：

- 大而全的会议转写平台；
- 云端账号体系和多端同步；
- 默认依赖云端大模型处理音频或文本；
- 复杂的团队协作管理功能；
- 在没有足够用户反馈前支持过多平台。

## 如何参与

如果你愿意帮忙，最有价值的方式是：

1. 下载最新 [Release](https://github.com/botaruibo/MyVoiceTyping/releases) 真实试用；
2. 用 [体验反馈 / User feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交使用场景和输出样例；
3. 用 [Bug report / 故障报告](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交可复现问题；
4. 在 [Discussions](https://github.com/botaruibo/MyVoiceTyping/discussions/2) 里反馈你希望优先改进的场景；
5. 如果项目解决了你的问题，欢迎 Star 关注后续版本。

## 相关资产

- 应用：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- ASR 后纠错数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)
- FAQ：[docs/FAQ.md](docs/FAQ.md)
- Privacy / Data Safety：[docs/PRIVACY.md](docs/PRIVACY.md)
