# my voice typing Apple PC 版本分析与优化报告

## 结论摘要

本项目当前已经事实上偏向 macOS 桌面语音输入：GUI 使用 Tk/customtkinter，状态栏和全局热键依赖 PyObjC/Quartz，打包使用 PyInstaller 生成 `.app`。如果本版本只支持苹果 PC 端，建议把平台目标明确收敛到 macOS，减少 Windows/Linux 兼容分支、依赖和文档承诺，让后续优化集中在权限、热键稳定性、启动速度、模型加载、文本写入体验和本地 rewrite。

Fn 按键目前使用 Quartz EventTap 监听 `kCGEventFlagsChanged` 并从 `CGEventGetFlags()` 里识别硬编码 mask `0x00800000`。这条路可行，但属于经验型实现，受 macOS 版本、键盘型号、系统“将 F1、F2 等键用作标准功能键”设置、外接键盘差异影响较大。更稳妥的产品策略是：Fn 可以保留为可选高级快捷键，但默认快捷键优先使用 Command/Option/Control/Shift 单键或组合键；如果一定要支持 Fn，应该补充运行时探测、诊断页面和降级方案。

本地 Ollama rewrite 目前已有实验代码 `LocalLlamaRewrite`，但尚未接入主流程。要完善本地使用，需要完成配置接入、provider 分发、Ollama 服务健康检查、模型管理、UI 设置、测试和打包权限说明。

## 项目现状

### 运行链路

- `run.py` 是主入口，设置启动日志和模型下载并发环境变量，然后启动 `FlashInputApp`。
- `src/main.py` 负责 GUI 初始化、热键注册、录音开始/停止、ASR、rewrite 和文本写入。
- `src/components/hotkey.py` 使用 Quartz EventTap 监听全局键盘事件。
- `src/core/stt_processor.py` 根据 `stt_provider` 选择 ASR provider，目前主要可用路径是 `funasr`。
- `src/core/text_rewrite.py` 中 `Rewrite` 已支持云端 OpenAI-compatible Chat API；`LocalLlamaRewrite` 是本地 Ollama/类 OpenAI 接口的实验实现。

### macOS-only 收敛建议

当前代码仍残留跨平台表达，例如 README 写跨平台，`src/main.py` 中有 Windows 音量控制分支，依赖里也有通用 GUI/窗口库。既然本版本只支持苹果 PC 端，建议：

1. 更新 README 和应用内文案，只承诺 macOS。
2. 将 Windows 音量控制、Linux 分支标记为 legacy，短期不再扩展。
3. 打包配置集中维护 PyInstaller `.app`，py2app 配置若不用可移入文档或删除。
4. 权限说明产品化：麦克风、辅助功能、自动化/AppleEvents、输入监控如果需要，应在首次启动或设置页给出明确指引。
5. 清理依赖：按 macOS 路径保留 `pyobjc-framework-*`、`sounddevice`、`customtkinter`、`funasr_onnx`、`onnxruntime`、`modelscope` 等，移除过期或无用依赖前先跑一次打包验证。

## Fn 按键实现分析

### 当前实现

`src/components/hotkey.py` 中：

- 通过 `CGEventTapCreate` 创建 session-level listen-only EventTap。
- 监听 `kCGEventKeyDown`、`kCGEventKeyUp`、`kCGEventFlagsChanged`。
- 使用 `CGEventGetFlags()` 读取 flags。
- `KNOWN_FN_MASKS = [0x00800000]`，检测到该 mask 后把当前键集合加入 `fn`。
- `ShortcutKey` 允许 `fn` 作为单键或与 `space`/修饰键组合。

优点是实现轻、无第三方热键库依赖、可以监听单独 Fn 这种 Carbon hotkey 通常不擅长处理的键。缺点是 Fn 不是普通虚拟键，稳定性比 Command/Option/Control/Shift 差；硬编码 mask 难覆盖所有键盘和系统设置。

### 是否有更优方式

没有一个“完全官方且简单”的 Fn 全局热键方式。可以按目标拆分：

1. 如果目标是产品稳定性：更优方式是不要把 Fn 作为默认快捷键。默认使用 `cmd_l`、`option_l`、`ctrl_l` 或 `fn+space` 的替代组合，并在设置页允许用户录制快捷键。
2. 如果目标是原生全局快捷键：对普通组合键使用 Carbon `RegisterEventHotKey` 或成熟库会更合适，但它不适合单独 Fn。
3. 如果目标是继续支持单独 Fn：当前 EventTap 方向基本合理，但需要增强探测和诊断，而不是只依赖固定 mask。
4. 如果目标是更底层、更完整的键盘状态：可研究 IOKit/HIDManager 监听键盘 HID usage，但复杂度、权限、打包和稳定性成本更高，不建议本版本优先投入。

### 建议改造

推荐方案：保留 EventTap，增强可靠性，并调整产品默认值。

1. 默认快捷键改为更稳定的 macOS 修饰键，例如“按住左 Command 说话，左 Option 免提”，或提供首次启动快捷键录制。
2. Fn 支持改为可选项：设置页中提示“Fn 在部分键盘上可能不可用”。
3. 扩展 Fn mask 探测：保留 `0x00800000`，允许 debug 模式记录 raw flags/keycode，用户按 Fn 后动态确认 mask。
4. 增加热键诊断工具：显示最近一次 `event_type`、`raw_flags`、`keycode`、解析后的 keys，便于定位外接键盘问题。
5. 增加超时和重启策略：当前已有 EventTap 健康检查，可补充权限失效、tap 被禁用、RunLoop 异常的用户可见状态。
6. 匹配策略优化：当前 exact match 会因为多按一个修饰键而不触发。可对“单键按住说话”保留 exact match，对组合键提供“包含匹配”选项，但要避免误触发。

