from __future__ import annotations

import unittest

from omnivoice.utils.malayalam_normalization import number_to_malayalam
from omnivoice.utils.text_normalization import normalize_structured_text
from omnivoice.utils.vietnamese_normalization import number_to_vietnamese


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

    def test_issue_161_malayalam_structured_values_are_verbalized(self) -> None:
        text = "എനിക്ക് ₹250 ഉണ്ട്, സമയം 5:30 ആയി. AICTE മോഡൽ 10.5 സ്കോർ നേടി."
        result = normalize_structured_text(text, "Malayalam")

        self.assertTrue(result.supported)
        self.assertEqual(result.language, "ml")
        self.assertEqual(
            result.normalized,
            "എനിക്ക് ഇരുനൂറ്റി അമ്പത് രൂപ ഉണ്ട്, സമയം അഞ്ച് മുപ്പത് ആയി. "
            "എ ഐ സി ടി ഇ മോഡൽ പത്ത് പോയിന്റ് അഞ്ച് സ്കോർ നേടി.",
        )
        self.assertEqual(
            [change.kind for change in result.changes],
            ["currency", "time", "acronym", "decimal"],
        )
        for change in result.changes:
            self.assertEqual(text[change.start : change.end], change.original)

    def test_malayalam_script_is_safely_auto_detected(self) -> None:
        result = normalize_structured_text("ഇതിന് 10km ദൂരമുണ്ട്.")

        self.assertTrue(result.supported)
        self.assertEqual(result.language, "ml")
        self.assertEqual(result.normalized, "ഇതിന് പത്ത് കിലോമീറ്റർ ദൂരമുണ്ട്.")

    def test_malayalam_numbers_fractions_ordinals_and_currency_forms(self) -> None:
        result = normalize_structured_text(
            "₹1,00,000, 98.5%, 1 1/2, 1st, $100, 50 £, 0484.",
            "ml-IN",
        )

        self.assertEqual(
            result.normalized,
            "ഒരു ലക്ഷം രൂപ, തൊണ്ണൂറ്റി എട്ട് പോയിന്റ് അഞ്ച് ശതമാനം, "
            "ഒന്ന് അര, ഒന്നാമത്തെ, നൂറ് ഡോളർ, അമ്പത് പൗണ്ട്, "
            "പൂജ്യം നാല് എട്ട് നാല്.",
        )

    def test_malayalam_controls_and_ambiguous_values_are_preserved(self) -> None:
        text = "പറയുക [R AE1 D], 25:99, 2/3, 2026-10-06, v1.2.3, വില 42."
        result = normalize_structured_text(text, "ml")

        self.assertEqual(
            result.normalized,
            "പറയുക [R AE1 D], 25:99, 2/3, 2026-10-06, v1.2.3, വില നാല്പത്തി രണ്ട്.",
        )
        self.assertEqual(len(result.changes), 1)
        self.assertIn("Invalid time-like values were preserved.", result.warnings)
        self.assertIn("Unsupported fraction forms were preserved.", result.warnings)
        self.assertIn(
            "ISO dates were preserved because Malayalam date verbalization is not supported yet.",
            result.warnings,
        )

    def test_malformed_malayalam_number_grouping_is_not_partially_rewritten(self) -> None:
        text = "തെറ്റായ സംഖ്യ 1,2,3 അതേപടി വേണം."
        result = normalize_structured_text(text, "ml")

        self.assertEqual(result.normalized, text)
        self.assertEqual(result.changes, ())

    def test_malayalam_number_vocabulary_matches_contributed_cases(self) -> None:
        cases = {
            0: "പൂജ്യം",
            1: "ഒന്ന്",
            9: "ഒമ്പത്",
            10: "പത്ത്",
            15: "പതിനഞ്ച്",
            21: "ഇരുപത്തി ഒന്ന്",
            99: "തൊണ്ണൂറ്റി ഒമ്പത്",
            100: "നൂറ്",
            250: "ഇരുനൂറ്റി അമ്പത്",
            900: "തൊള്ളായിരം",
            999: "തൊള്ളായിരത്തി തൊണ്ണൂറ്റി ഒമ്പത്",
            1000: "ആയിരം",
            2500: "രണ്ടായിരത്തി അഞ്ഞൂറ്",
            9999: "ഒമ്പതിനായിരത്തി തൊള്ളായിരത്തി തൊണ്ണൂറ്റി ഒമ്പത്",
            100_000: "ഒരു ലക്ഷം",
            150_000: "ഒരു ലക്ഷത്തി അമ്പത് ആയിരം",
            500_000: "അഞ്ച് ലക്ഷം",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(number_to_malayalam(value), expected)
        self.assertIsNone(number_to_malayalam(-1))
        self.assertIsNone(number_to_malayalam(10_000_000))

    def test_malayalam_remaining_transformation_classes(self) -> None:
        cases = {
            "5%": "അഞ്ച് ശതമാനം",
            "30cm": "മുപ്പത് സെന്റീമീറ്റർ",
            "500ml": "അഞ്ഞൂറ് മില്ലിലിറ്റർ",
            "10:00": "പത്ത് മണി",
            "12:45": "പന്ത്രണ്ട് നാല്പത്തി അഞ്ച്",
            "1/4": "കാൽ",
            "3/4": "മുക്കാൽ",
            "WHO": "ഡബ്ല്യൂ എച്ച് ഒ",
            "9876543210": "ഒമ്പത് എട്ട് ഏഴ് ആറ് അഞ്ച് നാല് മൂന്ന് രണ്ട് ഒന്ന് പൂജ്യം",
        }

        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_structured_text(source, "ml").normalized, expected)

    def test_issue_238_vietnamese_structured_values_are_verbalized(self) -> None:
        text = (
            "Tôi có 25 quyển sách, giá 250.000đ, giảm 12,5%, "
            "nặng 2kg lúc 08:30 ngày 2026-07-29."
        )
        result = normalize_structured_text(text, "Vietnamese")

        self.assertTrue(result.supported)
        self.assertEqual(result.language, "vi")
        self.assertEqual(
            result.normalized,
            "Tôi có hai mươi lăm quyển sách, giá hai trăm năm mươi nghìn đồng, "
            "giảm mười hai phẩy năm phần trăm, nặng hai ki lô gam lúc "
            "tám giờ ba mươi phút ngày hai mươi chín tháng bảy năm "
            "hai nghìn không trăm hai mươi sáu.",
        )
        self.assertEqual(
            [change.kind for change in result.changes],
            ["integer", "currency", "percentage", "unit", "time", "date"],
        )
        for change in result.changes:
            self.assertEqual(text[change.start : change.end], change.original)

    def test_vietnamese_number_vocabulary_matches_contributed_rules(self) -> None:
        cases = {
            0: "không",
            1: "một",
            10: "mười",
            15: "mười lăm",
            21: "hai mươi mốt",
            24: "hai mươi tư",
            25: "hai mươi lăm",
            101: "một trăm linh một",
            105: "một trăm linh năm",
            1_000: "một nghìn",
            1_005: "một nghìn không trăm linh năm",
            1_234: "một nghìn hai trăm ba mươi tư",
            1_000_000: "một triệu",
            -42: "âm bốn mươi hai",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(number_to_vietnamese(value), expected)
        with self.assertRaises(ValueError):
            number_to_vietnamese("1234567890123456789")

    def test_vietnamese_currency_units_decimals_and_seconds(self) -> None:
        result = normalize_structured_text(
            "Giá $19.99, 2 triệu VND, 1.234,56 EUR; nhiệt độ 25°C lúc 23:59:08.",
            "vi-VN",
        )

        self.assertEqual(
            result.normalized,
            "Giá mười chín phẩy chín chín đô la Mỹ, hai triệu đồng, "
            "một nghìn hai trăm ba mươi tư phẩy năm sáu euro; nhiệt độ "
            "hai mươi lăm độ xê lúc hai mươi ba giờ năm mươi chín phút tám giây.",
        )
        self.assertEqual(
            [change.kind for change in result.changes],
            ["currency", "currency", "currency", "unit", "time"],
        )

    def test_vietnamese_ambiguous_identifiers_and_malformed_values_are_preserved(self) -> None:
        text = (
            "Giữ 1.234, 1,234, mã 007, phòng 105, 1/2, 08/12/2026, 25:70, "
            "1,2,3, 090 123 4567, IP 192.168.1.5 và v1.2.3."
        )
        result = normalize_structured_text(text, "vi")

        self.assertEqual(result.normalized, text)
        self.assertEqual(result.changes, ())
        self.assertIn("Invalid time-like values were preserved.", result.warnings)
        self.assertTrue(
            any("dotted values" in warning for warning in result.warnings),
            result.warnings,
        )
        self.assertTrue(
            any("identifiers" in warning for warning in result.warnings),
            result.warnings,
        )
        self.assertTrue(
            any("numeric punctuation" in warning for warning in result.warnings),
            result.warnings,
        )

    def test_vietnamese_invalid_iso_date_is_not_partially_rewritten(self) -> None:
        text = "Ngày 2026-02-30 không hợp lệ, nhưng ngày 2024-02-29 hợp lệ."
        result = normalize_structured_text(text, "vi")

        self.assertEqual(
            result.normalized,
            "Ngày 2026-02-30 không hợp lệ, nhưng ngày hai mươi chín tháng hai "
            "năm hai nghìn không trăm hai mươi tư hợp lệ.",
        )
        self.assertIn("Invalid ISO dates were preserved.", result.warnings)


if __name__ == "__main__":
    unittest.main()
