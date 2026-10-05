from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
AUDIO_MODULE = ROOT / "omnivoice" / "utils" / "audio.py"


class OptionalTorchaudioTests(unittest.TestCase):
    def load_audio_module_without_torchaudio(self):
        spec = importlib.util.spec_from_file_location("optional_audio_test", AUDIO_MODULE)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        original_import_module = __import__("importlib").import_module

        def import_module(name: str, package=None):
            if name == "torchaudio":
                raise ModuleNotFoundError("blocked for optional dependency test")
            return original_import_module(name, package)

        with (
            patch.dict(os.environ, {"OMNIVOICE_RESAMPLE_BACKEND": "auto"}),
            patch("importlib.import_module", side_effect=import_module),
        ):
            spec.loader.exec_module(module)
            backend = module.get_resample_backend()
        return module, backend

    def test_import_and_resampling_fall_back_without_torchaudio(self) -> None:
        module, backend = self.load_audio_module_without_torchaudio()
        self.assertEqual(backend, "librosa")

        source = np.zeros((1, 800), dtype=np.float32)
        result = module.resample_audio(source, 8_000, 16_000)

        self.assertEqual(result.dtype, np.float32)
        self.assertEqual(result.shape, (1, 1600))

    def test_package_import_succeeds_without_torchaudio(self) -> None:
        script = textwrap.dedent(
            """
            import builtins
            import importlib.util
            import os

            os.environ["OMNIVOICE_RESAMPLE_BACKEND"] = "auto"
            original_import = builtins.__import__
            original_find_spec = importlib.util.find_spec

            def blocked_import(name, *args, **kwargs):
                if name == "torchaudio" or name.startswith("torchaudio."):
                    raise ModuleNotFoundError("torchaudio intentionally unavailable")
                return original_import(name, *args, **kwargs)

            def blocked_find_spec(name, *args, **kwargs):
                if name == "torchaudio" or name.startswith("torchaudio."):
                    return None
                return original_find_spec(name, *args, **kwargs)

            builtins.__import__ = blocked_import
            importlib.util.find_spec = blocked_find_spec

            import omnivoice
            from omnivoice.utils.audio import get_resample_backend

            assert get_resample_backend() == "librosa"
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
