# 30 秒看懂 MyVoiceTyping

这页用于在还没有精剪视频 / GIF 之前，让新用户用 30 秒判断 MyVoiceTyping 是否值得下载、试用或 Star。

> 说明：这不是伪装成真实录屏的视频结果，而是基于当前公开截图、文档和目标工作流整理的快速 walkthrough。真实输出会受麦克风、环境噪音、语速、模型版本和本地配置影响。

## 一句话

MyVoiceTyping 是一个面向 macOS 的本地优先中文语音输入工具：按住快捷键说话，松开后自动转写、恢复标点、轻量纠错 / 润写，并粘贴到当前输入框。

它更适合：

- 中文 / 中英混合输入；
- AI Coding prompt；
- Issue / PR / Bug 复现说明；
- 工作消息、邮件、笔记；
- 不希望音频和文本默认上云的隐私敏感输入。

## 30 秒流程

```text
按住快捷键
  ↓
口述一段中文 / 中英混合内容
  ↓
松开快捷键
  ↓
本地 ASR + 标点恢复 + 轻量纠错 / 润写
  ↓
检查结果
  ↓
粘贴到当前输入框
```

## 典型输入输出

### 口述内容

```text
帮我检查一下登录页面 用户点击发送验证码以后按钮应该进入倒计时 如果接口报错需要恢复按钮并显示错误信息
```

### 目标输出

```text
帮我检查一下登录页面：用户点击“发送验证码”以后，按钮应该进入倒计时；如果接口报错，需要恢复按钮并显示错误信息。
```

它想解决的不是“把每个字都机械识别出来”，而是把口述内容整理成可以直接发给 Cursor、Claude Code、Qwen Code、Copilot、GitHub Issue 或团队 IM 的文字。

## 为什么不是直接用 Typeless / 闪电说？

如果你要的是成熟商业产品、跨平台、开箱即用，Typeless / 闪电说这类工具会更省心。

MyVoiceTyping 的差异是：

- 开源；
- 0 费用；
- 本地优先；
- 面向 macOS 中文 / 中英混合输入；
- App、文本润写模型、调优数据集都公开；
- 更适合愿意试早期项目并反馈问题的人。

## Self-Evolution / 本地自进化

alpha-0.03 开始，MyVoiceTyping 正在推进本地自进化方向：

```text
用户确认后的文本
  ↓
本机 voice_history.jsonl
  ↓
用户确认参与训练
  ↓
本机 MLX LoRA 调优
  ↓
转换为 GGUF Q4
  ↓
替换本地文本改写模型
```

目标是让本地模型逐渐更懂你的：

- 常用词；
- 技术词；
- 项目名；
- 中英混合习惯；
- AI Coding prompt 写法；
- 个人表达风格。

数据边界：

- 默认不上传云端；
- 不自动进入公开数据集；
- 本地训练前需要用户确认；
- 不要把公司机密、客户信息、Token、密码、私人消息或内部代码作为公开反馈提交。

更完整说明：

- [Self-evaluation / 本地自进化说明](./SELF_EVALUATION.md)
- [Privacy / Data Safety](./PRIVACY.md)

## 现在怎么试？

1. 先看项目介绍页：
   - <https://botaruibo.github.io/MyVoiceTyping/landing/>
2. 下载最新 Release：
   - <https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02>
3. 用虚构内容跑 30 秒试用任务：
   - [Trial tasks / 30 秒试用任务](./TRIAL_TASKS.zh-CN.md)
4. 如果方向对你有用，欢迎 Star：
   - <https://github.com/botaruibo/MyVoiceTyping>

## 反馈什么最有帮助？

如果你愿意试用，最有帮助的反馈不是“好用 / 不好用”，而是：

- macOS 版本；
- Mac 芯片；
- 是否能顺利授权麦克风 / 辅助功能 / 输入监控；
- 是否能顺利下载模型；
- 哪些中文或中英混合词错得多；
- 标点、断句、润写是否改变原意；
- 是否适合你的 AI Coding prompt / 工作消息场景；
- 你是否愿意因为这个方向点 Star；如果不愿意，卡点是什么。

反馈入口：

- [没下载 / 安装卡点反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=download_install_blocker.md)
- [3 分钟 Beta 反馈模板](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=beta_3min_feedback.md)
- [体验反馈 / User feedback](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose)
- [Discussions 体验招募帖](https://github.com/botaruibo/MyVoiceTyping/discussions/2)
