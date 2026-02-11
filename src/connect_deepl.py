"""Minimal DeepL Free API connectivity check.

This script calls only the /v2/usage endpoint to confirm API access while
avoiding translation-character consumption.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

USAGE_URL = "https://api-free.deepl.com/v2/usage"
AUTH_HEADER_NAME = "Authorization"
AUTH_HEADER_PREFIX = "DeepL-Auth-Key"


def get_api_key() -> str:
    api_key = os.getenv("DEEPL_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Missing DEEPL_API_KEY environment variable. "
            "Set it to your DeepL auth key (free keys end with ':fx')."
        )
    return api_key


def build_usage_request(api_key: str) -> urllib.request.Request:
    headers = {
        AUTH_HEADER_NAME: f"{AUTH_HEADER_PREFIX} {api_key}",
    }
    # DeepL deprecated passing auth_key in the form body; keep body empty.
    return urllib.request.Request(USAGE_URL, data=b"", headers=headers, method="POST")


def fetch_usage(api_key: str) -> dict:
    request = build_usage_request(api_key)

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc

    return json.loads(payload)


def format_usage(count_key: str, limit_key: str, usage: dict) -> str:
    count = usage.get(count_key)
    limit = usage.get(limit_key)
    if count is None or limit is None:
        return "n/a"
    return f"{count}/{limit}"


def main() -> int:
    try:
        api_key = get_api_key()
        usage = fetch_usage(api_key)
    except Exception as exc:
        print(f"DeepL connection failed: {exc}", file=sys.stderr)
        return 1

    print("DeepL connection successful.")
    print(f"Character usage: {format_usage('character_count', 'character_limit', usage)}")
    print(f"Document usage: {format_usage('document_count', 'document_limit', usage)}")
    return 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        raise SystemExit(exit_code)
