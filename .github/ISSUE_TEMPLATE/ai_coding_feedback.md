---
name: AI Coding prompt 反馈
about: 反馈用 MyVoiceTyping 口述 Bug、重构需求、PR note 或测试说明给 AI Coding 工具的效果
title: "[AI Coding Feedback] "
labels: feedback, ai-coding
assignees: ""
---

感谢试用 MyVoiceTyping 的 AI Coding 场景！这个模板主要用于验证：语音输入生成的文本，能不能直接变成 Codex / Claude Code / Cursor / OpenCode / Copilot Chat 等工具可理解、可执行的 prompt。

请不要提交公司内部代码、私有仓库路径、客户信息、密钥、日志或任何敏感内容。可以用脱敏 / 虚构样例复现问题。

## 使用环境

- macOS 版本：
- Mac 型号 / 芯片：例如 MacBook Air M2、Mac mini M4
- MyVoiceTyping 版本 / Release：
- 使用的 AI Coding 工具：
  - [ ] Codex
  - [ ] Claude Code
  - [ ] Cursor
  - [ ] OpenCode
  - [ ] Copilot Chat
  - [ ] 浏览器 AI Chat
  - [ ] 其他：

## 测试场景

你这次主要口述的是哪类 prompt？

- [ ] Bug 复现步骤
- [ ] 重构需求
- [ ] 新功能说明
- [ ] PR / commit note
- [ ] 测试用例说明
- [ ] 代码审查意见
- [ ] 让 agent 修改文件 / 跑命令
- [ ] 其他：

## 可公开的口述大意

请用脱敏内容描述你大概说了什么：

```text
例如：帮我检查登录页面，用户点击发送验证码后按钮应该进入倒计时，如果接口报错需要恢复按钮并显示错误信息。
```

## MyVoiceTyping 输出结果

请贴出实际粘贴到 AI Coding 工具里的文本：

```text

```

## 理想输出

如果你手动改过，请贴出你最终希望发送给 AI Coding 工具的版本：

```text

```

## 主要问题

- [ ] 技术词 / 产品名识别错误
- [ ] 函数名 / 文件路径 / 命令被改坏
- [ ] 中文和英文之间空格不自然
- [ ] 标点或分段影响 agent 理解
- [ ] 润写过度，改变了技术含义
- [ ] 润写不足，仍然太口语
- [ ] 长 prompt 丢信息
- [ ] 粘贴后自动提交 / 没有 review 空间
- [ ] 延迟太高
- [ ] 其他：

## 对 agent 的实际影响

- [ ] agent 能直接理解并执行
- [ ] agent 基本理解，但需要我再手动改几处
- [ ] agent 误解了需求
- [ ] prompt 信息丢失，无法执行
- [ ] 我还没有发送，只测试了输入效果

## 补充说明

如果方便，请说明：

- 这个 prompt 大概多少字；
- 是否包含中英混合、代码符号、路径、命令；
- 是否希望保留更口语的表达，还是希望自动整理成更正式的任务描述。
