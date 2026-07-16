# MyVoiceTyping

面向 macOS 的本地优先中文语音输入工具：按住快捷键，说话，松开后自动转写、恢复标点、轻量纠错并粘贴到当前输入位置。

[![GitHub stars](https://img.shields.io/github/stars/botaruibo/MyVoiceTyping?style=flat-square)](https://github.com/botaruibo/MyVoiceTyping/stargazers)
[![Latest release](https://img.shields.io/github/v/release/botaruibo/MyVoiceTyping?style=flat-square)](https://github.com/botaruibo/MyVoiceTyping/releases)

适合：写文档、回消息、记录需求、整理想法，以及重视本地隐私的中文输入场景。

核心链路：

`语音 → SenseVoiceSmall ONNX → 标点恢复 → MyVoiceTyping-1.5b-q4 GGUF 纠错/轻量润写 → 粘贴`

默认音频和文本不上传云端。当前主要目标平台为 macOS。

## 3 分钟开始

1. 下载最新 [Release](https://github.com/botaruibo/MyVoiceTyping/releases)。
2. 首次启动时授予麦克风、输入监控和辅助功能权限。
3. 按住快捷键说一句中文，松开后查看结果。
4. 首次启动会按需下载本地模型；模型文件不会进入 Git 仓库或安装包。

## 三个开源资产

- 应用：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- ASR 后纠错数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

如果它解决了你的中文输入问题，欢迎先实际体验，再通过 Star 关注后续版本；安装问题请提交可复现的 [Issue](https://github.com/botaruibo/MyVoiceTyping/issues)。

![MyVoiceTyping dashboard](docs/img/myvoicetyping-dashboard.png)

## Downloads / Releases


- [release-0.02](https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02)
- [release-0.01](https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.01)


## Changelog


### release-0.02


- 优化首页和设置页 UI，新增更清晰的统计卡片、最近输入编辑区和关于页。
- 默认使用全本地链路：SenseVoice ONNX ASR、CT-Transformer 标点恢复、本地 GGUF 文本改写。
- 文本改写模型切换为 [botaruibo/MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)。
- 新增本地纠错和输入润色开关，关闭后启动时不预加载文本模型。
- 新增多热词词典管理，支持自定义词库和软件研发词库，默认仅加载自定义词库。
- 优化模型首次下载进度显示，减少下载过程中的界面闪烁。
- 优化 macOS 状态栏图标、侧边栏 logo 和应用图标资源。
- 增加 ASR 后处理场景识别日志，记录最终 scene 与 bundle id。


### release-0.01


- 初始可用版本。
- 支持 macOS 上按住 `Fn` 快捷键录音，松开后自动转写并粘贴到当前输入位置。
- 支持本地语音识别、标点恢复、录音浮窗、输入历史记录和基础统计。
- 支持模型缺失时首次启动自动下载。
- 支持基础设置页、日志目录入口和 macOS 权限引导。


## Highlights


- **输入更快**：用语音完成长句、段落和想法记录，减少键盘输入负担。
- **Typless 本地平替**：面向 macOS 常驻使用，按住快捷键即可在任意输入位置说话输入。
- **个人数据更安全**：默认全本地处理，音频和文本不上传云端，更适合敏感内容和办公场景。
- **自动整理文本**：转写后会做标点恢复、轻量纠错和简单润色，尽量保留原意。
