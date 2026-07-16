# Alternatives / Comparison

This page explains how MyVoiceTyping is positioned compared with other voice typing and AI dictation tools.

It is not meant to say that one tool is always better than another. Voice typing tools have different trade-offs: cloud vs local, commercial polish vs open source control, global multilingual support vs Chinese-first optimization, and subscription convenience vs self-hosted zero-cost usage.

中文版：[同类工具对比 / 选型建议](./ALTERNATIVES.zh-CN.md)

## Quick positioning

MyVoiceTyping is a local-first, open-source Chinese voice typing project for macOS.

You can think of it as a Typeless / Wispr Flow alternative direction for users who care more about:

- Chinese voice input on macOS;
- local data safety;
- zero subscription cost;
- open-source code;
- inspectable model and dataset assets;
- local LLM text polishing after ASR;
- self-evaluation / self-evolution from user-confirmed edits.

Current project assets:

- App: [MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
- Local text polishing model: [MyVoiceTyping-1.5b-q4](https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4)
- Dataset: [MyVoiceTyping-Dataset](https://github.com/botaruibo/MyVoiceTyping-Dataset)

## Compared with Typeless

Typeless is a polished commercial AI voice input product. It is usually a better choice if you want a mature product experience, broad platform support, and strong cloud AI editing out of the box.

MyVoiceTyping is different:

- It is open source.
- It focuses on macOS Chinese voice typing.
- It is designed around local-first data safety.
- It does not require a subscription for the open-source version.
- The app, text polishing model, and dataset are public.
- It is exploring self-evaluation: user-confirmed edits can become local preference data for future local model tuning.

If you want the most mature product today, Typeless may be more suitable. If you want an open, local-first, Chinese-focused voice typing stack that you can inspect, modify, and improve, MyVoiceTyping may be a better fit.

## Compared with Wispr Flow

Wispr Flow is a commercial AI dictation product focused on writing faster with voice across apps. It is strong in product polish and broad user experience.

MyVoiceTyping is not trying to clone every Wispr Flow feature. Its current focus is narrower:

- Chinese-first voice input;
- macOS desktop workflow;
- local ASR + punctuation + light text correction / polishing;
- privacy-sensitive usage where audio and text should stay on the user's machine as much as possible;
- open assets that can be reviewed and reused.

For English-first, cross-platform, highly polished commercial dictation, Wispr Flow may be a better fit. For Chinese developers and macOS users who want an open-source local-first stack, MyVoiceTyping is the more relevant direction.

## Compared with Handy / MacParakeet / OpenQuack / VocaMac / Turbo Whisper / OmniDictate / other local dictation tools

There are more and more local or low-cost dictation tools. Many of them are excellent, especially for English or general multilingual dictation.

MyVoiceTyping's differentiation is not simply "local speech-to-text". Its focus is the full Chinese input loop:

1. Press a shortcut and speak.
2. Run speech recognition.
3. Restore punctuation and sentence boundaries.
4. Correct common ASR mistakes.
5. Lightly polish the text.
6. Paste the final text into the current input field.
7. Use user-confirmed edits as future local preference data.

The last two points are especially important for daily input. A raw transcript is often not enough; users need text that is usable in chat, email, documentation, AI Coding prompts, PR descriptions, and issue reports.

If your main need is raw local speech-to-text, an English-first dictation app, a Whisper menu-bar utility, or a shortcut-driven recorder may already be enough. MyVoiceTyping is more focused on Chinese / mixed Chinese-English input where the post-ASR step matters: punctuation, common ASR error correction, light rewriting, and future local personalization from user-confirmed edits.

## Why local-first matters

Voice input often contains sensitive information:

- work notes;
- product requirements;
- bug descriptions;
- code ideas;
- private messages;
- meeting summaries;
- personal writing habits.

MyVoiceTyping's principle is that audio, transcripts, and user-confirmed edits should stay on the user's machine by default whenever possible.

If future cloud sync, cloud training, or shared sample features are added, they should be explicit, opt-in, and documented.

For more details, see [Privacy / Data Safety](./PRIVACY.md).

## What does self-evaluation / self-evolution mean?

Generic models do not always understand your vocabulary, tone, project names, team jargon, or writing habits.

MyVoiceTyping's self-evaluation direction means:

- The app generates an initial transcript / polished draft.
- The user edits and confirms the final text.
- The pair of "initial output → user-confirmed text" can become local preference data.
- That local data can later be used to tune or evaluate the local LLM.

The goal is to make the model become more aligned with the user's own expression style over time.

This should remain user-controlled. User-confirmed edits may contain sensitive information, so they should not be uploaded automatically.

## When should you use MyVoiceTyping?

Try MyVoiceTyping if you:

- mainly use macOS;
- often input Chinese or Chinese-English mixed text;
- want a Typeless-like workflow without a subscription;
- care about local data safety;
- want an open-source project you can inspect or modify;
- use voice to describe tasks to AI Coding tools;
- want future personalization through local self-evaluation data.

## When should you choose another tool?

Another tool may be better if you:

- need a polished commercial product immediately;
- need Windows, Linux, iOS, or Android support today;
- mainly dictate English long-form text;
- want cloud AI editing with minimal setup;
- do not want to manage local models or permissions;
- need enterprise support or team administration.

## Summary

MyVoiceTyping is not just another transcription app.

Its goal is to become a local-first, zero-cost, open-source Chinese voice typing layer for macOS, with a path toward self-evolving local personalization.

If that direction is useful to you, please try it, open an issue with feedback, or star the project to follow future releases:

[https://github.com/botaruibo/MyVoiceTyping](https://github.com/botaruibo/MyVoiceTyping)
