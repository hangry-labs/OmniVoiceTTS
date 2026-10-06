from __future__ import annotations

import unittest

from omnivoice.utils.text_normalization import normalize_structured_text


class StructuredTextNormalizationTests(unittest.TestCase):
    def test_issue_246_structured_english_is_verbalized(self) -> None:
        result = normalize_structured_text(
            "Email john.smith@example.com, call +1 555 123 4567, pay $19.99 on 2026-08-12, "
            "use code AB12-C, visit https://example.com/help, score 98.5% and count 42.",
            "English",
        )

        self.assertTrue(result.supported)
        self.assertIn("john dot smith at example dot com", result.normalized)
        self.assertIn("plus one five five five one two three four five six seven", result.normalized)
        self.assertIn("nineteen dollars and ninety nine cents", result.normalized)
        self.assertIn("August twelfth twenty twenty six", result.normalized)
        self.assertIn("A B one two dash C", result.normalized)
        self.assertIn("H T T P S colon slash slash example dot com slash help", result.normalized)
        self.assertIn("ninety eight point five percent", result.normalized)
        self.assertIn("forty two", result.normalized)
        self.assertEqual(
            [change.kind for change in result.changes],
            ["email", "phone", "currency", "date", "identifier", "url", "percentage", "integer"],
        )

    def test_control_syntax_and_ambiguous_values_are_preserved(self) -> None:
        text = "Read [R AE1 D], laugh [laughter], date 08/12/2026, IP 192.168.1.5, version v1.2.3."
        result = normalize_structured_text(text, "en-US")

        self.assertEqual(result.normalized, text)
        self.assertEqual(len(result.warnings), 2)

    def test_unsupported_or_ambiguous_auto_language_is_unchanged(self) -> None:
        polish = "Mam 42 wiadomości."
        explicit = normalize_structured_text(polish, "Polish")
        automatic = normalize_structured_text(polish)

        self.assertFalse(explicit.supported)
        self.assertFalse(automatic.supported)
        self.assertEqual(explicit.normalized, polish)
        self.assertEqual(automatic.normalized, polish)

    def test_ascii_auto_detection_and_change_serialization(self) -> None:
        result = normalize_structured_text("There are 12 items.")

        self.assertEqual(result.language, "en")
        self.assertEqual(result.normalized, "There are twelve items.")
        self.assertEqual(result.model_dump()["changes"][0]["kind"], "integer")

    def test_english_curly_punctuation_does_not_disable_auto_detection(self) -> None:
        result = normalize_structured_text("It’s item 12.")

        self.assertTrue(result.supported)
        self.assertEqual(result.normalized, "It’s item twelve.")


if __name__ == "__main__":
    unittest.main()
