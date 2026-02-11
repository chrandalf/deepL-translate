# DeepL Free API connection helper

This repository contains a tiny Python utility to verify your DeepL API connection while keeping usage strict.

## Why this is safe for low quotas

The script only calls DeepL's **`/v2/usage` endpoint**. It does **not** submit text for translation, so connectivity checks do not spend translation characters.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Run

```bash
export DEEPL_API_KEY='YOUR_KEY_HERE:fx'
python src/connect_deepl.py
```

Expected output:

- `DeepL connection successful.`
- Current character/document usage counters (`Document usage: n/a` when DeepL does not return document counters).

## Notes

- Keep your API key in an environment variable; do not hardcode it in files.
- Free-tier keys (`:fx`) must use `https://api-free.deepl.com` (already wired in this script).
- Authentication uses the `Authorization: DeepL-Auth-Key <key>` header, which is required by DeepL's updated auth rules.
- Successful runs do not raise `SystemExit`, which keeps notebook/interactive usage cleaner.
