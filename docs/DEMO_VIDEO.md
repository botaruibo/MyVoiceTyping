# 60 秒 Demo 录制脚本

这份文档用于录制可公开传播的 30–60 秒 Demo 视频或 GIF，帮助新用户快速理解 MyVoiceTyping 的核心价值。

推荐先看普通用户落地页：

- Website: <https://botaruibo.github.io/MyVoiceTyping/landing/>
- Download: <https://github.com/botaruibo/MyVoiceTyping/releases>
- 体验反馈: <https://github.com/botaruibo/MyVoiceTyping/issues/3>
- AI Coding 反馈: <https://github.com/botaruibo/MyVoiceTyping/issues/5>
- Demo/GIF 进展: <https://github.com/botaruibo/MyVoiceTyping/issues/8>

## 录制版本 A：AI Coding prompt

适合发到开发者社区、AI Coding 讨论、掘金、GitHub issue / discussion、Product Hunt 补充材料。

### 0–5 秒：痛点

画面：打开 Codex / Claude Code / Cursor / OpenCode / 浏览器 AI Chat 的空白输入框。

字幕：

```text
AI Coding 的瓶颈，有时不是模型，而是把需求说清楚。
```

旁白：

```text
写 bug 复现、重构要求、PR note 的时候，长 prompt 敲起来很慢。
```

### 5–10 秒：项目定位

画面：切到 MyVoiceTyping landing 首屏。

字幕：

```text
MyVoiceTyping：本地优先的 macOS 中文语音输入
```

旁白：

```text
我做了 MyVoiceTyping，一个 macOS 中文语音输入开源项目，可以理解成 Typeless 的开源平替方向。
```

### 10–30 秒：核心演示

画面：回到输入框，按住快捷键口述。

口述内容：

```text
帮我检查一下登录页面，用户点击发送验证码以后按钮应该进入倒计时，如果接口报错需要恢复按钮并显示错误信息。
```

目标输出：

```text
帮我检查一下登录页面：用户点击“发送验证码”以后，按钮应该进入倒计时；如果接口报错，需要恢复按钮并显示错误信息。
```

字幕：

```text
按住说话 → 本地 ASR → 标点恢复 → 轻量润写 → 粘贴
```

旁白：

```text
它不是会议转录，而是输入层：说完以后直接粘贴到当前输入框。
```

### 30–45 秒：差异点

画面：展示 landing 的截图区，或展示三张静态卡片。

字幕卡片：

```text
本地优先：尽量让音频和文本留在本机
0 费用：开源项目，可直接试用
可审查：应用、模型、数据集都公开
```

旁白：

```text
我更关注数据安全和可控性。语音输入里经常有工作需求、代码 prompt、私人消息，本地优先会更安心。
```

### 45–55 秒：Self-evaluation / 自进化

画面：展示 README 或 Demo 文档中 self-evaluation 相关段落。

字幕：

```text
后续方向：用用户确认后的改写结果，调优本地 LLM
```

旁白：

```text
后续还会做 self-evaluation：把你确认后的改写结果沉淀为本地偏好数据，让本地模型越来越贴合你的表达习惯。
```

### 55–60 秒：CTA

画面：展示 landing 页首屏的 “Star 关注项目” 和 “下载最新版”。

字幕：

```text
Landing: botaruibo.github.io/MyVoiceTyping/landing/
GitHub: botaruibo/MyVoiceTyping
```

旁白：

```text
如果你也在找本地优先的中文语音输入，欢迎试用、提反馈，或者在 GitHub 点个 Star。
```

## 录制版本 B：普通中文输入

适合发到微博、知乎想法、小红书、开源中国动弹、普通用户群。

把 10–30 秒的口述内容替换为：

```text
明天下午三点前帮我整理一下会议纪要，重点包括产品上线风险、客服反馈和下个版本的优先级。
```

目标输出：

```text
明天下午三点前，帮我整理一下会议纪要。重点包括：产品上线风险、客服反馈，以及下个版本的优先级。
```

## 画面检查清单

- 不出现真实公司代码、客户名、私聊、邮箱、Token、内部文档；
- 关闭菜单栏通知；
- 输入框字体足够大；
- 录屏前先预热模型，避免等待过长；
- 保留“输入前空白 → 口述 → 输出后文本”的完整链路；
- 结尾必须出现 landing URL 或 GitHub 仓库名；
- 如果视频平台允许放链接，优先放 landing，其次 Release 和 Issue #3 / #5。

## 发布文案

```text
我把 MyVoiceTyping 的 60 秒 demo 录出来了。

它是一个本地优先的 macOS 中文语音输入开源项目，可以理解成 Typeless 开源平替方向：按住快捷键说话，松开后本地识别、标点恢复、轻量纠错/润写，再粘贴到当前输入框。

适合写 AI Coding prompt、需求、Bug 复现、工作 IM，也适合在意数据安全的中文输入场景。

Landing：https://botaruibo.github.io/MyVoiceTyping/landing/
GitHub：https://github.com/botaruibo/MyVoiceTyping
```

## 不建议这样说

- 不说“完全替代 Typeless”；
- 不说“100% 隐私 / 绝对离线”；
- 不说“识别率吊打某某产品”；
- 不展示或上传敏感语音 / 文本样例。
