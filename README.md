# MyVoiceTyping

> 面向 macOS 的本地语音输入工具：用说话代替打字，让日常输入更快、更安全、更私密。

MyVoiceTyping 的目标很简单：让你在写文档、记需求、回消息、整理想法时少敲键盘，多直接表达。对大多数场景来说，说话比打字更快，也更接近日常思考的节奏。

它也可以作为 Typless 的本地化平替工具使用。默认能力全部在本机完成，不依赖云端模型，不上传音频和文本，更适合重视个人数据保护、隐私安全和合规要求的工作场景。

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
- **支持热词**：可维护常用技术词、项目词、人名，降低专有名词误识别。
- **输入工作台**：查看历史输入、累计字数和节约时间，也可以手工修正最近一次输入。
- **安装包更轻**：大模型不内置在安装包里，首次启动后按需下载到本机。

## Technical Highlights

- **全开源，可替换模型**：项目代码开放，ASR、标点恢复和文本纠错模型都可以按需替换。当前默认使用阿里 FunASR 生态中的模型，并通过 ONNX 推理实现，启动和运行性能更好。
- **本地化瘦身改造**：对运行链路做了本地化和打包裁剪，减少不必要的大依赖，瘦身安装包。
- **本地文本纠错与润色**：当前默认文本后处理模型为 [botaruibo/MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)。该模型基于 `qwen2.5:1.5b` 训练，并量化为适合本地运行的 GGUF 版本；
- **专用模型计划**：正在整理针对语音转录纠错、口语重复消除和格式化改写的数据样本，后续版本会替换为更适合语音输入场景的专用纠错润色模型。

## How It Works

```mermaid
flowchart LR
    A["Fn hotkey<br/>Quartz EventTap"] --> B["AudioRecorder<br/>sounddevice"]
    B --> C["WAV 保存<br/>Application Support"]
    C --> D["SenseVoiceSmall ONNX<br/>语音转文本"]
    D --> E["CT-Transformer ONNX<br/>标点恢复"]
    E --> F["llama.cpp GGUF<br/>文本纠错"]
    F --> G["voice_history.jsonl<br/>input/output 记录"]
    F --> H["pbcopy + CGEvent<br/>粘贴到当前输入框"]
```

核心路径：

1. `run.py` 启动应用，初始化日志和 `FlashInputApp`。
2. `src/main.py` 编排录音、静音、ASR、文本纠错、历史记录和粘贴。
3. `src/components/hotkey.py` 使用 macOS Quartz EventTap 注册全局快捷键。
4. `src/components/audio_recorder.py` 使用 `sounddevice` 录制 16k PCM 音频。
5. `src/core/stt_local_processor.py` 使用 vendored `funasr_onnx` + `onnxruntime` 做本地 ASR 和标点恢复。
6. `src/core/text_rewrite.py` 使用 `llama-cpp-python` 加载本地 GGUF 文本纠错模型。
7. `src/components/gui_tk.py` 提供 customtkinter 桌面 UI、历史记录、设置页和下载进度。

## Model Pipeline

默认使用 3 个本地模型：

| 阶段 | 模型 | 用途 | 默认下载目录 |
| --- | --- | --- | --- |
| ASR | `botaruibo/SenseVoiceSmall-onnx` | 语音转文本 | `~/Library/Application Support/MyVoiceTyping/data/models` |
| 标点 | `botaruibo/punc_ct-onnx` | 标点恢复 | 同上 |
| 纠错 | [botaruibo/MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)，基于 `qwen2.5:1.5b` 训练并量化 | ASR 文本纠错/简单润色 | 同上 |

模型文件不会提交到 Git，也不会被打包进 `.app`。首次启动时应用会按顺序检查和下载模型：

1. 语音转录模型
2. 标点恢复模型
3. 中文纠错 GGUF 模型

## Text Rewrite Model

[MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4) 是 MyVoiceTyping 当前默认使用的本地文本改写模型。它基于 `qwen2.5:1.5b` 训练，并量化为 GGUF 格式，主要用于 ASR 后处理：纠正常见错别字、减少口语重复、补足基础语义连贯性，并做非常轻量的输入润色。

模型特点：

- **本地运行**：通过 llama.cpp 加载 GGUF 量化模型，不依赖云端推理服务。
- **体积更小**：基于 1.5B 级别模型训练并量化，适合桌面常驻工具在启动速度、内存占用和效果之间取得平衡。
- **低改写倾向**：默认参数偏保守，目标是修正明显错误和轻量润色，而不是重写用户表达。
- **面向语音输入后处理**：当前版本主要用于 ASR 文本纠错、标点后文本整理和简单口语清理。
- **可替换**：模型路径、仓库 ID 和推理参数都在配置中，二开时可以替换为自己的 GGUF 模型。


开发环境默认数据目录在 `data/`；打包后的可写数据在：

```text
~/Library/Application Support/MyVoiceTyping/
├── audio/
├── config/
├── data/models/
├── logs/
└── transcripts/voice_history.jsonl
```

## Features

### 语音输入

- 默认按住 `Fn` 开始录音，松开后停止录音并转写。
- 录音期间可自动静音系统外放，结束后恢复原状态。
- 太短的音频会直接跳过，避免空录音生成无效文件。
- 录音浮窗使用 Cocoa 非激活面板，不抢占当前输入焦点。

### 本地文本处理

- SenseVoiceSmall ONNX 输出原始文本。
- CT-Transformer ONNX 恢复标点。
- llama.cpp 加载 `MyVoiceTyping-1.5b-q4` GGUF，对文本做轻量纠错和简单润色。
- 默认参数偏保守：低温度、低随机性，减少“自由发挥”。