## 本地 Ollama rewrite 需要补齐的事项

### 当前问题

`LocalLlamaRewrite` 已能向 `http://127.0.0.1:11434/api/chat` 发请求，但还不完整：

- 没有接入 `Rewrite.rewrite()` 的 `llm_text_provider` 分支，主流程只处理 `cloud_llm`。
- `base_url` 和 `model_name` 在类里硬编码为 `http://127.0.0.1:11434`、`qwen2.5:1.5b`，没有使用 `app_config.json` 里的 `ollama_model`。
- CLI 参数 `--base-url`、`--model` 已定义但没有传给 `LocalLlamaRewrite`。
- `test_local_llama()` 要求返回包含 `ok`，但测试 prompt 没明确要求模型输出 `OK`，容易误判。
- 本地 prompt 同时存在 `data/config/main_prompt.md` 和 `systemPrompt` 大字符串，重复维护风险高。
- 缺少 UI 设置、模型拉取/存在性检测、服务未启动提示、rewrite 降级策略和端到端测试。

### 推荐实现清单

1. 配置层：
   - 增加 `llm_text_provider = "cloud_llm" | "ollama"`。
   - 增加 `ollama_base_url`，默认 `http://127.0.0.1:11434`。
   - 增加 `ollama_model`，默认可用小模型如 `qwen2.5:1.5b`，也允许用户改为 `qwen3:8b`。
   - 增加 `ollama_timeout`、`ollama_temperature`、`ollama_num_predict`。

2. 代码分发：
   - 在 `Rewrite.__init__` 中维护 `local_llm_client` 或懒创建 `LocalLlamaRewrite`。
   - 在 `Rewrite.rewrite()` 中增加 `provider == "ollama"` 分支。
   - 云端与本地都失败时统一降级返回原 ASR 文本，不能阻塞或中断文本写入。

3. Ollama 客户端：
   - `LocalLlamaRewrite` 从配置读取 base URL/model，不硬编码。
   - 支持 `/api/chat` 为主；如果未来要兼容 OpenAI `/v1/chat/completions`，用显式 provider mode 区分。
   - 健康检查使用 `/api/tags` 判断服务可达和模型是否存在。
   - 模型不存在时给出命令建议：`ollama pull <model>`，不要在后台静默拉大模型，除非 UI 明确确认。

4. Prompt：
   - 统一使用 `data/config/main_prompt.md`，删除或降级 `systemPrompt` 常量。
   - 本地小模型可使用更短 prompt，减少延迟和跑偏。

5. UI：
   - 模型设置增加“文本优化引擎”：关闭、云端、本地 Ollama。
   - 本地模式显示 base URL、模型名、测试按钮、服务状态。
   - 测试按钮输出明确状态：服务不可达、模型不存在、请求超时、成功。

6. 性能：
   - 本地 rewrite 应设置短超时，例如 8-15 秒。
   - 对短文本可直接 rewrite；对长文本限制最大输入长度或提示用户。
   - 小模型建议低温度 `0.1-0.3`，`num_predict` 根据文本长度动态设置。

7. 打包与安装说明：
   - Ollama 不随 `.app` 打包，作为外部依赖说明安装：安装 Ollama、启动服务、拉取模型。
   - macOS 沙盒/签名如果未来启用，需要确认本机 loopback HTTP 访问权限。

8. 测试：
   - 单测 `_normalize_chat_completion_url()`、response 解析、配置读取。
   - 用 mock HTTP 测试服务不可达、模型不存在、成功 rewrite。
   - 用真实 Ollama 做手工验收：开启 `format_text=true`、`llm_text_provider=ollama`，录音后确认文本被本地优化并写入当前输入框。

## 其他可优化点

1. 配置默认值为空：`ConfigManager.default_config = {}`，配置缺失时会生成空配置，建议补完整默认值。
2. 配置大小写混用：`get()` 会 lower key，`set()` 不 lower key，长期可能产生重复键，建议统一 lowercase 写入。
3. 敏感信息：开发配置中存在真实 `api_key` 字段，应迁移到本地未跟踪配置或系统 Keychain。
4. 云端 STT 代码疑似过期：`CloudSTTProcessor` 使用属性式 config 和旧 OpenAI API 风格，且 `transcribe` 签名与 `STTProcessor` 调用不一致。
5. README 过时：仍描述 Alt+Space、Faster Whisper、跨平台支持，与当前实现不一致。
6. 测试/日志/音频文件较多：建议补 `.gitignore`，排除 `.DS_Store`、`logs/`、`data/audio/`、`test_data/*.wav`、模型目录、build/dist。
7. 打包配置重复：`pyproject.toml`、`setup.py`、`MyVoiceInput.spec` 同时存在，建议明确唯一推荐打包方式。

## 建议优先级

P0：

- 明确 macOS-only 文档和权限指引。
- 移除或隔离配置中的真实密钥。
- 补 `.gitignore`，避免日志、音频、模型和系统文件进入版本库。
- 为 `ConfigManager` 补默认配置。

P1：

- 将 Ollama rewrite 接入主流程。
- 设置页增加本地 Ollama 配置和测试。
- Fn 热键增加诊断和降级提示。

P2：

- 清理过期跨平台代码和云端 STT 实现。
- 统一打包方式与依赖。
- 为 ASR/rewrite/hotkey 增加自动化或半自动测试。
