# MyVoiceTyping：Typeless / 闪电说之外，一个本地优先的中文语音输入选择

如果你正在搜索 **Typeless 平替**、**闪电说替代**、**macOS 中文语音输入**、**本地语音输入** 或 **AI Coding 语音 prompt 工具**，可以先用这一页快速判断 MyVoiceTyping 是否适合你。

先说清楚：MyVoiceTyping 不是要宣称“完胜”成熟商业产品，也不是泛用版 Typeless 克隆。它更像一个窄定位的开源路线：

```text
macOS 中文 / 中英混合输入
→ 本地 ASR
→ 标点恢复、轻量纠错、文本润写
→ 粘贴到当前输入框
→ 用户确认后的文本沉淀为本地偏好样本
```

项目入口：

- GitHub：<https://github.com/botaruibo/MyVoiceTyping>
- 当前下载版本：<https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02>
- Landing page：<https://botaruibo.github.io/MyVoiceTyping/>
- 本地文本润写模型：<https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4>
- 调优数据集：<https://github.com/botaruibo/MyVoiceTyping-Dataset>

## 30 秒决策

如果你是从社区讨论点进来的，不需要先完整读完文档，可以直接按下面判断：

| 你的问题 | 建议动作 |
|---|---|
| 想先看项目是否靠谱 | 打开 [GitHub 仓库](https://github.com/botaruibo/MyVoiceTyping)，先看 README、MIT License、模型和数据集链接 |
| 想马上试用 | 下载 [release-0.02](https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02)，按 [Quickstart](./QUICKSTART.zh-CN.md) 走权限和模型下载 |
| 只想知道和 Typeless / 闪电说差在哪 | 先看下面“和 Typeless / 闪电说类产品的差异”，再看 [同类工具完整对比](./ALTERNATIVES.zh-CN.md) |
| 最关心数据安全 | 先看 [Privacy / Data Safety](./PRIVACY.md) 和本页“本地优先到底是什么意思？” |
| 对 Self-Evolution 感兴趣 | 先看 [Self-Evolution / 本地自进化说明](./SELF_EVALUATION.md)，不要把它理解成默认上传或成熟自动训练闭环 |
| 看完仍然不想下载 | 直接提交 [没下载 / 安装卡点反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=download_install_blocker.md)，告诉我卡在哪里 |

如果这个方向刚好解决了你的中文输入、AI Coding prompt 或隐私输入问题，欢迎在 GitHub 点 Star：<https://github.com/botaruibo/MyVoiceTyping>。

## 它更适合谁？

MyVoiceTyping 当前更适合这些用户：

- 使用 macOS，日常有大量中文或中英混合输入；
- 经常写 AI Coding prompt、bug 复现、PR note、需求说明、技术方案；
- 希望语音输入不要默认把音频、文本、公司内容发到云端；
- 能接受早期开源项目的不完善，愿意提交 issue 或反馈卡点；
- 觉得商业语音输入工具好用，但更想要一个 0 费用、可审查、可改造的本地优先选择。

如果你主要需要会议转录、多人说话识别、跨平台成熟客户端或完整商业级体验，MyVoiceTyping 目前可能还不是最佳选择。

## 和 Typeless / 闪电说类产品的差异

| 维度 | MyVoiceTyping 的取舍 |
|---|---|
| 定位 | 更聚焦 macOS 中文 / 中英混合输入，不做泛用全场景承诺 |
| 费用 | App 开源，0 费用使用 |
| 数据安全 | 默认本地处理语音识别、标点恢复和文本润写，不把音频 / 文本默认上传到云端模型 |
| 可审查性 | App、文本润写模型和调优数据集都公开，方便开发者检查和二次改造 |
| AI Coding | 特别关注 prompt、bug 复现、技术词、变量名、文件路径和命令行表达 |
| 个性化方向 | Self-Evolution / 本地自进化：让用户确认后的文本成为本机偏好样本 |
| 当前短板 | 仍处于早期，真实 Demo/GIF、安装体验和更多用户反馈还需要继续补齐 |

## 本地优先到底是什么意思？

MyVoiceTyping 的目标不是一句泛泛的“重视隐私”，而是把默认数据路径尽量放在本机：

- 音频、转写文本、历史记录和本地自进化样本应保留在用户设备上；
- 文本润写使用本地 GGUF 模型；
- 用户确认后的“原始转写 → 最终文本”可以写入本机 `voice_history.jsonl`；
- 这些样本不会自动进入公开数据集，也不会默认上传云端；
- 如果未来新增云端同步、共享样例或远程训练能力，应该明确标注数据去向，并提供显式开关。

更完整的数据边界见：[Privacy / Data Safety](./PRIVACY.md) 和 [Self-Evolution / 本地自进化说明](./SELF_EVALUATION.md)。

## Self-Evolution / 本地自进化是什么？

普通语音输入通常只解决“这一次有没有识别对”。MyVoiceTyping 想继续往后走一步：让本地模型逐渐理解你的表达习惯。

一个典型链路是：

1. 你按住快捷键说话；
2. App 生成原始转写、标点和轻量润写结果；
3. 你在输入框里确认、修改或重写；
4. App 把原始转写和最终确认文本作为本地偏好样本；
5. 在你确认后，这些样本可以参与本机 MLX LoRA 调优；
6. 调优后的模型转换为 GGUF Q4，用来替换本地文本润写模型。

所以它追求的不是“把你的数据送去训练公共模型”，而是“让你自己的本地模型越来越懂你”。

当前这个方向仍在 alpha 阶段推进，不应该理解成完整成熟的自动训练闭环已经全部完成。

## 可以先怎么试？

建议不要一上来就输入公司机密、客户信息、Token、内部代码或私人聊天。你可以先用虚构内容试这些场景：

- 口述一个 AI Coding prompt；
- 口述一段 bug 复现；
- 口述一条中英混合工作消息；
- 口述包含变量名、函数名、文件路径的技术说明；
- 口述一段你会手工改写的中文长句。

快速入口：

- 下载：<https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02>
- 快速上手：[Quickstart](./QUICKSTART.zh-CN.md)
- 30 秒试用任务：[Trial tasks](./TRIAL_TASKS.zh-CN.md)
- 如果不想下载，请直接说原因：[没下载 / 安装卡点反馈](https://github.com/botaruibo/MyVoiceTyping/issues/new?template=download_install_blocker.md)

## 社区回复时可以怎么透明介绍？

如果有人在讨论 Typeless、闪电说、本地语音输入、AI Coding prompt 或隐私输入，可以用这种低打扰说法：

> 我在做一个早期 macOS 开源项目 MyVoiceTyping，方向是 Typeless / 闪电说之外的本地优先中文语音输入。它不主打“完胜商业产品”，而是聚焦中文 / 中英混合、AI Coding prompt、0 费用、App/模型/数据集公开，以及用户确认文本驱动的本地自进化。比较适合想自己审查数据边界、或者希望输入内容默认留在本机的人。项目在这里：<https://github.com/botaruibo/MyVoiceTyping>

推荐保持透明维护者身份，不伪装路人，不在无关话题下刷屏。

## 如果你看完仍然不想 Star

这也很有价值。请直接告诉我是哪一步挡住了你：

- 没有真实 Demo/GIF；
- 不想授予 macOS 权限；
- 模型下载太麻烦；
- 本地优先边界还不够清楚；
- 已有 Typeless / 闪电说 / 豆包输入法够用了；
- 只支持 macOS，不符合你的环境；
- 项目太早期，还不敢用。

反馈入口：<https://github.com/botaruibo/MyVoiceTyping/issues/new?template=download_install_blocker.md>

如果它刚好解决了你的中文输入、AI Coding prompt 或隐私输入问题，欢迎在 GitHub 点一个 Star：<https://github.com/botaruibo/MyVoiceTyping>
