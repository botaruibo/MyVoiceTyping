# Contributing to MyVoiceTyping

感谢你愿意关注或参与 MyVoiceTyping！这个项目还处在早期阶段，最需要的是来自真实 macOS 使用场景的反馈、可复现问题、中文语音输入样例和小而清晰的改进。

## 可以怎样参与？

你不需要会写代码也可以贡献。

### 1. 真实试用反馈

如果你是 macOS 用户，最有价值的贡献是：

1. 下载最新 [Release](https://github.com/botaruibo/MyVoiceTyping/releases)；
2. 按照 README 完成首次启动和权限授权；
3. 用一段真实但不含隐私的中文口述测试；
4. 通过 [体验反馈 / User feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交结果。

请尽量包含：

- macOS 版本；
- Mac 型号 / 芯片；
- 使用场景：文档、聊天、AI Coding、会议记录等；
- 原始口述大意；
- 实际输出结果；
- 你期望的输出结果。

### 1.1 AI Coding 30 秒测试

如果你主要把 MyVoiceTyping 用在 Codex、Claude Code、Cursor、Qwen Code、OpenCode 或浏览器里的 AI 助手输入框，请优先试这个 30 秒任务：

1. 口述一个真实但不含敏感信息的 bug 复现、重构要求或 PR note；
2. 看输出是否保留技术词、文件名、函数名和中英混合表达；
3. 判断它是否可以直接发给 coding agent，还是需要手动改很多；
4. 通过 [AI Coding feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交结构化反馈。

尤其欢迎反馈：

- 技术词是否被误改；
- 中文断句是否影响 prompt 质量；
- 润写是否改变原意；
- 是否适合长 prompt / 多步骤任务；
- review-before-submit 是否足够安心。

### 2. Bug report

如果遇到应用启动、权限、录音、模型下载、转写、润写或粘贴问题，请使用：

- [Bug report / 故障报告](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose)

一个好的 bug report 通常包含：

- 复现步骤；
- 预期结果；
- 实际结果；
- macOS 版本和设备芯片；
- MyVoiceTyping Release 版本；
- 错误提示或日志片段。

### 3. 中文语音输入样例

MyVoiceTyping 的一个重点是 ASR 后处理：错词、标点、断句、轻量润写。

欢迎提交可公开样例，例如：

```text
原始口述大意：我想写一段 PR 描述，说明这次改动主要是修复模型下载失败时没有提示的问题。
实际输出：……
期望输出：……
```

请不要提交包含以下内容的样例：

- 公司机密；
- 个人身份信息；
- 密码、Token、密钥；
- 医疗、财务、法律等敏感内容；
- 未经授权的他人音频或文本。

### 3.1 Self-evaluation / 自进化样例边界

项目长期方向是把用户确认后的“原始转写 → 最终确认文本”作为本地偏好数据，用于词表、cleanup 规则或本地小模型调优。

如果你愿意提交样例，请只提交可公开内容。不要把真实公司需求、客户信息、私人聊天、Token、密码、内部路径或受版权限制的文本放进 Issue、Discussion 或 PR。

更推荐的方式是构造一个等价的公开样例，例如把真实项目名替换成 `ProjectA`，把真实接口名替换成 `fetchUserProfile()` 这类虚构名称。

### 4. 文档改进

当前欢迎改进：

- README 首屏说明；
- [FAQ / Troubleshooting](docs/FAQ.md)；
- [Privacy / Data Safety](docs/PRIVACY.md)；
- [Roadmap](ROADMAP.md)；
- 安装、权限、模型下载和排障说明；
- 面向中文用户的使用示例。

### 5. 代码贡献

如果你想提交代码，请优先选择小而明确的改动。

适合的贡献方向：

- 权限引导和错误提示；
- 模型下载、校验、重试；
- 粘贴稳定性；
- 热词词典和技术术语识别；
- ASR 后处理和轻量润写；
- 日志、测试和可复现样例；
- 打包、Release 和安装体验。

在提交较大改动前，建议先开 issue 或 discussion 说明动机，避免方向不一致。

### 6. 安全 / 隐私问题

如果你发现以下问题，请不要直接在公开 issue 里贴敏感细节：

- 原始音频、原始转写文本或用户确认文本被写入普通日志；
- Token、密码、公司路径、私有项目名出现在截图、日志或崩溃报告中；
- 模型下载、缓存目录或权限处理存在安全风险；
- 语音输入结果被自动提交到第三方服务，用户没有机会 review。

请先阅读 [Security Policy](SECURITY.md) 和 [Privacy / Data Safety](docs/PRIVACY.md)，再决定如何提交最小可复现信息。

## Pull Request 建议

提交 PR 前，请尽量做到：

- 改动聚焦，一个 PR 解决一个问题；
- 描述清楚改动动机；
- 如果是 bug fix，请关联 issue 或给出复现步骤；
- 如果改动用户可见行为，请更新 README / FAQ / Roadmap；
- 不要提交模型文件、大型二进制文件或本地隐私数据；
- 不要提交 API key、Token、日志里的敏感路径或公司数据。
- 不要把原始听写文本、用户确认后的改写文本或 self-evaluation 样例写入普通测试快照，除非它们是明确构造的公开样例。

## 项目方向

请先阅读：

- [Roadmap](ROADMAP.md)
- [Privacy / Data Safety](docs/PRIVACY.md)
- [FAQ / Troubleshooting](docs/FAQ.md)

当前项目优先级是把 macOS 中文语音输入、本地优先、轻量纠错/润写和粘贴链路做稳。暂不优先做大而全的会议转写平台、云端账号体系或复杂团队协作功能。

## 沟通方式

- 不确定该去哪里反馈：先看 [Support / 反馈与支持](SUPPORT.md)
- 不确定是不是 bug：先发 [Discussions](https://github.com/botaruibo/MyVoiceTyping/discussions)
- 有明确复现步骤：发 Issue
- 有代码改动：发 Pull Request
- 只是想关注项目：欢迎 Star，后续版本会持续更新
