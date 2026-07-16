# Security Policy

MyVoiceTyping is a local-first voice typing project. Security and privacy issues are especially important because voice input may contain work context, private messages, file paths, project names, code prompts, or other sensitive text.

## What to report

Please treat the following as security or privacy-sensitive issues:

- Raw audio, raw transcript, polished text, or user-confirmed text is written to normal logs.
- Debug output, crash reports, screenshots, or issue templates expose private dictation content.
- API keys, tokens, passwords, private paths, customer data, or company context can leak through logs or feedback flows.
- Voice input is submitted to an agent, chat app, third-party API, or cloud service without an explicit user action.
- Model download, cache, permission, or local file handling creates an unexpected security risk.
- Self-evaluation / user-confirmed edit samples are stored, exported, uploaded, or reused without clear user control.

## Reporting guidance

Please do not post secrets, private audio, private transcripts, or company data in a public issue.

When reporting a security or privacy issue, use the smallest safe reproduction:

- Replace real project names with placeholders such as `ProjectA`.
- Replace real file paths with fake paths such as `/path/to/example.swift`.
- Replace tokens or keys with `REDACTED`.
- Avoid attaching full logs if a short sanitized excerpt is enough.
- Prefer screenshots with sensitive text blurred or removed.

If the issue can be discussed publicly without exposing sensitive data, open a GitHub issue using:

https://github.com/botaruibo/MyVoiceTyping/issues/new/choose

If the issue requires private coordination, contact the maintainer through the safest available private channel before sharing details. If no private channel is available, open a minimal public issue that says a sensitive report exists, without including the sensitive content.

## Logging and debug boundary

Normal logs should record only operational metadata such as state, duration, character counts, and error types.

Normal logs should not store:

- raw audio;
- raw transcript text;
- polished / rewritten text;
- user-confirmed final text;
- self-evaluation samples;
- tokens, passwords, or private file paths.

Text-level debug modes, if added, should be explicit, temporary, and clearly warn users not to dictate sensitive content while enabled.

## Self-evaluation data

The long-term self-evaluation direction is to let user-confirmed edits improve local vocabulary, cleanup rules, or local small-model tuning.

That data can be more sensitive than ordinary logs because it may contain real work content and personal writing style. It should therefore be:

- local-first by default;
- user-controlled;
- reviewable before training or export;
- removable by the user;
- never submitted to public issues or discussions unless explicitly sanitized.

## Related documents

- [Privacy / Data Safety](docs/PRIVACY.md)
- [Contributing](CONTRIBUTING.md)
- [FAQ / Troubleshooting](docs/FAQ.md)
