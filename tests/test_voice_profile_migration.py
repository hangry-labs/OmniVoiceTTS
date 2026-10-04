from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_profiles_module():
    omnivoice_package = types.ModuleType("omnivoice")
    omnivoice_package.__path__ = []
    service_package = types.ModuleType("omnivoice.service")
    service_package.__path__ = []
    web_package = types.ModuleType("omnivoice.web")
    web_package.__path__ = []
    gradio_stub = types.ModuleType("gradio")

    paths_spec = importlib.util.spec_from_file_location(
        "omnivoice.service.paths",
        ROOT / "omnivoice" / "service" / "paths.py",
    )
    assert paths_spec and paths_spec.loader
    paths_module = importlib.util.module_from_spec(paths_spec)

    modules = {
        "omnivoice": omnivoice_package,
        "omnivoice.service": service_package,
        "omnivoice.service.paths": paths_module,
        "omnivoice.web": web_package,
        "gradio": gradio_stub,
    }
    with patch.dict(sys.modules, modules):
        paths_spec.loader.exec_module(paths_module)
        profiles_spec = importlib.util.spec_from_file_location(
            "omnivoice.web.openai_profiles",
            ROOT / "omnivoice" / "web" / "openai_profiles.py",
        )
        assert profiles_spec and profiles_spec.loader
        profiles_module = importlib.util.module_from_spec(profiles_spec)
        profiles_spec.loader.exec_module(profiles_module)
    return profiles_module


PROFILES_MODULE = load_profiles_module()


class VoiceProfileMigrationTests(unittest.TestCase):
    def test_legacy_absolute_audio_path_is_rebased_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile_dir = Path(directory)
            audio = profile_dir / "voice-example.wav"
            audio.write_bytes(b"RIFF")
            profile_index = profile_dir / "profiles.json"
            profile_index.write_text(
                json.dumps(
                    {
                        "example": {
                            "ref_audio": "/app/openai_voice_profiles/voice-example.wav",
                            "ref_text": "Example transcript.",
                            "language": "English",
                            "seed": "12345",
                            "randomize_seed": False,
                        }
                    }
                ),
                encoding="utf-8",
            )

            profiles = PROFILES_MODULE.load_openai_voice_profiles(profile_index)

            expected = str(audio.resolve())
            self.assertEqual(profiles["example"]["ref_audio"], expected)
            persisted = json.loads(profile_index.read_text(encoding="utf-8"))
            self.assertEqual(persisted["example"]["ref_audio"], expected)
            self.assertFalse(any(profile_dir.glob(".profiles.json.*.tmp")))


if __name__ == "__main__":
    unittest.main()
