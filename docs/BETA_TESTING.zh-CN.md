# Beta 测试 / 3 分钟帮 MyVoiceTyping 挑毛病

MyVoiceTyping 还处在早期阶段。现在最需要的不是泛泛夸奖，而是真实 macOS 用户告诉我：

- 安装和权限哪里卡住；
- 中文 / 中英混合是否能用；
- AI Coding prompt 里的文件名、变量名、库名、错误信息有没有被误改；
- 标点、断句、轻量润写是否自然；
- 你为什么愿意或不愿意 Star。

如果你愿意帮忙测试，请先使用虚构内容，不要输入真实公司信息、客户信息、私人聊天、token、密码、内部路径或未脱敏日志。

## 适合参与的人

优先欢迎这些用户：

1. macOS 用户，平时大量输入中文或中英混合内容；
2. 正在比较 Typeless、闪电说、Typeoff、OpenTypeless、OpenLess、SayIt 或 Wispr Flow；
3. 经常给 Codex、Claude Code、Cursor、Copilot 写长 prompt；
4. 在意公司内容、代码 prompt、会议纪要、私人消息尽量留在本机；
5. 愿意接受早期开源项目的不完美，并能指出具体卡点。

暂时不太适合：

- 只需要成熟商业客服和跨平台同步；
- 只使用 Windows / Linux / iOS / Android；
- 不愿安装早期 App，也不愿看文档或 Trial tasks；
- 想把真实敏感工作内容直接贴到公开 issue。

## 3 分钟测试路径

### 1. 先看 20 秒项目入口

Website：

<https://botaruibo.github.io/MyVoiceTyping/>

请先判断：

- 你是否能在 20 秒内看懂它是做什么的；
- 你是否知道它和 Typeless / 闪电说这类工具的差异；
- 你是否知道它目前还是早期项目。

### 2. 用虚构内容做 30 秒试用任务

Trial tasks：

<https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/TRIAL_TASKS.zh-CN.md>

任选一条虚构任务即可。推荐先试 AI Coding 场景：

```text
帮我写一个 issue，说明登录页点击提交以后没有 loading，而且接口返回 500。请前端先加错误提示，后端查一下 trace id。
```

### 3. 如果愿意安装，再下载 release-0.02

Release：

<https://github.com/botaruibo/MyVoiceTyping/releases/tag/release-0.02>

首次使用通常需要处理：

- 麦克风权限；
- 辅助功能权限；
- 输入监控权限；
- 首次模型下载；
- macOS 安全提示。

如果卡住，请先看：

<https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/FAQ.md>

## 最希望收到的 5 类反馈

### 1. 安装 / 权限 / 模型下载

请反馈：

- macOS 版本；
- Mac 芯片；
- 哪一步卡住；
- 是否看得懂 Quickstart / FAQ；
- 是否因为权限或模型下载放弃试用。

### 2. 中文 / 中英混合转写质量

请反馈：

- 原始口述大意；
- 你期望得到的文本；
- 实际输出哪里错；
- 是否把中文、英文、技术词、文件名、变量名混在一起时更容易出错。

### 3. AI Coding prompt

如果你用它给 Codex / Claude Code / Cursor 口述需求，请重点看：

- 文件名是否被改坏；
- 变量名 / 库名是否被误改；
- 错误信息是否被润写到失真；
- 是否适合先粘贴到输入框里 review，再手动发送。

AI Coding 反馈入口：

<https://github.com/botaruibo/MyVoiceTyping/issues/5>

### 4. 隐私 / 本地优先 / self-evaluation

请反馈：

- Privacy 是否讲清楚了；
- 日志、调试信息、模型下载边界是否可信；
- self-evaluation 是否容易被误解成默认上传或默认自动训练；
- 你是否希望所有偏好样本只保留在本机。

Privacy：

<https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/PRIVACY.md>

Self-evaluation：

<https://github.com/botaruibo/MyVoiceTyping/blob/main/docs/SELF_EVALUATION.md>

### 5. Star / 不 Star 的真实原因

如果你看完或试完暂时不想 Star，也很有价值。请直接说最大阻碍：

- 没有真实 Demo/GIF；
- 模型 / 数据集的独立使用边界还需要看说明；
- 安装步骤看起来麻烦；
- 权限太敏感；
- 模型下载不清楚；
- 中文/中英混合质量不够；
- 不确定是否比 Typeless / 闪电说 / Typeoff 更适合你；
- 项目定位还不够清楚。

## 推荐反馈格式

```text
来自 3 分钟 Beta 测试反馈（已脱敏）：

- 用户类型：
- macOS / 芯片：
- 测试任务：
- 是否安装：
- 安装 / 权限 / 模型下载：
- 转写质量：
- 标点 / 断句：
- 技术词是否被误改：
- 粘贴行为：
- 隐私说明是否可信：
- 是否愿意继续用：
- 是否愿意 Star：
- 最大阻碍：
```

## 反馈入口

- 普通试用反馈：<https://github.com/botaruibo/MyVoiceTyping/issues/3>
- AI Coding prompt 反馈：<https://github.com/botaruibo/MyVoiceTyping/issues/5>
- 新 issue 模板：<https://github.com/botaruibo/MyVoiceTyping/issues/new/choose>
- Discussions 体验招募帖：<https://github.com/botaruibo/MyVoiceTyping/discussions/2>

如果 MyVoiceTyping 的方向确实解决了你的中文输入问题，或者你也希望看到一个开源、本地优先、0 费用、App / 模型 / 数据集公开的 Typeless / 闪电说之外选择，欢迎 Star 关注后续版本。

Star 对早期项目很重要：它会帮助我判断是否优先补 Demo/GIF、中文 / 中英混合质量、AI Coding prompt、安装体验和本地 self-evaluation。
