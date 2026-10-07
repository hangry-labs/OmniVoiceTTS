from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_LOCALES = ("nb", "pl", "ja", "zh", "es")
PRODUCT_PAGE = "https://hangrylabs.app/software/omnivoicetts"
EXAMPLE_LOCALES = (
    "en",
    "nb",
    "pl",
    "ja",
    "zh",
    "es",
    "ar",
    "bn",
    "de",
    "fr",
    "hi",
    "id",
    "it",
    "ko",
    "nl",
    "pt",
    "ru",
    "th",
    "tr",
    "ur",
    "vi",
)


def placeholders(value: str) -> set[str]:
    return set(re.findall(r"\{[a-zA-Z0-9_]+\}", value))


class LocalizationContractTests(unittest.TestCase):
    def test_readme_language_selectors_are_complete(self) -> None:
        readmes = [ROOT / "README.md", *(ROOT / f"README.{locale}.md" for locale in DOCUMENT_LOCALES)]
        expected_links = ["README.md", *(f"README.{locale}.md" for locale in DOCUMENT_LOCALES)]

        for readme in readmes:
            with self.subTest(readme=readme.name):
                text = readme.read_text(encoding="utf-8")
                for link in expected_links:
                    if link != readme.name:
                        self.assertIn(f'href="{link}"', text)
                self.assertIn("English", text)
                self.assertIn("Norsk bokmål", text)
                self.assertIn("Polski", text)
                self.assertIn("日本語", text)
                self.assertIn("简体中文", text)
                self.assertIn("Español", text)

    def test_dockerhub_language_selector_uses_absolute_github_links(self) -> None:
        text = (ROOT / "docs" / "dockerhub.md").read_text(encoding="utf-8")

        for locale in DOCUMENT_LOCALES:
            self.assertIn(
                f"https://github.com/Hangry-Labs/OmniVoiceTTS/blob/master/README.{locale}.md",
                text,
            )

        self.assertIn(PRODUCT_PAGE, text)

    def test_readmes_link_to_localized_product_and_installation_pages(self) -> None:
        self.assertIn(PRODUCT_PAGE, (ROOT / "README.md").read_text(encoding="utf-8"))

        for locale in DOCUMENT_LOCALES:
            with self.subTest(locale=locale):
                text = (ROOT / f"README.{locale}.md").read_text(encoding="utf-8")
                self.assertIn(f"https://hangrylabs.app/{locale}/software/omnivoicetts", text)

    def test_example_catalog_covers_every_selectable_language(self) -> None:
        script = (ROOT / "examples" / "i18n.js").read_text(encoding="utf-8")
        prefix = "window.EXAMPLE_I18N = "
        self.assertTrue(script.startswith(prefix))
        catalog = json.loads(script.removeprefix(prefix).strip().removesuffix(";"))
        self.assertEqual(tuple(catalog), EXAMPLE_LOCALES)

        english = catalog["en"]
        for locale, messages in catalog.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(messages), set(english))
                for key, value in messages.items():
                    self.assertEqual(placeholders(value), placeholders(english[key]), key)

    def test_examples_page_loads_localization_before_application_code(self) -> None:
        html = (ROOT / "examples" / "index.html").read_text(encoding="utf-8")
        player = (ROOT / "examples" / "player.js").read_text(encoding="utf-8")

        self.assertLess(html.index('src="i18n.js"'), html.index('src="player.js"'))
        self.assertIn('data-i18n="heading"', html)
        self.assertIn('data-i18n-aria-label="chooseLanguage"', html)
        self.assertIn("function translatePage(locale, updateUrl = false)", player)
        self.assertIn("EXAMPLE_I18N[requestedLocale] ? requestedLocale : null", player)


if __name__ == "__main__":
    unittest.main()
