import io
import json
import os
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import src.connect_deepl as connect_deepl


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ConnectDeepLTests(unittest.TestCase):
    def test_get_api_key_reads_env(self):
        with patch.dict(os.environ, {"DEEPL_API_KEY": "test-key:fx"}, clear=False):
            self.assertEqual(connect_deepl.get_api_key(), "test-key:fx")

    def test_get_api_key_raises_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                connect_deepl.get_api_key()

    def test_build_usage_request_uses_header_auth(self):
        request = connect_deepl.build_usage_request("abc:fx")
        self.assertEqual(request.full_url, connect_deepl.USAGE_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, b"")
        self.assertEqual(request.get_header("Authorization"), "DeepL-Auth-Key abc:fx")

    def test_build_translate_request_uses_header_and_body(self):
        request = connect_deepl.build_translate_request("abc:fx", "Hi", target_lang="DE")
        self.assertEqual(request.full_url, connect_deepl.TRANSLATE_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "DeepL-Auth-Key abc:fx")
        self.assertIn(b"text=Hi", request.data)
        self.assertIn(b"target_lang=DE", request.data)

    def test_fetch_usage_success(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse({"character_count": 1})):
            payload = connect_deepl.fetch_usage("abc:fx")
        self.assertEqual(payload["character_count"], 1)

    def test_fetch_usage_http_error(self):
        error = urllib.error.HTTPError(
            url=connect_deepl.USAGE_URL,
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"Auth failed"}'),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(RuntimeError):
                connect_deepl.fetch_usage("bad")

    def test_translate_text_success(self):
        with patch(
            "urllib.request.urlopen",
            return_value=FakeResponse({"translations": [{"text": "Hallo"}]}),
        ):
            translated = connect_deepl.translate_text("abc:fx", "Hello")
        self.assertEqual(translated, "Hallo")

    def test_translate_text_missing_translations(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse({"translations": []})):
            with self.assertRaises(RuntimeError):
                connect_deepl.translate_text("abc:fx", "Hello")

    def test_format_usage_returns_na_when_usage_keys_missing(self):
        self.assertEqual(connect_deepl.format_usage("document_count", "document_limit", {}), "n/a")


    def test_parse_args_ignores_unknown_args(self):
        args = connect_deepl.parse_args(["--translate-text", "Hello", "-f", "kernel.json"])
        self.assertEqual(args.translate_text, "Hello")

    def test_main_usage_mode(self):
        stdout_buffer = io.StringIO()
        with patch.dict(os.environ, {"DEEPL_API_KEY": "ok:fx"}, clear=False), patch(
            "src.connect_deepl.fetch_usage",
            return_value={"character_count": 0, "character_limit": 500000},
        ), redirect_stdout(stdout_buffer):
            exit_code = connect_deepl.main([])

        self.assertEqual(exit_code, 0)
        output = stdout_buffer.getvalue()
        self.assertIn("DeepL connection successful.", output)
        self.assertIn("Character usage: 0/500000", output)
        self.assertIn("Document usage: n/a", output)

    def test_main_translate_requires_allow_flag(self):
        stderr_buffer = io.StringIO()
        with patch.dict(os.environ, {"DEEPL_API_KEY": "ok:fx"}, clear=False), redirect_stderr(stderr_buffer):
            exit_code = connect_deepl.main(["--translate-text", "Hello"])  # no allow flag
        self.assertEqual(exit_code, 1)
        self.assertIn("Translation blocked", stderr_buffer.getvalue())

    def test_main_translate_respects_char_limit(self):
        stderr_buffer = io.StringIO()
        with patch.dict(os.environ, {"DEEPL_API_KEY": "ok:fx"}, clear=False), redirect_stderr(stderr_buffer):
            exit_code = connect_deepl.main(
                [
                    "--translate-text",
                    "abcdef",
                    "--allow-translate",
                    "--max-chars",
                    "5",
                ]
            )
        self.assertEqual(exit_code, 1)
        self.assertIn("exceeds --max-chars=5", stderr_buffer.getvalue())

    def test_main_translate_success(self):
        stdout_buffer = io.StringIO()
        with patch.dict(os.environ, {"DEEPL_API_KEY": "ok:fx"}, clear=False), patch(
            "src.connect_deepl.translate_text",
            return_value="Hallo Welt",
        ), redirect_stdout(stdout_buffer):
            exit_code = connect_deepl.main(
                [
                    "--translate-text",
                    "Hello world",
                    "--allow-translate",
                    "--max-chars",
                    "50",
                ]
            )

        self.assertEqual(exit_code, 0)
        output = stdout_buffer.getvalue()
        self.assertIn("DeepL translation successful.", output)
        self.assertIn("Source chars sent: 11", output)
        self.assertIn("Target (DE): Hallo Welt", output)


if __name__ == "__main__":
    unittest.main()
