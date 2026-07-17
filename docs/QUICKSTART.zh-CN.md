# 快速上手 / macOS 试用指南

这份指南给第一次试用 MyVoiceTyping 的用户。目标是在 3–5 分钟内完成：下载 → 授权 → 试一句中文 → 判断是否值得继续使用或 Star。

> MyVoiceTyping 仍处于早期阶段。如果你遇到安装、权限、模型下载、转写、润写或粘贴问题，欢迎提交脱敏后的反馈。

## 1. 下载最新版

当前推荐先下载 `release-0.02`：

https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02

在 Assets 里下载：

```text
MyVoiceTyping_Installer.dmg
```

如果只是想看所有版本，可以打开 Releases：

https://github.com/botaruibo/MyVoiceTyping/releases

如果 macOS 提示无法打开来自未知开发者的应用，请先确认你下载的是本仓库 Release 页面里的文件，再按系统提示到“系统设置 → 隐私与安全性”里允许打开。

## 下载前 / 首次启动 60 秒检查

为了避免第一次试用时卡住，建议按下面顺序检查：

1. 下载来源必须是本仓库 Release 页面，不要从第三方网盘或未知镜像下载；
2. 如果 macOS 阻止打开应用，先到“系统设置 → 隐私与安全性”里确认并允许打开；
3. 首次启动后，按提示授予麦克风、辅助功能和输入监控权限；
4. 不要一开始就在真实工作群、客户文档或 AI agent 输入框里测试，先用“备忘录”；
5. 第一次模型下载可能需要网络、代理或较长等待时间；
6. 先用 [30 秒试用任务](./TRIAL_TASKS.zh-CN.md) 的虚构句子测试，不要输入公司机密、客户信息、Token、密码或私人原文；
7. 如果卡在权限、模型下载、录音或粘贴，可以按 [FAQ / Troubleshooting](./FAQ.md) 排查，或提交脱敏反馈。

最短试用路径：

```text
下载 DMG → 打开应用 → 授权麦克风 / 辅助功能 / 输入监控 → 打开备忘录 → 按住快捷键说一句虚构测试语 → 检查是否粘贴成功
```

## 下载前先看：会要哪些权限 / 会下载什么？

如果你只是因为“DMG、权限、模型下载”犹豫，可以先看这张表。MyVoiceTyping 是语音输入工具，所以这些步骤比较难完全绕开，但每一步都有明确用途。

| 看到的步骤 | 为什么需要 | 如果没完成会怎样 | 卡住时怎么反馈 |
|---|---|---|---|
| 打开 DMG / macOS 安全提示 | 确认你打开的是 GitHub Release 里的安装包 | 应用可能被系统拦截，无法启动 | 反馈 macOS 版本和提示截图，不要上传私人内容 |
| 麦克风权限 | 录制你按住快捷键时说的话 | 不能录音，或录到空音频 | 说明是否能看到录音浮窗 / 是否有音频文件 |
| 辅助功能权限 | 把识别后的文本粘贴到当前输入框 | 有转写结果但不能自动粘贴 | 说明目标应用，例如备忘录、浏览器、Cursor |
| 输入监控权限 | 监听全局快捷键 | 按快捷键没有反应 | 说明用的快捷键和键盘类型 |
| 首次模型下载 | 下载本地 ASR、标点和润写模型，避免把大模型塞进 DMG | 下载慢、失败或首次启动等待较久 | 说明网络环境、是否公司网络、是否需要代理 |

安全边界：

- 请只从 [release-0.02](https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02) 或 [DMG 直链](https://github.com/botaruibo/MyVoiceTyping/releases/download/release-0.02/MyVoiceTyping_Installer.dmg) 下载；
- 首次试用请用虚构内容，先不要输入公司机密、客户信息、Token、内部代码或私人聊天；
- 模型下载需要联网，但默认语音识别、标点恢复和文本润写链路尽量在本机完成；
- 如果你因为这些步骤放弃下载，也欢迎直接提交 [没下载 / 安装卡点反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=download_install_blocker.md) 或 [3 分钟 Beta 反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=beta_3min_feedback.md)，只写“不下载的原因”也可以。

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
