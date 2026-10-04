from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


PATHS_PATH = Path(__file__).resolve().parents[1] / "omnivoice" / "service" / "paths.py"
PATHS_SPEC = importlib.util.spec_from_file_location("omnivoice_service_paths_test", PATHS_PATH)
assert PATHS_SPEC and PATHS_SPEC.loader
PATHS_MODULE = importlib.util.module_from_spec(PATHS_SPEC)
PATHS_SPEC.loader.exec_module(PATHS_MODULE)
safe_existing_file_path = PATHS_MODULE.safe_existing_file_path


class SafeExistingFilePathTests(unittest.TestCase):
    def test_accepts_existing_file_inside_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "voice.wav"
            audio.write_bytes(b"RIFF")

            resolved = safe_existing_file_path(
                audio,
                [root],
                allowed_extensions={".wav"},
            )

            self.assertEqual(resolved, audio.resolve())

    def test_rejects_missing_file_inside_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "existing file"):
                safe_existing_file_path(root / "missing.wav", [root])

    def test_rejects_existing_file_outside_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            allowed = base / "allowed"
            allowed.mkdir()
            outside = base / "outside.wav"
            outside.write_bytes(b"RIFF")

            with self.assertRaisesRegex(ValueError, "inside one of these safe roots"):
                safe_existing_file_path(outside, [allowed])


if __name__ == "__main__":
    unittest.main()
