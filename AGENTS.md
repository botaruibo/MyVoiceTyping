# AGENTS.md

## 项目概览

MyVoiceTyping 是一个基于 Python 的桌面语音输入应用。当前版本目标平台仅为 Apple PC/macOS。除非用户明确要求恢复跨平台能力，否则 Windows/Linux 相关代码路径应视为历史兼容或未来参考，不作为本版本主要维护目标。

应用定位是本地优先的常驻语音输入工具：按住快捷键说话，松开后在本机完成 ASR、标点恢复、轻量文本纠错，并把结果粘贴到当前输入位置。默认链路不依赖云端 LLM，也不应把音频、文本或模型密钥外发。

核心流程：

1. `run.py` 启动应用，配置启动日志，并创建 `src.main.FlashInputApp`。
2. `FlashInputApp` 构建 Tk/customtkinter UI，异步初始化重型服务，并启动全局热键监听。
3. `src.components.audio_recorder.AudioRecorder` 录制 PCM 音频。
4. `src.core.stt_processor.STTProcessor` 分发到本地 FunASR/SenseVoice ONNX ASR。
5. ASR 输出经过本地标点恢复，并可交给 `src.core.text_rewrite.Rewrite` 做本地 llama.cpp/GGUF 纠错。
6. 原始转录文本和最终输出文本写入 `voice_history.jsonl`，最终文本会被粘贴到当前聚焦的应用输入位置。

## 关键文件

- `run.py`：开发和打包后的应用入口。
- `src/main.py`：应用编排层，负责录音生命周期、扬声器静音/恢复、ASR、rewrite 和写回文本。
- `src/components/gui_tk.py`：customtkinter GUI 与 macOS 状态栏集成。
- `src/components/hotkey.py`：基于 macOS Quartz EventTap 的全局热键监听。
- `src/components/config_manager.py`：JSON 配置和 prompt 加载；macOS 打包应用会把可写配置放到 `~/Library/Application Support/MyVoiceTyping`。
- `src/core/stt_processor.py`：ASR provider 分发入口。
- `src/core/stt_local_processor.py`：本地 FunASR ONNX/SenseVoice 实现，以及模型下载/加载逻辑。
- `src/core/text_rewrite.py`：本地 llama.cpp/GGUF 文本纠错主路径；云端/Ollama HTTP 相关代码只作为历史兼容或实验入口。
- `src/vendor/funasr_onnx/`：精简后的 FunASR ONNX 运行实现，当前是运行和打包依赖。
- `data/config/app_config.json`：开发环境默认配置。不要提交真实密钥；默认配置不应包含云端 LLM 地址、模型名或 API key。
- `data/config/main_prompt.md`：本地文本纠错 prompt；打包后会复制到用户可写配置目录。
- `MyVoiceTyping.spec`：PyInstaller macOS `.app` 打包配置。
- `build_dmg.sh`：打包辅助脚本。
- `scripts/build_app.sh`：推荐的 PyInstaller 构建入口。

## 开发命令

安装依赖前建议先创建虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

常用定向检查：

```bash
python3 test_hotkey.py
python3 -m src.core.stt_local_processor
python3 src/core/text_rewrite.py --text "今天下午的需求评审内容很多 晚点整理成纪要"
```

当前打包方式以 PyInstaller 为主：

```bash
source venv/bin/activate
scripts/build_app.sh
bash build_dmg.sh
```

## 配置说明

`ConfigManager.get()` 会把查询 key 转成小写，因此代码里可能调用 `get("FORMAT_TEXT")`，而 JSON 中实际写的是 `format_text`。后续新增配置时，配置文件和 UI 写入都优先使用统一的小写 key。

重要配置项：

- `press_hotkey`：按住说话快捷键，当前默认 `fn`。
- `toggle_hotkey`：免提模式切换快捷键，例如 `option_l`。
- `stt_provider`：ASR provider；目前主要可用的本地路径是 `funasr`。
- `format_text`：是否启用 ASR 文本改写。
- `llm_text_provider`：默认 `llama_cpp`，即本地 GGUF 文本纠错。`cloud_llm`、`ollama` 只作为历史兼容或实验路径，不是当前默认维护主线。
- `llama_cpp_model_id`、`llama_cpp_model_file`、`llama_cpp_model_path`：本地纠错模型下载和加载配置。
- `llama_cpp_temperature`、`llama_cpp_top_p`、`llama_cpp_top_k`、`llama_cpp_max_tokens`：本地纠错生成参数，默认应保持保守，避免大幅改写用户原意。
- `ollama_*`：历史兼容的本地 Ollama HTTP 配置。除非用户明确要求恢复 Ollama provider，否则不要把它作为默认方案。
- `mute_speaker`：录音期间是否静音系统外放。

不要向已提交文件中新增 API key、私有 token、内网地址或个人路径。`data/config/app_config.json` 中不应再出现云端 LLM 的 `base_url`、`api_key`、`model_name` 等字段；如用户本机存在私有配置，应保持未跟踪或被 `.gitignore` 忽略。

## 编码约定

- 保持应用 macOS-first。后续新增能力优先按 macOS 权限、打包、TCC 行为验证；不要重新引入 Windows/Linux 运行分支，除非用户明确要求。
- 优先沿用现有模式：`ConfigManager` 单例、GUI 首屏后异步初始化、rewrite 失败时降级返回原始 ASR 文本。
- 不要在 Tk 主线程执行模型加载、网络请求、模型下载、ASR 或 rewrite 等耗时工作。
- 默认文本纠错走 `llama_cpp`。不要新增 pycorrector 依赖或恢复 PyCorrector 场景；此前已决定移除该方案。
- 模型下载、模型加载和首次预热需要通过 GUI 进度或日志给出可观察状态，避免用户误以为应用卡死。
- 历史记录采用 `voice_history.jsonl`，每行至少包含 `dataId`、`input`、`output`。`input` 是 ASR 加标点后的原始文本，`output` 是 LLM 或手工修正后的最终文本。
- 手工编辑文件时使用 `apply_patch`。
- 搜索项目内容时优先使用 `rg` 或 `rg --files`。
- 避免提交生成物和本地文件：日志、`.DS_Store`、录音音频、下载模型、构建产物、IDE 文件、`.env*`、证书和密钥文件。

## 当前技术关注点

- Fn 键检测依赖 Quartz flags mask：`0x00800000`。默认热键仍是 `fn`，涉及键盘监听改动时必须在应用激活和非激活两种状态下验证。
- `ShortcutDetector` 当前使用精确 key set 匹配。快捷键触发时如果额外按下其他修饰键，可能不会匹配。
- `LocalLlamaCppRewrite` 是当前默认本地纠错路径。改动模型路径、下载逻辑或打包 hidden imports 时，要同时验证开发环境和 `.app` 内运行。
- `LocalLlamaRewrite`/Ollama HTTP 代码属于历史兼容路径；不要让默认配置依赖 Ollama daemon。
- `ConfigManager.default_config` 已提供默认值。新增配置时要同步开发默认配置、打包种子配置和 UI 读写逻辑。
- `MyVoiceTyping.spec` 不应打包 `data/models` 下的大模型；模型应在首次启动下载到用户 Application Support 目录。