### 历史与统计

- 首页显示今日记录、今日字数、历史记录、累计字数和已节约时间。
- `voice_history.jsonl` 每行记录一条输入：

```json
{"dataId":"20260625_222254.wav","input":"ASR 标点恢复文本","output":"LLM 或手工修正后的文本"}
```

- “最近一次输入”文本框支持手工编辑，便于修正最终输出。

### 隐私与安全

- 默认不使用云端 ASR，也不上传音频。
- 本地配置、音频、历史记录、模型都写入用户目录或开发环境 `data/`，并被 `.gitignore` 忽略。
- 打包时会清空配置中的 `api_key`、`token` 等敏感字段。
- 如果启用云端 LLM 或第三方服务，请自行确认数据合规和密钥管理。

## Requirements

- macOS on Apple Silicon is the primary target.
- Python 3.11 is recommended.
- 系统权限：
  - 麦克风：录制语音
  - 输入监控：后台监听全局快捷键
  - 辅助功能：向其他应用发送 `Cmd + V`

主要运行依赖：

- GUI：`customtkinter`, `Pillow`, PyObjC (`AppKit`, `Quartz`, `Foundation`)
- 录音：`sounddevice`, `soundfile`, `numpy`
- 本地 ASR：`onnxruntime`, vendored `funasr_onnx`, `kaldi-native-fbank`, `sentencepiece`, `jieba`
- 模型下载：`modelscope`
- 本地纠错：`llama-cpp-python`
- 打包：`PyInstaller`, `create-dmg` 或 macOS `hdiutil`

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

首次启动会检查本地模型；如果缺失，会显示下载进度。下载完成后模型会保存在本机，不需要每次重复下载。

## Build

当前打包方案以 PyInstaller 为准。

```bash
source venv/bin/activate
scripts/build_app.sh
```

生成 `.app` 后可以打包 DMG：

```bash
bash build_dmg.sh
```

为了减少 macOS TCC 权限在重装后失效，可以创建本地自签名代码签名证书：

```bash
bash create_signing_cert.sh
CODESIGN_IDENTITY="MyVoiceTyping Self-Signed" bash build_dmg.sh
```

说明：

- `MyVoiceTyping.spec` 不打包 `data/audio`、`data/models`、`data/transcripts` 下的运行数据。
- `build_dmg.sh` 会检查 `.app` 中是否包含默认配置和 prompt。
- 自签名证书主要用于稳定本机权限身份，不等价于 Apple Developer ID notarization。

## Project Structure

```text
.
├── assets/                    # App 图标和 UI 资源
├── data/config/               # 开发环境默认配置和 prompt，敏感配置不要提交
├── docs/                      # 项目文档和截图
├── scripts/build_app.sh       # PyInstaller 构建入口
├── src/
│   ├── components/            # GUI、录音、快捷键、录音浮层
│   ├── core/                  # STT、文本纠错、进度条
│   ├── util/                  # 日志、macOS 权限引导
│   └── vendor/funasr_onnx/    # 精简后的 funasr_onnx 运行实现
├── MyVoiceTyping.spec          # PyInstaller 配置
├── build_dmg.sh               # DMG 打包脚本
└── run.py                     # 应用入口
```

## Development Notes

- 代码默认按 macOS-only 维护，不再保留 Windows/Linux 兼容分支。
- 手工测试热键时注意系统权限，尤其是“输入监控”和“辅助功能”。
- 不要把以下内容提交到 Git：
  - `data/models/`, `data/audio/`, `data/transcripts/`
  - 本地私有配置，例如包含真实密钥的 `data/config/app_config.json`
  - `logs/`
  - `dist/`, `build/`, `.pyinstaller-cache/`
  - `*.gguf`, `*.onnx`, `*.safetensors`, `*.pt`, `*.pth`
  - `.env*`, `*.pem`, `*.p12`, `*.cer`, `*.key`
- 修改打包配置后建议执行：

```bash
venv/bin/python -m py_compile src/main.py src/components/gui_tk.py src/core/stt_local_processor.py src/core/text_rewrite.py
scripts/build_app.sh
```

## Contributing / 二次开发

欢迎围绕以下方向二开：

- 更稳定的全局快捷键策略，例如不同键盘/系统版本下的 Fn 掩码适配。
- 更轻的 ASR 推理链路，进一步降低打包体积。
- 更好的热词后处理策略，减少专有名词误识别。
- 更细粒度的历史记录管理，例如搜索、导出、批量清理。
- 更丰富的本地文本处理模型适配。

提交建议：

1. 保持 macOS-first，不引入未验证的跨平台分支。
2. 不提交模型文件、音频、日志、真实配置和任何 API Key。
3. 大依赖新增前先说明必要性和包体积影响。
4. UI 改动请附截图或说明测试过的窗口尺寸。
5. 打包链路改动请说明 `.app` 和 DMG 的验证方式。

## Credits

MyVoiceTyping 站在这些开源项目和生态之上：

- [FunASR](https://github.com/modelscope/FunASR) / SenseVoice
- [ONNX Runtime](https://onnxruntime.ai/)
- [ModelScope](https://modelscope.cn/)
- [llama.cpp](https://github.com/ggerganov/llama.cpp) and `llama-cpp-python`
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- PyObjC / macOS Cocoa, Quartz, ApplicationServices
- PyInstaller

## License

本项目源码建议采用 Apache License 2.0 开源。

模型文件不随源码仓库分发，首次运行时按需下载。SenseVoice、标点模型、中文纠错模型等模型权重遵循其上游模型仓库声明的 license；商业使用前请分别确认模型授权。
