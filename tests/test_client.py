from __future__ import annotations

import unittest
from unittest.mock import patch

from omnivoice.client import OmniVoiceTTSClient


class OmniVoiceTTSClientTests(unittest.TestCase):
    def test_structured_text_helpers_send_explicit_payloads(self) -> None:
        client = OmniVoiceTTSClient()
        with patch.object(client, "_json", return_value={"normalized": "Item twelve."}) as request:
            response = client.normalize_text("Item 12.", "English")

        self.assertEqual(response["normalized"], "Item twelve.")
        request.assert_called_once_with(
            "POST",
            "/tts/text/normalize",
            {"text": "Item 12.", "language": "English"},
        )

    def test_generate_forwards_normalization_flag(self) -> None:
        client = OmniVoiceTTSClient()
        with patch.object(client, "_audio") as request:
            client.generate("Item 12.", normalize_text=True)

        self.assertTrue(request.call_args.args[1]["normalize_text"])

    def test_generate_forwards_output_mastering_controls(self) -> None:
        client = OmniVoiceTTSClient()
        with patch.object(client, "_audio") as request:
            client.generate(
                "Hello.",
                float_preserving_silence=False,
                output_keep_silence_ms=240,
                output_preserve_active_edges=True,
                output_peak_limit=0.8,
            )

        payload = request.call_args.args[1]
        self.assertFalse(payload["float_preserving_silence"])
        self.assertEqual(payload["output_keep_silence_ms"], 240)
        self.assertTrue(payload["output_preserve_active_edges"])
        self.assertEqual(payload["output_peak_limit"], 0.8)


if __name__ == "__main__":
    unittest.main()
