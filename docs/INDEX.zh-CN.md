# MyVoiceTyping 文档索引 / 从这里开始

如果你是从 Typeless、闪电说、Typeoff、OpenTypeless、OpenLess、SayIt、AI Coding 语音输入或本地隐私输入相关讨论点进来的，可以按下面路径快速判断 MyVoiceTyping 是否值得试用、Star、转发或参与反馈。

## 30 秒决策

| 你想做什么 | 先看这个 | 适合解决的问题 |
|---|---|---|
| 只想判断是否值得 Star | [30 秒试用任务](./TRIAL_TASKS.zh-CN.md) | 用虚构内容测试中文 / 中英混合、AI Coding prompt、工作消息和隐私敏感输入 |
| 想马上安装试用 | [快速上手](./QUICKSTART.zh-CN.md) | 下载 release-0.02、处理 macOS 安全提示、授予麦克风 / 辅助功能 / 输入监控权限 |
| 想看适用场景 | [使用场景](./USE_CASES.zh-CN.md) | 写 prompt、写消息、写 issue、写 PR note、整理想法 |
| 愿意帮忙试用 / 挑毛病 | [Beta 测试 / 3 分钟反馈](./BETA_TESTING.zh-CN.md) | 反馈安装权限、模型下载、中文 / 中英混合、AI Coding prompt、隐私说明和不 Star 阻碍 |
| 正在比较 Typeless / 闪电说 / Typeoff / OpenTypeless / OpenLess / SayIt | [同类工具对比](./ALTERNATIVES.zh-CN.md) | 判断 MyVoiceTyping 作为开源、本地优先、0 费用路线是否适合你 |
| 遇到权限、模型下载、粘贴或转写问题 | [FAQ / Troubleshooting](./FAQ.md) | 排查首次启动、权限配置、模型下载、转写质量、粘贴失败 |

## 项目定位

MyVoiceTyping 是面向 macOS 的开源、本地优先中文语音输入项目：

```text
按住快捷键 → 说话 → 本地 ASR → 标点恢复 / 轻量纠错 / 润写 → 粘贴到当前输入框
```

它不是会议转录工具，也不是要宣称全面替代成熟商业产品。当前更适合作为 Typeless / 闪电说 / Typeoff 之外的一个开源、本地优先、可审查、可改造方向。

核心公开资产：

- App：<https://github.com/botaruibo/MyVoiceTyping>
- 输入文本润写模型：<https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4>
- 调优数据集：<https://github.com/botaruibo/MyVoiceTyping-Dataset>

## 数据安全、模型和自进化

| 主题 | 文档 | 说明 |
|---|---|---|
| 隐私 / 数据安全 | [Privacy](./PRIVACY.md) | 说明本地优先边界、音频 / 文本 / 日志 / self-evaluation 数据处理原则 |
| 安全反馈 | [Security Policy](../SECURITY.md) | 如果发现日志、调试信息、模型下载或数据处理相关风险，先看这里 |
| 本地润写模型 | [Model usage](./MODEL.md) | 说明 MyVoiceTyping-1.5b-q4 在 ASR 后处理 / 轻量润写链路中的作用 |
| Self-evaluation / 自进化 | [Self-evaluation](./SELF_EVALUATION.md) | 说明用户确认后的改写结果如何作为本地偏好样本，先用于评估、热词和规则优化，后续在明确授权下探索本地轻量调优 |
| App 许可证决策 | [License decision](./LICENSE_DECISION.zh-CN.md) | 比较 MIT / Apache-2.0 / GPL / AGPL 对传播、收录、fork 和企业采用的影响 |

注意：不要把 self-evaluation 理解成默认上传用户隐私数据，也不要理解成完整自动训练闭环已经完成。它的目标是让用户确认后的文本在本地可控边界内成为偏好样本，先服务于评估、热词和规则优化，再逐步探索本地轻量调优。

## 如果你想推荐、投稿或转发

| 场景 | 使用文档 | 建议 |
|---|---|---|
| 在社区评论区透明补充项目 | [Community sharing](./COMMUNITY_SHARING.md) | 用口语化、维护者身份，不伪装路人，不刷屏 |
| 想看已经发布过哪些外部文章 / 讨论 | [Community proof](./COMMUNITY_PROOF.md) | 查看 CSDN、开源中国、知乎、掘金、SegmentFault、Watcha、周刊投稿等公开入口 |
| 投稿周刊、产品目录、媒体或作者私信 | [Press kit](./PRESS_KIT.md) | 使用 30 字、100 字、300 字简介和限制说明 |
| 准备录屏、截图、GIF 或演示素材 | [Demo assets](./DEMO_ASSETS.md) | 使用统一卖点、截图和录屏脚本 |
| 准备录制 30–60 秒视频 | [Demo video script](./DEMO_VIDEO.md) | 优先展示“按住说话 → 本地处理 → 粘贴”的完整链路 |

## 当前还没补齐的信任项

这两个点会影响周刊、awesome list、Product Hunt、目录站和企业/开发者采用判断：

- App repo license 仍在确认中：<https://github.com/botaruibo/MyVoiceTyping/issues/7>；决策参考见 [License decision guide](./LICENSE_DECISION.zh-CN.md)
- 真实 Demo/GIF 仍在准备中：<https://github.com/botaruibo/MyVoiceTyping/issues/8>

在这两个 issue 关闭前，不要把项目描述成“已 MIT / 已 Apache-2.0”或“已有完整 Demo 视频”。

## 如何反馈

如果你愿意帮这个早期开源项目变好，最有价值的反馈不是一句“好用/不好用”，而是可复现的场景：

- 如果你只愿意花 3 分钟，请先看 [Beta 测试 / 3 分钟反馈](./BETA_TESTING.zh-CN.md)；
- macOS 版本、芯片、目标 App；
- 是否授予麦克风、辅助功能、输入监控权限；
- 是否是中文 / 中英混合 / 技术词 / 文件路径 / 命令行 prompt；
- 原始口述大意、最终希望得到的文本、实际输出哪里错；
- 是否出现粘贴失败、焦点丢失、模型下载失败或润写过度。

反馈入口：

- 普通试用反馈：<https://github.com/botaruibo/MyVoiceTyping/issues/3>
- AI Coding prompt 反馈：<https://github.com/botaruibo/MyVoiceTyping/issues/5>
- 新 issue 模板：<https://github.com/botaruibo/MyVoiceTyping/issues/new/choose>

如果它解决了你的中文输入问题，欢迎 Star 关注后续版本。Star 对早期项目很重要：它会帮助更多 macOS 中文用户发现一个本地优先、0 费用、App / 模型 / 数据集公开的语音输入选择。
