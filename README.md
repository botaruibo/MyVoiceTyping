# MyVoiceTyping


面向 macOS 的本地优先中文语音输入工具：按住快捷键，说话，松开后自动转写、恢复标点、轻量纠错并粘贴到当前输入位置。


[![GitHub stars](https://img.shields.io/github/stars/botaruibo/MyVoiceTyping?style=flat-square)](https://github.com/botaruibo/MyVoiceTyping/stargazers)
[![Latest release](https://img.shields.io/github/v/release/botaruibo/MyVoiceTyping?style=flat-square)](https://github.com/botaruibo/MyVoiceTyping/releases)

🌐 Website: https://botaruibo.github.io/MyVoiceTyping/landing/  
⬇️ Download: https://github.com/botaruibo/MyVoiceTyping/releases  
🔒 Privacy: https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/PRIVACY.md  
🛡️ Security: https://github.com/botaruibo/MyVoiceTyping/blob/main/SECURITY.md

<p align="center">
  <img
    src="docs/assets/launch/01-hold-to-speak.png"
    alt="MyVoiceTyping - Hold to speak. Release to paste."
    width="100%"
  />
</p>


适合：写文档、回消息、记录需求、整理想法、AI Coding 需求描述，以及重视本地隐私的中文输入场景。


## 为什么做这个项目


MyVoiceTyping 可以理解为 Typeless 的开源平替方向：它同样关注“说话直接变成可用文字”的输入体验，但更强调 0 费用、本地数据安全、可审查和可复现。


核心差异：


- 本地优先：默认尽量让音频和文本留在本机，减少敏感内容外传。
- 0 费用：开源项目，可直接试用、学习和二次开发。
- 中文优先：重点优化 macOS 中文语音输入、标点恢复和轻量纠错/润写。
- 可复现：应用、输入文本润写模型和调优数据集都公开。
- 自进化方向：用户确认后的改写数据可定期作为本地训练/调优数据，让本地 LLM 越用越贴合个人表达习惯。


核心链路：


`语音 → SenseVoiceSmall ONNX → 标点恢复 → MyVoiceTyping-1.5b-q4 GGUF 纠错/轻量润写 → 粘贴`


默认音频和文本不上传云端。当前主要目标平台为 macOS。

隐私与数据安全边界见 [Privacy / Data Safety](docs/PRIVACY.md)。后续计划见 [Roadmap](ROADMAP.md)。如果你正在比较 Typeless、闪电说、Typeoff、Wispr Flow、Handy、MacParakeet 等语音输入工具，可以看 [同类工具对比 / 选型建议](docs/ALTERNATIVES.zh-CN.md) 或 [Alternatives / Comparison](docs/ALTERNATIVES.md)。


## Self-evaluation / 自进化


语音输入最难的地方，不只是识别准确率，而是“越来越像你自己会写出来的话”。MyVoiceTyping 后续会围绕 self-evaluation / 自进化继续打磨：


1. 语音输入先生成初稿；
2. 用户根据自己的真实表达习惯修改、确认；
3. 这些确认后的改写结果可以沉淀为本地偏好数据；
4. 定期用于本地 LLM 的训练或轻量调优；
5. 让模型逐步适应个人词汇、语气、常用表达和工作场景。


这个方向会优先遵守本地优先原则：用于调优的数据应尽量保留在用户自己的设备上，由用户自行控制是否保留、删除或参与训练。


## 3 分钟开始


1. 下载最新 [Release](https://github.com/botaruibo/MyVoiceTyping/releases)。
2. 首次启动时授予麦克风、输入监控和辅助功能权限。
3. 按住快捷键说一句中文，松开后查看结果。
4. 首次启动会按需下载本地模型；模型文件不会进入 Git 仓库或安装包。

想先看输入效果，可以查看 [Demo / 使用效果示例](docs/DEMO.md)；如果想录制、转发或投稿，可以参考 [Demo assets / 演示传播素材](docs/DEMO_ASSETS.md) 和 [Demo video script / 录屏脚本](docs/DEMO_VIDEO.md)。遇到权限、模型下载、转写质量或粘贴问题，请先查看 [FAQ / Troubleshooting](docs/FAQ.md)。


## 三个开源资产


- 应用：[MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- 文本润写模型：[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- ASR 后纠错数据集：[MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

License / 使用边界：应用代码许可证仍在确认中，见 [Issue #7](https://github.com/botaruibo/MyVoiceTyping/issues/7)；模型页当前标注 Apache-2.0，同时请遵守上游 Qwen 模型许可；数据集由多个公开来源整理而来，使用、再分发、商业训练或公开发布模型前，请查看 Dataset 的 [DATA_LICENSE](https://github.com/botaruibo/MyVoiceTyping-Dataset/blob/main/DATA_LICENSE.md) 和 [SOURCES](https://github.com/botaruibo/MyVoiceTyping-Dataset/blob/main/docs/SOURCES.md)，并确认各原始数据源的许可证、引用要求和使用边界。

模型在应用中的作用、Ollama / llama.cpp 使用方式和数据边界见 [Model usage / 模型使用说明](docs/MODEL.md)。


如果它解决了你的中文输入问题，欢迎先实际体验，再通过 Star 关注后续版本；安装、权限、转写、润写或 AI Coding prompt 问题可以通过 [Issue templates](https://github.com/botaruibo/MyVoiceTyping/issues/new/choose) 提交结构化反馈。想参与反馈、文档或代码改进，请查看 [Contributing](CONTRIBUTING.md)；如果发现日志、调试信息、模型下载或 self-evaluation 数据相关的安全 / 隐私问题，请先查看 [Security Policy](SECURITY.md)。


![MyVoiceTyping dashboard](docs/img/myvoicetyping-dashboard.png)


## Downloads / Releases




- [release-0.02](https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02)
- [release-0.01](https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.01)




## Changelog




### release-0.02




- 优化首页和设置页 UI，新增更清晰的统计卡片、最近输入编辑区和关于页。
- 默认使用全本地链路：SenseVoice ONNX ASR、CT-Transformer 标点恢复、本地 GGUF 文本改写。
- 文本改写模型切换为 [botaruibo/MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)。
