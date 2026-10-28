from __future__ import annotations

import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import torch
from fastapi.testclient import TestClient

import omnivoice.app as app_module
from omnivoice.models.omnivoice import OmniVoice


class VoiceCloneInferenceTests(unittest.TestCase):
    def make_model(self) -> tuple[OmniVoice, Mock]:
        weight = torch.tensor(2.0, requires_grad=True)

        def encode(waveform: torch.Tensor) -> SimpleNamespace:
            self.assertTrue(torch.is_inference_mode_enabled())
            self.assertFalse(torch.is_grad_enabled())
            activation = waveform * weight
            self.assertFalse(activation.requires_grad)
            self.assertIsNone(activation.grad_fn)
            return SimpleNamespace(
                audio_codes=torch.zeros(
                    (1, 8, waveform.shape[-1] // 128), dtype=torch.long
                )
            )

        encoder = Mock(side_effect=encode)
        model = OmniVoice.__new__(OmniVoice)
        model.audio_tokenizer = SimpleNamespace(
            device=torch.device("cpu"),
            config=SimpleNamespace(hop_length=128),
            encode=encoder,
        )
        model.sampling_rate = 24_000
        model._asr_pipe = None
        model.load_asr_model = Mock()

        def transcribe(_audio) -> str:
            self.assertTrue(torch.is_inference_mode_enabled())
            self.assertFalse(torch.is_grad_enabled())
            return "A complete reference transcript."

        model.transcribe = Mock(side_effect=transcribe)
        return model, encoder

    def test_direct_prompt_disables_gradients_and_preserves_transcript_and_audio(self) -> None:
        for preprocess in (False, True):
            for transcript in (None, "A complete reference transcript."):
                with self.subTest(preprocess=preprocess, transcript=transcript):
                    model, encoder = self.make_model()
                    audio = np.full((1, 96_000), 0.25, dtype=np.float32)
                    original = audio.copy()
                    with torch.enable_grad():
                        prompt = model.create_voice_clone_prompt(
                            (audio, 24_000), transcript, preprocess
                        )
                        self.assertTrue(torch.is_grad_enabled())
                        self.assertFalse(torch.is_inference_mode_enabled())
                    self.assertEqual(prompt.ref_text, "A complete reference transcript.")
                    self.assertEqual(prompt.ref_rms, 0.25)
                    self.assertEqual(prompt.ref_audio_tokens.dtype, torch.long)
                    self.assertTrue(torch.is_inference(prompt.ref_audio_tokens))
                    np.testing.assert_array_equal(audio, original)
                    encoder.assert_called_once()
                    self.assertEqual(model.transcribe.call_count, int(transcript is None))
                    self.assertEqual(model.load_asr_model.call_count, int(transcript is None))

    def test_inference_guard_restores_caller_state_after_failure(self) -> None:
        model, encoder = self.make_model()

        def fail(_waveform):
            self.assertTrue(torch.is_inference_mode_enabled())
            self.assertFalse(torch.is_grad_enabled())
            raise RuntimeError("Tokenizer failed")

        encoder.side_effect = fail
        with torch.enable_grad():
            with self.assertRaisesRegex(RuntimeError, "Tokenizer failed"):
                model.create_voice_clone_prompt(
                    (np.full((1, 256), 0.25, dtype=np.float32), 24_000),
                    "Reference.",
                    preprocess_prompt=False,
                )
            self.assertTrue(torch.is_grad_enabled())
            self.assertFalse(torch.is_inference_mode_enabled())

    def test_cached_prompt_is_encoded_once_and_reusable_in_inference(self) -> None:
        model, encoder = self.make_model()
        with (
            patch.object(app_module, "VOICE_CLONE_PROMPT_CACHE", OrderedDict()),
            patch(
                "omnivoice.models.omnivoice.load_audio",
                return_value=np.full((1, 96_000), 0.25, dtype=np.float32),
            ),
            torch.enable_grad(),
        ):
            prompts = [
                app_module.get_cached_voice_clone_prompt(
                    model,
                    "cpu",
                    str(app_module.OPENAI_DEFAULT_CLONE_AUDIO),
                    "A complete reference transcript.",
                    True,
                    cache_enabled=True,
                )
                for _ in range(2)
            ]
            self.assertIsNotNone(prompts[0])
            self.assertIs(prompts[0], prompts[1])
            self.assertTrue(torch.is_grad_enabled())
            self.assertFalse(torch.is_inference_mode_enabled())
            self.assertEqual(len(app_module.VOICE_CLONE_PROMPT_CACHE), 1)
        encoder.assert_called_once()
        with torch.inference_mode():
            tokens = prompts[0].ref_audio_tokens
            combined = torch.cat([tokens, tokens], dim=-1)
            self.assertTrue(torch.equal(combined[:, :tokens.shape[-1]], tokens))

    def test_ssml_h_dynamic_voice_preparation_uses_inference_guard(self) -> None:
        model, encoder = self.make_model()
        calls: list[dict] = []

        def synthesize(**kwargs):
            calls.append(kwargs)
            return 24_000, np.full(96_000, 1200, dtype=np.int16)

        document = """<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0" xml:lang="en-US">
          <metadata><h:extensions version="1.0">
            <h:voice-definition name="InferenceTest" gender="female" scope="request" seed="4242"/>
          </h:extensions></metadata>
          <voice name="InferenceTest">We are ready for this test.</voice>
        </speak>"""
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(app_module, "UI_UPLOAD_DIR", Path(directory)),
                patch.object(app_module, "get_model", return_value=model),
                patch.object(app_module, "synthesize_array", side_effect=synthesize),
                TestClient(app_module.api) as client,
            ):
                response = client.post(
                    "/tts/generate",
                    json={
                        "text": document,
                        "input_type": "ssml-h",
                        "device": "cpu",
                        "output_format": "wav",
                    },
                )
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(response.status_code, 200, response.text)
        encoder.assert_called_once()
        model.transcribe.assert_not_called()
        self.assertEqual(len(calls), 2)
        self.assertTrue(torch.is_inference(calls[1]["voice_clone_prompt"].ref_audio_tokens))


if __name__ == "__main__":
    unittest.main()
