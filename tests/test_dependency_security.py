from __future__ import annotations

import unittest
from unittest.mock import patch

from starlette.requests import Request
from transformers.generation.utils import GenerationMixin


class DependencySecurityTests(unittest.TestCase):
    def test_declining_custom_generation_code_prevents_download(self) -> None:
        with (
            patch("transformers.generation.utils.has_file", return_value=True),
            patch("transformers.generation.utils.get_cached_module_file") as download,
            patch("transformers.generation.utils.get_class_in_module") as load_code,
        ):
            with self.assertRaises(ValueError):
                GenerationMixin.load_custom_generate(
                    object(), "untrusted/custom-generation", trust_remote_code=False
                )

        download.assert_not_called()
        load_code.assert_not_called()

    def test_malformed_host_cannot_replace_the_request_url_path(self) -> None:
        for host in (b"testserver/mcp/?path=", b"testserver#fragment", b"testserver?query="):
            with self.subTest(host=host):
                request = Request(
                    {
                        "type": "http",
                        "scheme": "http",
                        "server": ("testserver", 80),
                        "path": "/mcp/advanced/",
                        "query_string": b"",
                        "headers": [(b"host", host)],
                    }
                )
                self.assertEqual(request.url.path, "/mcp/advanced/")
                self.assertEqual(request.url.hostname, "testserver")


if __name__ == "__main__":
    unittest.main()
