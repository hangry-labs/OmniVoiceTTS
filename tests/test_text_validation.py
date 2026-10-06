from __future__ import annotations

import unittest

from pydantic import ValidationError

from omnivoice.service.schemas import OpenAISpeechRequest, TTSRequest
from omnivoice.cli.infer import get_parser as get_infer_parser
from omnivoice.cli.infer_batch import get_parser as get_batch_parser
from omnivoice.utils.text import (
    normalize_terminal_punctuation_spacing,
    validate_synthesis_text,
    validate_synthesis_texts,
)


class SynthesisTextValidationTests(unittest.TestCase):
    def test_accepts_multilingual_text_and_supported_control_syntax(self) -> None:
        accepted = (
            "Hello world.",
            "Zażółć gęślą jaźń.",
            "你好。",
            "مرحبا",
            "[laughter]",
            "Read this as [R AE1 D].",
            "12345",
        )

        for text in accepted:
            with self.subTest(text=text):
                self.assertEqual(validate_synthesis_text(text), text)

    def test_rejects_empty_and_symbol_only_text(self) -> None:
        rejected = ("", "   ", "_____", "...?!", "😀")

        for text in rejected:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    validate_synthesis_text(text)

    def test_batch_error_identifies_the_bad_item(self) -> None:
        with self.assertRaisesRegex(ValueError, "symbol-only"):
            validate_synthesis_texts(["Valid text", "____"])

    def test_native_and_openai_requests_reject_symbol_only_text(self) -> None:
        with self.assertRaises(ValidationError):
            TTSRequest(text="____")
        with self.assertRaises(ValidationError):
            OpenAISpeechRequest(input="____")

    def test_structured_normalization_is_plain_text_only(self) -> None:
        with self.assertRaisesRegex(ValidationError, "plain-text|input_type='text'"):
            TTSRequest(
                text='<speak version="1.1">Item 12.</speak>',
                input_type="ssml",
                normalize_text=True,
            )

        self.assertTrue(TTSRequest(text="Item 12.", normalize_text=True).normalize_text)

    def test_inference_clis_expose_opt_in_normalization(self) -> None:
        single = get_infer_parser().parse_args(
            ["--text", "Item 12.", "--output", "out.wav", "--normalize_text", "true"]
        )
        batch = get_batch_parser().parse_args(
            ["--test_list", "items.jsonl", "--res_dir", "results", "--normalize_text", "true"]
        )

        self.assertTrue(single.normalize_text)
        self.assertTrue(batch.normalize_text)

    def test_spaces_attached_terminal_question_and_exclamation_marks(self) -> None:
        cases = {
            "Jesteśmy gotowi do ofiary?": "Jesteśmy gotowi do ofiary ?",
            "Jesteśmy gotowi do ofiary!": "Jesteśmy gotowi do ofiary !",
            "Really?!": "Really ?!",
            "First! Second?": "First ! Second ?",
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_terminal_punctuation_spacing(raw), expected)

    def test_terminal_punctuation_spacing_is_conservative_and_idempotent(self) -> None:
        unchanged = (
            "Already spaced !",
            "你好？",
            "你好?",
            "https://example.test/?query=value",
            "Read this as [R AE1 D].",
        )

        for text in unchanged:
            with self.subTest(text=text):
                normalized = normalize_terminal_punctuation_spacing(text)
                self.assertEqual(normalized, text)
                self.assertEqual(normalize_terminal_punctuation_spacing(normalized), text)


if __name__ == "__main__":
    unittest.main()
