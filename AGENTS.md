# AGENTS.md

## 项目概览

MyVoiceInput 是一个基于 Python 的桌面语音输入应用。当前版本目标平台仅为 Apple PC/macOS。除非用户明确要求恢复跨平台能力，否则 Windows/Linux 相关代码路径应视为历史兼容或未来参考，不作为本版本主要维护目标。

核心流程：

1. `run.py` 启动应用，配置启动日志，并创建 `src.main.FlashInputApp`。
2. `FlashInputApp` 构建 Tk/customtkinter UI，异步初始化重型服务，并启动全局热键监听。
3. `src.components.audio_recorder.AudioRecorder` 录制 PCM 音频。
4. `src.core.stt_processor.STTProcessor` 根据配置选择 ASR 后端。
5. ASR 输出可选地交给 `src.core.text_rewrite.Rewrite` 做文本改写。
6. 最终文本会被粘贴到当前聚焦的应用输入位置。

## 关键文件

- `run.py`：开发和打包后的应用入口。
- `src/main.py`：应用编排层，负责录音生命周期、扬声器静音/恢复、ASR、rewrite 和写回文本。
- `src/components/gui_tk.py`：customtkinter GUI 与 macOS 状态栏集成。
- `src/components/hotkey.py`：基于 macOS Quartz EventTap 的全局热键监听。
- `src/components/config_manager.py`：JSON 配置和 prompt 加载；macOS 打包应用会把可写配置放到 `~/Library/Application Support/MyVoiceInput`。
- `src/core/stt_processor.py`：ASR provider 分发入口。
- `src/core/stt_local_processor.py`：本地 FunASR ONNX/SenseVoice 实现，以及模型下载/加载逻辑。
- `src/core/stt_cloud_processor.py`：历史 OpenAI Whisper API 路径；使用前必须重新验证，因为方法签名和配置访问方式已经偏旧。
- `src/core/text_rewrite.py`：云端 LLM rewrite 与实验性的本地 Ollama rewrite。
- `data/config/app_config.json`：开发环境默认配置。不要提交真实密钥。
- `data/config/main_prompt.md`：云端 LLM rewrite 当前使用的 prompt。
- `MyVoiceInput.spec`：PyInstaller macOS `.app` 打包配置。
- `build_dmg.sh`：打包辅助脚本。

## 开发命令

安装依赖前建议先创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

常用定向检查：

```bash
python test_hotkey.py
python -m src.core.stt_local_processor
python src/core/text_rewrite.py --text "今天下午的需求评审内容很多 晚点整理成纪要"
```

当前打包方式以 PyInstaller 为主：

```bash
pyinstaller MyVoiceInput.spec
```

## 配置说明

`ConfigManager.get()` 会把查询 key 转成小写，因此代码里可能调用 `get("FORMAT_TEXT")`，而 JSON 中实际写的是 `format_text`。后续新增配置时，配置文件和 UI 写入都优先使用统一的小写 key。

重要配置项：

- `press_hotkey`：按住说话快捷键，当前默认 `fn`。
- `toggle_hotkey`：免提模式切换快捷键，例如 `option_l`。
- `stt_provider`：ASR provider；目前主要可用的本地路径是 `funasr`。
- `format_text`：是否启用 ASR 文本改写。
- `llm_text_provider`：当前主要是 `cloud_llm`；本地 Ollama 集成已有代码雏形，但尚未接入主 `Rewrite.rewrite()` 路径。
- `base_url`、`api_key`、`model_name`：云端 OpenAI-compatible LLM 配置。
- `ollama_model`：预期用于本地 rewrite 的模型配置；目前 `LocalLlamaRewrite` 尚未完整读取该配置。
- `mute_speaker`：录音期间是否静音系统外放。

不要向已提交文件中新增 API key 或私有 token。如果 `data/config/app_config.json` 中已经存在密钥，应视为敏感信息，避免在文档、日志或测试输出中重复暴露。

## 编码约定

- 保持应用 macOS-first。除非用户明确要求清理，否则不要大范围删除 Windows/Linux 分支；可以将它们视为历史兼容代码。
- 优先沿用现有模式：`ConfigManager` 单例、GUI 首屏后异步初始化、rewrite 失败时降级返回原始 ASR 文本。
- 不要在 Tk 主线程执行模型加载、网络请求、模型下载、ASR 或 rewrite 等耗时工作。
- 手工编辑文件时使用 `apply_patch`。
- 搜索项目内容时优先使用 `rg` 或 `rg --files`。
- 避免提交生成物：日志、`.DS_Store`、录音音频、下载模型、构建产物和 IDE 文件。

## 当前技术关注点

- Fn 键检测依赖硬编码 Quartz flags mask：`0x00800000`。如果要把 Fn 作为默认快捷键，必须先在目标 Mac 型号、键盘类型和系统设置下验证。
- `ShortcutDetector` 当前使用精确 key set 匹配。快捷键触发时如果额外按下其他修饰键，可能不会匹配。
- `LocalLlamaRewrite` 目前仍是独立/实验类：base URL 和 model 存在硬编码，CLI 参数没有完整传入，也尚未接入 provider 分发。
- `CloudSTTProcessor` 与 `STTProcessor.transcribe(file_path, audio_frames)` 的调用方式不一致，并且使用了 `ConfigManager` 不提供的属性式配置访问。
- `ConfigManager.default_config` 目前为空；配置缺失或损坏时，应用可能生成一个没有可用默认值的配置。
