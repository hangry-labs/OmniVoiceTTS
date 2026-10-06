from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import omnivoice.app as app_module
from omnivoice.service.voice_profiles import load_openai_voice_profiles


class _FakeModel:
    sampling_rate = 24_000

    def __init__(self) -> None:
        self.prompts: list[tuple[str, str | None, bool]] = []

    def create_voice_clone_prompt(self, ref_audio, ref_text, preprocess_prompt):
        self.prompts.append((ref_audio, ref_text, preprocess_prompt))
        return object()


class SSMLApiTests(unittest.TestCase):
    def test_dynamic_voice_rejects_incompatible_accent_and_dialect(self) -> None:
        document = """<speak version="1.1"
          xmlns="http://www.w3.org/2001/10/synthesis"
          xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0" xml:lang="en-US">
          <metadata><h:extensions version="1.0">
            <h:voice-definition name="Mixed" gender="female" accent="american" dialect="cantonese"/>
          </h:extensions></metadata>
          <voice name="Mixed">This must be rejected before inference.</voice>
        </speak>"""
        with patch.object(app_module, "get_model") as get_model:
            with TestClient(app_module.api) as client:
                response = client.post(
                    "/tts/generate",
                    json={"text": document, "input_type": "ssml-h", "device": "cpu"},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot combine", response.json()["detail"])
        get_model.assert_not_called()

    def test_capabilities_and_metrics_do_not_load_a_model(self) -> None:
        with patch.object(app_module, "get_model") as get_model:
            with TestClient(app_module.api) as client:
                capabilities = client.get("/tts/ssml/capabilities")
                metrics = client.post(
                    "/tts/metrics",
                    json={
                        "text": '<speak version="1.1"><prosody rate="slow">Hello.</prosody><break time="250ms"/>World.</speak>',
                        "input_type": "ssml",
                    },
                )

        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json()["ssml_h"]["version"], "1.0")
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(metrics.json()["metrics"]["break_ms"], 250)
        get_model.assert_not_called()

    def test_standard_ssml_generate_uses_ordered_units(self) -> None:
        calls: list[dict] = []

        def synthesize(**kwargs):
            calls.append(kwargs)
            return 24_000, np.full(36_000, 1000, dtype=np.int16)

        with patch.object(app_module, "synthesize_array", side_effect=synthesize):
            with TestClient(app_module.api) as client:
                response = client.post(
                    "/tts/generate",
                    json={
                        "text": '<speak version="1.1" xml:lang="en-US">Hello.<break time="0ms"/><prosody rate="slow">World.</prosody></speak>',
                        "input_type": "ssml",
                        "device": "cpu",
                        "output_format": "wav",
                        "randomize_seed": False,
                        "seed": 42,
                    },
                )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["x-omnivoicetts-input-type"], "ssml")
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual([call["text"] for call in calls], ["Hello.", "World."])
        self.assertEqual(calls[0]["speed"], 1.0)
        self.assertEqual(calls[1]["speed"], 0.75)

    def test_ssml_h_profile_is_published_after_success_and_collision_is_safe(self) -> None:
        fake_model = _FakeModel()
        synthesis_calls: list[dict] = []

        def synthesize(**kwargs):
            synthesis_calls.append(kwargs)
            return 24_000, np.full(36_000, 1200, dtype=np.int16)

        document = """<speak version="1.1"
          xmlns="http://www.w3.org/2001/10/synthesis"
          xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0"
          xml:lang="en-US">
          <metadata><h:extensions version="1.0">
            <h:voice-definition name="Bob" gender="male" age="elderly"
              accent="american" scope="profile" seed="4242">
              <h:sample xml:lang="en-US">My name is Bob.</h:sample>
            </h:voice-definition>
          </h:extensions></metadata>
          <voice name="Bob">Are we ready?</voice>
        </speak>"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_dir = root / "profiles"
            upload_dir = root / "uploads"
            profile_index = profile_dir / "profiles.json"
            with (
                patch.object(app_module, "OPENAI_VOICE_PROFILE_DIR", profile_dir),
                patch.object(app_module, "OPENAI_VOICE_PROFILE_INDEX", profile_index),
                patch.object(app_module, "UI_UPLOAD_DIR", upload_dir),
                patch.object(app_module, "get_model", return_value=fake_model),
                patch.object(app_module, "synthesize_array", side_effect=synthesize),
            ):
                with TestClient(app_module.api) as client:
                    response = client.post(
                        "/tts/generate",
                        json={
                            "text": document,
                            "input_type": "ssml-h",
                            "device": "cpu",
                            "output_format": "wav",
                        },
                    )
                    duplicate = client.post(
                        "/tts/generate",
                        json={
                            "text": document,
                            "input_type": "ssml-h",
                            "device": "cpu",
                            "output_format": "wav",
                        },
                    )

            profiles = load_openai_voice_profiles(profile_index)
            staging_directories = list(upload_dir.glob("ssml-h-*"))

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("already exists", duplicate.json()["detail"])
        self.assertIn("bob", profiles)
        self.assertEqual(profiles["bob"]["ref_text"], "My name is Bob.")
        self.assertEqual(len(fake_model.prompts), 1)
        self.assertEqual(len(synthesis_calls), 2)
        self.assertIsNotNone(synthesis_calls[1]["voice_clone_prompt"])
        self.assertEqual(staging_directories, [])

    def test_ssml_h_profile_is_not_published_when_encoding_fails(self) -> None:
        fake_model = _FakeModel()
        document = """<speak version="1.1"
          xmlns="http://www.w3.org/2001/10/synthesis"
          xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0" xml:lang="en-US">
          <metadata><h:extensions version="1.0">
            <h:voice-definition name="Alice" gender="female" scope="profile">
              <h:sample xml:lang="en-US">My name is Alice.</h:sample>
            </h:voice-definition>
          </h:extensions></metadata>
          <voice name="Alice">This output will fail to encode.</voice>
        </speak>"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_dir = root / "profiles"
            upload_dir = root / "uploads"
            profile_index = profile_dir / "profiles.json"
            with (
                patch.object(app_module, "OPENAI_VOICE_PROFILE_DIR", profile_dir),
                patch.object(app_module, "OPENAI_VOICE_PROFILE_INDEX", profile_index),
                patch.object(app_module, "UI_UPLOAD_DIR", upload_dir),
                patch.object(app_module, "get_model", return_value=fake_model),
                patch.object(
                    app_module,
                    "synthesize_array",
                    return_value=(24_000, np.full(36_000, 1000, dtype=np.int16)),
                ),
                patch.object(app_module, "encode_audio_bytes", side_effect=RuntimeError("encoder failed")),
            ):
                with TestClient(app_module.api) as client:
                    response = client.post(
                        "/tts/generate",
                        json={
                            "text": document,
                            "input_type": "ssml-h",
                            "device": "cpu",
                            "output_format": "mp3",
                        },
                    )
            profiles = load_openai_voice_profiles(profile_index)
            staging_directories = list(upload_dir.glob("ssml-h-*"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("encoder failed", response.json()["detail"])
        self.assertEqual(profiles, {})
        self.assertEqual(staging_directories, [])


if __name__ == "__main__":
    unittest.main()
