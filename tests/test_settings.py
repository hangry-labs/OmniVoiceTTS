from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SETTINGS_PATH = Path(__file__).resolve().parents[1] / "omnivoice" / "settings.py"
SETTINGS_SPEC = importlib.util.spec_from_file_location("omnivoice_runtime_settings", SETTINGS_PATH)
assert SETTINGS_SPEC and SETTINGS_SPEC.loader
SETTINGS_MODULE = importlib.util.module_from_spec(SETTINGS_SPEC)
SETTINGS_SPEC.loader.exec_module(SETTINGS_MODULE)
DEFAULT_SETTINGS_PATH = SETTINGS_MODULE.DEFAULT_SETTINGS_PATH
RuntimeSettingsStore = SETTINGS_MODULE.RuntimeSettingsStore


class RuntimeSettingsStoreTests(unittest.TestCase):
    def test_default_path_uses_unified_persistent_volume(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(RuntimeSettingsStore().path, Path(DEFAULT_SETTINGS_PATH))
        self.assertEqual(DEFAULT_SETTINGS_PATH, "/app/persistent/app/settings.json")

    def test_environment_path_overrides_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.json"
            with patch.dict("os.environ", {"OMNIVOICE_SETTINGS_PATH": str(path)}):
                self.assertEqual(RuntimeSettingsStore().path, path)

    def test_values_are_persisted_atomically_and_preserve_existing_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"existing": 42}\n', encoding="utf-8")
            store = RuntimeSettingsStore(path)

            store.set("future_ui_preference", True)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload, {"existing": 42, "future_ui_preference": True})
            self.assertTrue(RuntimeSettingsStore(path).get("future_ui_preference"))
            self.assertFalse(any(path.parent.glob(".settings.json.*.tmp")))

    def test_missing_or_invalid_settings_fall_back_to_empty_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = RuntimeSettingsStore(path)
            self.assertEqual(store.snapshot(), {})

            path.write_text("not-json", encoding="utf-8")
            self.assertEqual(store.snapshot(), {})

            path.write_text("[]", encoding="utf-8")
            self.assertEqual(store.snapshot(), {})

    def test_empty_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                store.set("", True)


if __name__ == "__main__":
    unittest.main()
