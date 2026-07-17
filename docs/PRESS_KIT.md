# Press kit / 投稿包

这页给周刊、产品目录、开源推荐、Appinn / 小众软件、Product Hunt、AlternativeTo、ModelScope 社区和作者私信使用。它的目标是让编辑或社区维护者在 1–2 分钟内判断 MyVoiceTyping 是否值得收录。

> 使用边界：请不要把 MyVoiceTyping 描述成“完全替代 Typeless / 闪电说 / Typeoff”，也不要宣传“100% 隐私 / 绝对离线 / 识别率吊打”。更准确的表达是：开源、本地优先、面向 macOS 中文 / 中英混合输入的早期项目。

## 基本信息

| 项目 | 内容 |
|---|---|
| 名称 | MyVoiceTyping |
| 一句话 | 开源、本地优先的 macOS 中文语音输入工具：按住快捷键说话，松开后转写、补标点、轻量纠错 / 润写，并粘贴到当前输入框。 |
| 适合人群 | macOS 中文 / 中英混合输入用户、AI Coding 用户、隐私敏感用户、想要可审查语音输入链路的开发者 |
| 项目主页 | <https://github.com/botaruibo/MyVoiceTyping> |
| Website | <https://botaruibo.github.io/MyVoiceTyping/> |
| 下载 | <https://github.com/botaruibo/MyVoiceTyping/releases> |
| 模型 | <https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4> |
| 数据集 | <https://github.com/botaruibo/MyVoiceTyping-Dataset> |
| FAQ | <https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/FAQ.md> |
| 同类工具对比 | <https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/ALTERNATIVES.zh-CN.md> |
| 试用任务 | <https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/TRIAL_TASKS.zh-CN.md> |
| Beta 测试 / 3 分钟反馈 | <https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md> |

## 30 字以内标题

```text
MyVoiceTyping：开源、本地优先的 macOS 中文语音输入工具
```

```text
MyVoiceTyping：Typeless / 闪电说之外的开源本地优先选择
```

```text
MyVoiceTyping：面向 AI Coding 的中文语音输入层
```

## 100 字简介

```text
MyVoiceTyping 是一个面向 macOS 的开源、本地优先中文语音输入项目。按住快捷键说话，松开后自动转写、恢复标点、轻量纠错 / 润写，并粘贴到当前输入框。它适合中文 / 中英混合输入、AI Coding prompt、工作消息和隐私敏感场景。
```

## 300 字简介

```text
MyVoiceTyping 是一个面向 macOS 的开源、本地优先中文语音输入项目。它的核心交互是：按住快捷键说话，松开后完成语音识别、标点恢复、轻量纠错 / 润写，并把结果粘贴到当前输入框。

它不是会议转写 SaaS，也不是完整 AI 助手，而是一个日常输入层：适合写需求、PR 说明、Bug 复现、工作消息、笔记，以及给 Codex、Claude Code、Cursor、Copilot 等 AI Coding 工具口述长 prompt。

相比成熟商业语音输入产品，MyVoiceTyping 仍处于早期；它的差异在于开源、本地优先、0 费用，并且应用、文本润写模型和 ASR 后处理数据集都公开。后续方向是 self-evaluation：用户确认后的改写结果可以作为本地偏好样本，先用于评估、热词和规则优化，后续在明确授权下探索本地轻量调优，让它更贴合个人表达习惯。
```

## 适合收录的栏目

- macOS 工具；
- 开源效率工具；
- AI Coding 工作流；
- 本地优先 / 隐私工具；
- 中文语音输入；
- 开源模型应用；
- 开源数据集实践；
- Typeless / 闪电说 / Typeoff / Wispr Flow 等语音输入工具对比。

## 推荐标签

```text
macOS, voice typing, speech-to-text, Chinese voice input, local-first, privacy, AI Coding, ASR, FunASR, text rewriting, open source
```

中文标签：

```text
macOS，语音输入，中文语音输入，本地优先，隐私，AI Coding，开源，ASR，文本润写，Typeless 平替方向
```

## 亮点

- 按住快捷键说话，松开后粘贴到当前输入框；
- 面向中文 / 中英混合输入，而不是只做英文 dictation；
- 本地优先，默认尽量减少音频和文本外传；
- 0 费用，开源项目，可直接试用和二次开发；
- 应用、文本润写模型、ASR 后处理数据集都公开；
- 适合 AI Coding prompt、工作消息、需求、Bug 复现、PR 描述；
- 探索 self-evaluation：用户确认后的改写样本可用于本地偏好评估 / 调优。

## 当前状态和限制

- 项目仍处于早期，体验不应和成熟商业产品直接等同；
- 当前主要面向 macOS；
- 真实 Demo / GIF 仍在补齐中，进展见 <https://github.com/botaruibo/MyVoiceTyping/issues/8>；
- App code uses the MIT License: <https://github.com/botaruibo/MyVoiceTyping/blob/main/LICENSE>；模型和数据集有独立使用边界，使用前请查看对应说明；
- 如果输入内容涉及公司、客户、隐私或内部代码，请不要把真实音频 / 文本提交到公开 issue 或评论区。
- 如果编辑、作者或早期用户愿意帮忙判断项目是否值得继续推荐，建议先看 Beta 测试 / 3 分钟反馈页：<https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md>。最有价值的反馈是安装权限、模型下载、中文 / 中英混合、AI Coding prompt、隐私说明，以及为什么愿意或不愿意 Star。

## 推荐截图

可以从下面页面选择截图或 launch card：

- Demo assets: <https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/DEMO_ASSETS.md>
- Social preview: <https://botaruibo.github.io/MyVoiceTyping/assets/social-preview.png>
- Website: <https://botaruibo.github.io/MyVoiceTyping/>

## 投稿短文案

```text
自荐一个开源项目：MyVoiceTyping，一个面向 macOS 中文 / 中英混合输入的本地优先语音输入工具。

它的交互是按住快捷键说话，松开后转写、补标点、轻量纠错 / 润写，再粘贴到当前输入框。比较适合写 AI Coding prompt、工作消息、需求、Bug 复现、PR 说明和笔记。

项目主打开源、本地优先、0 费用，应用、润写模型和数据集都公开。和 Typeless / 闪电说 / Typeoff 这类成熟商业产品相比，它更早期，但更适合在意可审查、可二开和本地数据安全的人。

GitHub: https://github.com/botaruibo/MyVoiceTyping
Website: https://botaruibo.github.io/MyVoiceTyping/
Beta testing: https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
```

## 英文短文案

```text
MyVoiceTyping is an open-source, local-first Chinese voice typing tool for macOS. Hold a hotkey, speak, release, and get transcribed, punctuated, lightly corrected, and polished text pasted into the current input field.

It is designed for Chinese / mixed Chinese-English dictation, AI coding prompts, work messages, notes, and privacy-sensitive input. The app, local text-polishing model, and ASR post-processing dataset are public.

GitHub: https://github.com/botaruibo/MyVoiceTyping
Website: https://botaruibo.github.io/MyVoiceTyping/
Beta testing: https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/BETA_TESTING.zh-CN.md
```

## 不建议的表达

- “完全替代 Typeless / 闪电说 / Typeoff”；
- “100% 隐私 / 绝对不上云 / 绝对离线”；
- “识别率吊打某某产品”；
- “已经被大量企业采用”；
- “自动学习用户隐私数据”。

更建议说：

- “Typeless / 闪电说之外的开源本地优先方向”；
- “默认尽量让音频和文本留在本机”；
- “用户确认后的改写样本可作为本地偏好数据，由用户控制是否保留、删除或参与调优”。
