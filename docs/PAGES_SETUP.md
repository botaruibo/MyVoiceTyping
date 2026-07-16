# GitHub Pages setup

MyVoiceTyping already includes a static product landing page and launch screenshots in the repository:

```text
docs/landing/index.html
docs/landing/assets/
docs/assets/launch/
```

The expected public URL is:

```text
https://botaruibo.github.io/MyVoiceTyping/landing/
```

If the URL returns `404`, GitHub Pages has not been enabled yet.

## Option A: enable GitHub Pages from Settings

Open:

```text
https://github.com/botaruibo/MyVoiceTyping/settings/pages
```

In **Build and deployment**, set:

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

Then click **Save**.

GitHub usually needs a short time to publish the site. After deployment, verify:

```text
https://botaruibo.github.io/MyVoiceTyping/landing/
```

## Option B: deploy with GitHub Actions

This repository also includes:

```text
.github/workflows/pages.yml
```

It deploys the `docs/` directory to GitHub Pages on every push to `main` that changes `docs/**` or the workflow itself.

If GitHub Pages is not yet enabled from Settings, the workflow uses `actions/configure-pages` with `enablement: true` to try to create / enable the Pages site automatically.

You can also run it manually:

```text
Actions → Deploy GitHub Pages → Run workflow
```

## After Pages is live

Update the repository About sidebar:

```text
Website:
https://botaruibo.github.io/MyVoiceTyping/landing/
```

Suggested topics:

```text
voice-typing
speech-to-text
macos
chinese
local-first
asr
typeless-alternative
ai-coding
dictation
open-source
```

## Promotion use

Use the live landing page URL for:

- Product Hunt;
- Appinn / 小众软件;
- independent developer directories;
- README website link;
- community follow-up comments only when adding new useful context.

Avoid overclaiming privacy. Prefer:

```text
local-first
designed to keep audio and text on device by default
```

Avoid:

```text
100% private
fully offline
complete Typeless replacement
```
