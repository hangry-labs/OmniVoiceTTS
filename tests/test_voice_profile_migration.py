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
    }
    with patch.dict(sys.modules, modules):
        paths_spec.loader.exec_module(paths_module)
        profiles_spec = importlib.util.spec_from_file_location(
            "omnivoice.service.voice_profiles",
            ROOT / "omnivoice" / "service" / "voice_profiles.py",
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
            self.assertEqual(profiles["example"]["description"], "")
            self.assertEqual(profiles["example"]["profile_type"], "cloned")
            self.assertFalse(any(profile_dir.glob(".profiles.json.*.tmp")))

    def test_replacing_profile_removes_only_previous_copied_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile_dir = Path(directory) / "profiles"
            source_dir = Path(directory) / "uploads"
            source_dir.mkdir()
            first_source = source_dir / "first.wav"
            second_source = source_dir / "second.wav"
            first_source.write_bytes(b"RIFF-first")
            second_source.write_bytes(b"RIFF-second")
            profile_index = profile_dir / "profiles.json"

            PROFILES_MODULE.save_openai_voice_profile(
                profile_dir,
                profile_index,
                2**32 - 1,
                "Example Voice",
                str(first_source),
                [source_dir],
                "First transcript.",
                "English",
                12345,
                False,
            )
            first_copy = Path(PROFILES_MODULE.load_openai_voice_profiles(profile_index)["example-voice"]["ref_audio"])

            PROFILES_MODULE.save_openai_voice_profile(
                profile_dir,
                profile_index,
                2**32 - 1,
                "Example Voice",
                str(second_source),
                [source_dir],
                "Second transcript.",
                "English",
                54321,
                False,
                "Clear product narrator.",
                "designed",
            )
            replaced = PROFILES_MODULE.load_openai_voice_profiles(profile_index)["example-voice"]
            second_copy = Path(replaced["ref_audio"])

            self.assertFalse(first_copy.exists())
            self.assertTrue(second_copy.exists())
            self.assertEqual(second_copy.read_bytes(), b"RIFF-second")
            self.assertEqual(replaced["ref_text"], "Second transcript.")
            self.assertEqual(replaced["description"], "Clear product narrator.")
            self.assertEqual(replaced["profile_type"], "designed")
            self.assertTrue(first_source.exists())
            self.assertTrue(second_source.exists())


if __name__ == "__main__":
    unittest.main()
