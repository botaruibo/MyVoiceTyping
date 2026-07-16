# 快速上手 / macOS 试用指南

这份指南给第一次试用 MyVoiceTyping 的用户。目标是在 3–5 分钟内完成：下载 → 授权 → 试一句中文 → 判断是否值得继续使用或 Star。

> MyVoiceTyping 仍处于早期阶段。如果你遇到安装、权限、模型下载、转写、润写或粘贴问题，欢迎提交脱敏后的反馈。

## 1. 下载最新版

打开 Releases：

https://github.com/botaruibo/MyVoiceTyping/releases

下载最新版本的 macOS 安装包或压缩包。

如果 macOS 提示无法打开来自未知开发者的应用，请先确认你下载的是本仓库 Release 页面里的文件，再按系统提示到“系统设置 → 隐私与安全性”里允许打开。

## 2. 首次启动需要的权限

MyVoiceTyping 通常需要这些权限：

- 麦克风：录音；
- 辅助功能：把结果粘贴到当前输入位置；
- 输入监控：监听快捷键；
- 通知或状态栏权限：显示状态、入口和提示。

如果权限没授予完整，常见表现是：

- 快捷键没有反应；
- 能录音但没有文字；
- 有文字但不能粘贴；
- 某些输入框无法收到结果。

建议先在系统自带“备忘录”里测试，减少第三方应用干扰。

## 3. 首次模型下载

为了控制安装包体积，语音识别、标点恢复和文本润写相关模型不会直接提交到 Git 仓库，也不一定全部打包进安装包。首次启动或模型缺失时，应用可能需要联网下载模型。

如果下载失败，请检查：

- 当前网络是否能访问模型源；
- 是否需要代理；
- 磁盘空间是否足够；
- 公司网络或安全软件是否拦截模型下载。

数据边界说明见：[Privacy / Data Safety](./PRIVACY.md)。

## 4. 30 秒试用任务

打开“备忘录”或任意普通文本框，按住快捷键，说下面这句话：

```text
帮我检查一下登录页面，用户点击发送验证码以后按钮应该进入倒计时，如果接口报错需要恢复按钮并显示错误信息。
```

理想输出类似：

```text
帮我检查一下登录页面：用户点击“发送验证码”以后，按钮应该进入倒计时；如果接口报错，需要恢复按钮并显示错误信息。
```

重点观察：

- 是否能稳定录音；
- 是否能粘贴到当前输入框；
- 中文错字是否明显；
- 标点和断句是否自然；
- 润写有没有改变原意；
- 中英文或技术词是否被破坏。

更多示例见：[Demo / 使用效果示例](./DEMO.md) 和 [30 秒试用任务 / Trial tasks](./TRIAL_TASKS.zh-CN.md)。

## 5. AI Coding 试用任务

如果你经常用 Codex、Claude Code、Cursor、Qwen Code、Copilot 或其他 AI Coding 工具，可以试这个场景：

```text
帮我重构这个 React hook，保留 useMemo，但是把 loading state 和 error state 拆成两个独立的 reducer。
```

观察点：

- `React hook`、`useMemo`、`loading state`、`error state`、`reducer` 是否保留；
- 结果是否适合直接粘贴进 AI Coding prompt；
- 是否需要先 review/edit 再发送。

如果你愿意反馈 AI Coding 场景，请使用：

https://github.com/botaruibo/MyVoiceTyping/issues/5

## 6. 如何提交有效反馈

最有价值的反馈格式：

```text
使用设备：
macOS 版本：
芯片：M1 / M2 / M3 / M4 / Intel
使用场景：聊天 / 文档 / AI Coding / 邮件 / 其他

原始口述大意：
实际输出：
期望输出：

问题类型：
启动 / 权限 / 模型下载 / 录音 / 粘贴 / 错字 / 标点 / 润写过度 / 技术词 / 其他
```

提交入口：

- 普通反馈 / Bug report：<https://github.com/botaruibo/MyVoiceTyping/issues/new/choose>
- 0→50 stars 真实试用反馈追踪：<https://github.com/botaruibo/MyVoiceTyping/issues/3>
- AI Coding prompt 反馈：<https://github.com/botaruibo/MyVoiceTyping/issues/5>

请不要上传公司机密、客户信息、私聊、Token、密码、内部代码或未脱敏日志。

## 7. 如果它对你有用

如果 MyVoiceTyping 解决了你的中文输入问题，欢迎：

- Star 项目，方便后续跟进版本；
- 提交真实试用反馈；
- 分享给同样需要中文 / 中英混合语音输入的 macOS 用户；
- 参与文档、问题复现或代码改进。

项目主页：

https://github.com/botaruibo/MyVoiceTyping
