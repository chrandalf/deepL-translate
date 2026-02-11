"""Minimal DeepL Free API connectivity check and guarded translation helper.

The default behavior calls only /v2/usage to confirm API access while avoiding
translation-character consumption. Translation requires explicit CLI flags.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

USAGE_URL = "https://api-free.deepl.com/v2/usage"
TRANSLATE_URL = "https://api-free.deepl.com/v2/translate"
AUTH_HEADER_NAME = "Authorization"
AUTH_HEADER_PREFIX = "DeepL-Auth-Key"
DEFAULT_MAX_TRANSLATE_CHARS = 200


def get_api_key() -> str:
    api_key = os.getenv("DEEPL_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Missing DEEPL_API_KEY environment variable. "
            "Set it to your DeepL auth key (free keys end with ':fx')."
        )
    return api_key


def build_auth_headers(api_key: str) -> dict:
    return {AUTH_HEADER_NAME: f"{AUTH_HEADER_PREFIX} {api_key}"}


def build_usage_request(api_key: str) -> urllib.request.Request:
    # DeepL deprecated passing auth_key in the form body; keep body empty.
    return urllib.request.Request(
        USAGE_URL,
        data=b"",
        headers=build_auth_headers(api_key),
        method="POST",
    )


def build_translate_request(api_key: str, text: str, target_lang: str = "DE") -> urllib.request.Request:
    body = urllib.parse.urlencode(
        {
            "text": text,
            "target_lang": target_lang,
        }
    ).encode("utf-8")
    headers = build_auth_headers(api_key)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    return urllib.request.Request(
        TRANSLATE_URL,
        data=body,
        headers=headers,
        method="POST",
    )


def urlopen_json(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc

    return json.loads(payload)


def fetch_usage(api_key: str) -> dict:
    return urlopen_json(build_usage_request(api_key))


def translate_text(api_key: str, text: str, target_lang: str = "DE") -> str:
    payload = urlopen_json(build_translate_request(api_key, text, target_lang=target_lang))
    translations = payload.get("translations", [])
    if not translations:
        raise RuntimeError("DeepL response did not contain translations")
    translated = translations[0].get("text")
    if not translated:
        raise RuntimeError("DeepL translation text missing in response")
    return translated


def format_usage(count_key: str, limit_key: str, usage: dict) -> str:
    count = usage.get(count_key)
    limit = usage.get(limit_key)
    if count is None or limit is None:
        return "n/a"
    return f"{count}/{limit}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DeepL Free API helper")
    parser.add_argument(
        "--translate-text",
        default="",
        help="Optional text to translate. If omitted, only usage check runs.",
    )
    parser.add_argument(
        "--target-lang",
        default="DE",
        help="Target language code for translation mode (default: DE).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_TRANSLATE_CHARS,
        help=(
            "Max allowed characters for --translate-text before aborting "
            f"(default: {DEFAULT_MAX_TRANSLATE_CHARS})."
        ),
    )
    parser.add_argument(
        "--allow-translate",
        action="store_true",
        help="Required safety switch before consuming translation characters.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        api_key = get_api_key()
    except Exception as exc:
        print(f"DeepL connection failed: {exc}", file=sys.stderr)
        return 1

    if not args.translate_text:
        try:
            usage = fetch_usage(api_key)
        except Exception as exc:
            print(f"DeepL connection failed: {exc}", file=sys.stderr)
            return 1

        print("DeepL connection successful.")
        print(f"Character usage: {format_usage('character_count', 'character_limit', usage)}")
        print(f"Document usage: {format_usage('document_count', 'document_limit', usage)}")
        return 0

    text_length = len(args.translate_text)
    if not args.allow_translate:
        print(
            "Translation blocked: add --allow-translate to confirm character usage.",
            file=sys.stderr,
        )
        return 1
    if text_length > args.max_chars:
        print(
            f"Translation blocked: {text_length} chars exceeds --max-chars={args.max_chars}.",
            file=sys.stderr,
        )
        return 1

    try:
        translated = translate_text(api_key, args.translate_text, target_lang=args.target_lang)
    except Exception as exc:
        print(f"DeepL translation failed: {exc}", file=sys.stderr)
        return 1

    print("DeepL translation successful.")
    print(f"Source chars sent: {text_length}")
    print(f"Target ({args.target_lang}): {translated}")
    return 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        raise SystemExit(exit_code)
