from __future__ import annotations

import unittest

from omnivoice.utils.lang_map import LANG_NAMES, LANG_NAME_ALIASES, LANG_NAME_TO_ID


class LanguageMapTests(unittest.TestCase):
    def test_punjabi_names_are_canonical_and_legacy_spellings_remain_aliases(self) -> None:
        self.assertEqual(LANG_NAME_TO_ID["punjabi"], "pa")
        self.assertEqual(LANG_NAME_TO_ID["panjabi"], "pa")
        self.assertEqual(LANG_NAME_TO_ID["western punjabi"], "pnb")
        self.assertEqual(LANG_NAME_TO_ID["western panjabi"], "pnb")
        self.assertEqual(LANG_NAME_ALIASES["panjabi"], "punjabi")
        self.assertEqual(
            LANG_NAME_ALIASES["western panjabi"],
            "western punjabi",
        )

        self.assertIn("punjabi", LANG_NAMES)
        self.assertIn("western punjabi", LANG_NAMES)
        self.assertNotIn("panjabi", LANG_NAMES)
        self.assertNotIn("western panjabi", LANG_NAMES)


if __name__ == "__main__":
    unittest.main()
