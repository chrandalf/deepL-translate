import io
import json
import os
import unittest
import urllib.error
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
        self.assertEqual(
            request.get_header("Authorization"),
            "DeepL-Auth-Key abc:fx",
        )

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


if __name__ == "__main__":
    unittest.main()
