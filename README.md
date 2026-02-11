# DeepL Free API connection helper

This repository contains a tiny Python utility to verify your DeepL API connection and perform guarded, low-volume translations.

## Why this is safe for low quotas

- Default behavior only calls DeepL's **`/v2/usage` endpoint**.
- Translation is **opt-in** and requires `--allow-translate`.
- Translation is guarded by `--max-chars` (default: `200`) so you can keep usage strict.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 1) Connectivity / usage check (no translation cost)

```bash
export DEEPL_API_KEY='YOUR_KEY_HERE:fx'
python src/connect_deepl.py
```

## 2) Translate text (English -> German example)

```bash
python src/connect_deepl.py \
  --translate-text "A fox found a lantern and carried it through the quiet forest at night." \
  --target-lang DE \
  --allow-translate \
  --max-chars 120
```

## Notes

- Keep your API key in an environment variable; do not hardcode it in files.
- Free-tier keys (`:fx`) must use `https://api-free.deepl.com` (already wired in this script).
- Authentication uses the `Authorization: DeepL-Auth-Key <key>` header.
- Missing usage counters print as `n/a`.
- Successful runs do not raise `SystemExit`, which keeps notebook/interactive usage cleaner.
