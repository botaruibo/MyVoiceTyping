# Model usage / 模型使用说明

This document explains how the MyVoiceTyping text polishing model fits into the full voice typing app.

模型地址：

- ModelScope: [botaruibo/MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)

相关项目：

- App: [MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- Dataset: [MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

## What is this model for?

`MyVoiceTyping-1.5b-q4` is a local GGUF model for Chinese ASR post-processing.

It is not a general chat model. It is designed for the text that comes after speech recognition, especially:

- correcting ASR mistakes;
- restoring punctuation;
- improving sentence boundaries;
- fixing common Chinese word errors;
- keeping the original meaning;
- avoiding unnecessary rewriting;
- preserving existing links, URLs, Markdown links, and image syntax.

In the full MyVoiceTyping app, it sits after local ASR and punctuation restoration:

```text
voice → local ASR → punctuation restoration → MyVoiceTyping-1.5b-q4 correction / light polishing → paste
```

## Why does MyVoiceTyping use a local model?

Voice input often contains sensitive content:

- product requirements;
- bug descriptions;
- code ideas;
- work notes;
- private messages;
- meeting notes;
- personal writing habits.

MyVoiceTyping's route is local-first. The goal is to keep audio, transcripts, and user-confirmed edits on the user's machine whenever possible.

The model is published separately so users and developers can inspect, test, reuse, and improve the ASR post-processing part independently.

## Quick use with Ollama

Download the model files from ModelScope, then run in the model directory:

```bash
ollama create myvoicetyping-1.5b-q4 -f Modelfile
```

Example prompt:

```text
<ASR_POST><MIN_EDIT><CORRECT><NO_NEW_LINKS><PRESERVE_EXISTING_LINKS>
场景：general
原文：今天下五我想去医院看一下感冒药怎么吃
```

Expected output style:

```text
今天下午我想去医院看一下感冒药怎么吃。
```

## Quick use with llama.cpp

You can also load the GGUF file directly with llama.cpp:

```bash
llama-cli -m MyVoiceTyping-1.5B-Q4_K_M.gguf -p "<|im_start|>system
你是ASR和中文文本后处理纠错助手。纠正错字词、实体专名、常用词组、语病和句意不顺，并修补必要的标点和断句。保持原意，仅做必要的最小修改。禁止额外追加链接、URL、Markdown链接、Markdown图片或解释。如果原文中已有链接、URL、图片Markdown、HTML图片片段或文件路径，必须原样保留，不要新增、删除或改写。<|im_end|>
<|im_start|>user
<ASR_POST><MIN_EDIT><CORRECT><NO_NEW_LINKS><PRESERVE_EXISTING_LINKS>
场景：general
原文：今天下五我想去医院看一下感冒药怎么吃<|im_end|>
<|im_start|>assistant
"
```

## Recommended prompt pattern

The model was trained with tagged prompts. For best results, use:

```text
<ASR_POST><MIN_EDIT><CORRECT><NO_NEW_LINKS><PRESERVE_EXISTING_LINKS>
场景：{scene}
原文：{input}
```

Recommended scenes:

- `general`: everyday voice input;
- `coding`: AI Coding prompts, bug descriptions, PR notes;
- `note`: notes and personal writing;
- `message`: chat / email style input.

## How this differs from a general correction model

General Chinese correction models usually focus on written text.

MyVoiceTyping-1.5b-q4 focuses on ASR output, where the errors are different:

- sound-alike mistakes;
- missing punctuation;
- long spoken sentences;
- repeated spoken fragments;
- wrong entity names;
- mixed Chinese-English terms;
- URLs or Markdown that must not be rewritten.

The model should make the smallest useful edit, not rewrite the user's meaning.

## Self-evaluation / 自进化 direction

The long-term direction is self-evaluation / self-evolution:

1. The app produces an initial transcript or polished draft.
2. The user edits and confirms the final text.
3. The pair of initial output and user-confirmed text can become local preference data.
4. That local data can later be used to tune or evaluate the local LLM.

The goal is to make the model gradually align with the user's vocabulary, tone, work context, and preferred expression style.

This should remain user-controlled. User-confirmed edits may contain sensitive work or personal content, so they should not be uploaded automatically.

## Dataset

Training data is maintained here:

- [MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

The dataset focuses on Chinese ASR post-processing:

- ASR word correction;
- punctuation and sentence boundary recovery;
- entity and domain term correction;
- date / number formatting;
- Markdown / URL / link guarding.

## Try the full app

If you are looking for the complete macOS voice typing workflow, use the app instead of only running the model:

- [Download latest release](https://github.com/botaruibo/MyVoiceTyping/releases/latest)
- [FAQ / Troubleshooting](./FAQ.md)
- [Privacy / Data Safety](./PRIVACY.md)
- [Alternatives / Comparison](./ALTERNATIVES.md)

If the model or app helps your Chinese voice input workflow, please consider starring the repository:

[https://github.com/botaruibo/MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
