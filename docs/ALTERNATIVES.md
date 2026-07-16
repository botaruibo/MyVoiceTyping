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

## Quick comparison table

| Tool / direction | Best fit | Strengths | Caveats |
|---|---|---|---|
| MyVoiceTyping | macOS Chinese / mixed Chinese-English input, AI Coding prompts, privacy-sensitive users, open-source tinkerers | Open source, local-first, zero-cost; public app/model/dataset; post-ASR punctuation, correction, light rewriting; local self-evaluation direction | Early-stage project; app license is still being finalized; currently macOS-focused |
| Typeless | Users who want a polished commercial product with less setup | Mature product experience and smoother onboarding | Pricing, data flow, and customization depend on the vendor; not the same as an inspectable open-source stack |
| OpenTypeless | Users who want a cross-platform, open-source Typeless alternative with configurable STT / LLM providers | Open source, free, Windows / macOS / Linux; multi-provider STT and LLM setup; app-aware writing direction | More of a general desktop AI voice input framework; Chinese / mixed Chinese-English optimization and public local polishing model + dataset are not its main differentiators |
| OpenLess | Users who want an open-source, local-first voice input tool centered on AI prompt workflows | Emphasizes user-owned code/data/credentials, global input boxes, prompt-oriented output, MIT/open-source positioning, and multi-platform direction | More of an open Typeless / prompt input tool; MyVoiceTyping is narrower around macOS Chinese / mixed Chinese-English post-ASR cleanup with a public local polishing model and dataset |
| Shandianshuo / Typeoff | Users who want a complete voice input product with commercial support and product polish | More complete product experience, potentially broader platform/cloud features | For sensitive input, users should check each product's data handling boundary |
| VoiceSnap / local dictation tools | Users who mainly need offline speech-to-text | Fully offline, lightweight, local dictation focus | Often closer to raw transcription; may not cover Chinese post-ASR polishing, self-evaluation, or the full input loop |
| Wispr Flow / English-first commercial dictation | English-first or cross-platform dictation users | Stronger commercial dictation polish and general writing UX | Chinese / mixed Chinese-English and local open-source inspectability may not be the main focus |

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

## If you are searching for "Typeless is too expensive" or "Typeless alternative"

Those searches are usually not only about recognition accuracy. They are about trade-offs:

- whether you want to pay for a long-term subscription;
- whether company notes, code prompts, meeting summaries, and private messages can go through cloud services;
- whether dictated text should appear in the current input field;
- whether Chinese, English, file names, variables, project names, and technical terms can be mixed naturally;
- whether the text can be reviewed before being sent;
- whether the tool can be inspected, modified, or tuned by the user.

MyVoiceTyping is a better fit if you mainly use macOS, often dictate Chinese / mixed Chinese-English text, care about local data safety, and prefer an open-source zero-cost stack with public app/model/dataset assets.

If you need a polished, stable, cross-platform product with commercial support today, a mature commercial tool may be a better choice. If you want a local-first stack you can inspect and gradually tune around your own vocabulary and writing habits, MyVoiceTyping is the more relevant direction.

## Compared with OpenTypeless

OpenTypeless is a strong open-source Typeless alternative direction. Its advantages are cross-platform support, free/open-source availability, and configurable STT / LLM providers such as Whisper-style STT, GLM-ASR, OpenAI, Claude, Qwen, Ollama, and other provider options.

MyVoiceTyping is intentionally narrower:

- It focuses on macOS Chinese / mixed Chinese-English voice typing.
- It publishes not only the app, but also the local text-polishing model and dataset.
- It is optimized around Chinese post-ASR punctuation, common recognition error correction, technical term preservation, and light rewriting.
- It is designed for AI Coding prompts, Chinese work messages, requirements, bug reports, PR descriptions, and other input-layer workflows.
- Its self-evaluation direction is to turn user-confirmed edits into local preference samples, so the local model can gradually fit the user's own vocabulary and style.

If you want cross-platform support and a configurable multi-provider desktop AI voice input framework, OpenTypeless may be a better fit. If you mainly need macOS Chinese / mixed Chinese-English input with public app/model/dataset assets and local personalization, MyVoiceTyping is more directly targeted at that use case.

## Compared with OpenLess

OpenLess is another very close open-source direction. It emphasizes local-first ownership, user-owned code/data/credentials, and turning voice into polished AI prompts in any focused input box.

MyVoiceTyping differs mainly in scope:

- It is currently more explicitly focused on macOS Chinese / mixed Chinese-English input.
- It publishes the app, local text-polishing model, and dataset as a connected open stack.
- Its core work is Chinese post-ASR cleanup: punctuation restoration, common ASR error correction, technical term preservation, and light rewriting.
- Its self-evaluation direction is to turn user-confirmed edits into local preference samples, so the local model can gradually fit the user's vocabulary and style.

If you want a more general open-source prompt dictation tool, OpenLess is worth comparing. If you care more about Chinese voice input, Chinese ASR post-processing, public model/dataset assets, and future local personalization, MyVoiceTyping is the more targeted option.

## Compared with Wispr Flow

Wispr Flow is a commercial AI dictation product focused on writing faster with voice across apps. It is strong in product polish and broad user experience.

MyVoiceTyping is not trying to clone every Wispr Flow feature. Its current focus is narrower:

- Chinese-first voice input;
- macOS desktop workflow;
- local ASR + punctuation + light text correction / polishing;
- privacy-sensitive usage where audio and text should stay on the user's machine as much as possible;
- open assets that can be reviewed and reused.

For English-first, cross-platform, highly polished commercial dictation, Wispr Flow may be a better fit. For Chinese developers and macOS users who want an open-source local-first stack, MyVoiceTyping is the more relevant direction.

## Compared with VoiceSnap / Handy / MacParakeet / OpenQuack / VocaMac / Turbo Whisper / OmniDictate / other local dictation tools

There are more and more local or low-cost dictation tools. Many of them are excellent, especially for English or general multilingual dictation.

Projects such as VoiceSnap, MacParakeet, Local Whisper, and Muesli emphasize fully offline dictation, local macOS dictation, cross-platform offline transcription, meeting transcription, or local voice input on their target platforms. They can be a good fit when the main requirement is turning speech into text offline, or when the goal is local meeting notes.

MyVoiceTyping's differentiation is not simply "local speech-to-text". Its focus is the full Chinese input loop:

1. Press a shortcut and speak.
2. Run speech recognition.
3. Restore punctuation and sentence boundaries.
4. Correct common ASR mistakes.
5. Lightly polish the text.
6. Paste the final text into the current input field.
7. Use user-confirmed edits as future local preference data.

The last two points are especially important for daily input. A raw transcript is often not enough; users need text that is usable in chat, email, documentation, AI Coding prompts, PR descriptions, and issue reports.

If your main need is raw local speech-to-text, an English-first dictation app, a fully offline Typeless alternative, a Whisper menu-bar utility, or a shortcut-driven recorder may already be enough. MyVoiceTyping is more focused on macOS Chinese / mixed Chinese-English input where the post-ASR step matters: punctuation, common ASR error correction, light rewriting, and future local personalization from user-confirmed edits.

## Compared with Prompt Line / AI Coding prompt input layers

Prompt Line and similar tools solve a different but related problem: prompt input for Claude Code, Codex CLI, Gemini CLI, and other AI Coding agents can be uncomfortable when the prompt is long, when you need history reuse, or when you want file / symbol search before pasting into a terminal.

MyVoiceTyping is more complementary than competitive here:

- Prompt Line / prompt input layers are better at organizing, editing, searching, and pasting prompts.
- MyVoiceTyping is better at turning Chinese / mixed Chinese-English speech into reviewable text.
- Both workflows should avoid "recording stopped, so submit immediately"; the safer path is transcript → editable prompt buffer → explicit send.
- For AI Coding, file names, variable names, library names, error messages, and mixed-language technical terms should be preserved rather than aggressively rewritten.

If you already have a comfortable prompt input layer, MyVoiceTyping can be the speech-to-text front end. If your main pain is prompt management, history reuse, file search, or terminal paste UX, a Prompt Line-style tool may be more directly useful.

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
