from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np
import torch

from omnivoice.models.omnivoice import (
    OmniVoice,
    OmniVoiceGenerationConfig,
    _duration_to_target_tokens,
    _normalize_duration_values,
)
from omnivoice.utils.audio import (
    analyze_reference_audio,
    edge_silence_durations,
    ensure_reference_edge_silence,
    limit_audio_peak,
    remove_silence,
)


class AudioQualityControlTests(unittest.TestCase):
    def test_clone_prompt_repairs_edges_before_tokenizer_alignment(self) -> None:
        captured: dict[str, torch.Tensor] = {}

        class _Tokenizer:
            device = torch.device("cpu")
            config = SimpleNamespace(hop_length=128)

            @staticmethod
            def encode(waveform: torch.Tensor) -> SimpleNamespace:
                captured["waveform"] = waveform.detach().clone()
                token_count = waveform.shape[-1] // 128
                return SimpleNamespace(
                    audio_codes=torch.zeros((1, 8, token_count), dtype=torch.long)
                )

        model = OmniVoice.__new__(OmniVoice)
        model.audio_tokenizer = _Tokenizer()
        model.sampling_rate = 1000
        model._asr_pipe = None
        audio = np.full((1, 4_000), 0.25, dtype=np.float32)

        prompt = model.create_voice_clone_prompt(
            (audio, 1000),
            "A complete reference transcript.",
            preprocess_prompt=True,
        )

        tokenized = captured["waveform"].squeeze(0).numpy()
        self.assertEqual(tokenized.shape[-1] % 128, 0)
        leading_ms, trailing_ms = edge_silence_durations(tokenized, 1000)
        self.assertGreaterEqual(leading_ms, 100)
        self.assertGreaterEqual(trailing_ms, 200)
        self.assertEqual(prompt.ref_text, "A complete reference transcript.")

    def test_clone_reference_edge_padding_preserves_original_samples(self) -> None:
        audio = np.full((1, 500), 0.25, dtype=np.float32)

        padded, added_leading_ms, added_trailing_ms = ensure_reference_edge_silence(
            audio,
            1000,
        )

        self.assertEqual((added_leading_ms, added_trailing_ms), (100, 200))
        self.assertEqual(padded.shape, (1, 800))
        np.testing.assert_array_equal(padded[:, 100:600], audio)
        self.assertEqual(np.count_nonzero(padded[:, :100]), 0)
        self.assertEqual(np.count_nonzero(padded[:, 600:]), 0)
        self.assertEqual(edge_silence_durations(padded, 1000), (100, 200))

    def test_clone_reference_edge_padding_only_adds_missing_silence(self) -> None:
        audio = np.concatenate(
            [
                np.zeros((1, 50), dtype=np.float32),
                np.full((1, 500), 0.25, dtype=np.float32),
                np.zeros((1, 150), dtype=np.float32),
            ],
            axis=-1,
        )

        padded, added_leading_ms, added_trailing_ms = ensure_reference_edge_silence(
            audio,
            1000,
        )

        self.assertEqual((added_leading_ms, added_trailing_ms), (50, 50))
        self.assertEqual(edge_silence_durations(padded, 1000), (100, 200))

    def test_reference_analysis_warns_about_abrupt_boundaries(self) -> None:
        audio = np.full((1, 4_000), 0.25, dtype=np.float32)

        analysis = analyze_reference_audio(audio, 1000)

        codes = {warning["code"] for warning in analysis["warnings"]}
        self.assertEqual(
            codes,
            {"reference_starts_on_speech", "reference_ends_on_speech"},
        )
        self.assertEqual(analysis["prompt_padding"], {"leading_ms": 100, "trailing_ms": 200})

    def test_reference_analysis_accepts_healthy_boundaries(self) -> None:
        audio = np.concatenate(
            [
                np.zeros((1, 100), dtype=np.float32),
                np.full((1, 3_700), 0.25, dtype=np.float32),
                np.zeros((1, 200), dtype=np.float32),
            ],
            axis=-1,
        )

        analysis = analyze_reference_audio(audio, 1000)

        self.assertEqual(analysis["warnings"], [])
        self.assertEqual(analysis["leading_silence_ms"], 100)
        self.assertEqual(analysis["trailing_silence_ms"], 200)
        self.assertEqual(analysis["prompt_padding"], {"leading_ms": 0, "trailing_ms": 0})

    def test_float_preserving_mode_does_not_quantize_retained_samples(self) -> None:
        audio = np.array([[0.1234567, -0.2345678, 0.3456789]], dtype=np.float32)

        preserved = remove_silence(
            audio,
            1000,
            mid_sil=0,
            lead_sil=100,
            trail_sil=100,
            preserve_float=True,
        )
        legacy = remove_silence(
            audio,
            1000,
            mid_sil=0,
            lead_sil=100,
            trail_sil=100,
            preserve_float=False,
        )

        np.testing.assert_array_equal(preserved, audio)
        self.assertFalse(np.array_equal(legacy, audio))

    def test_middle_silence_detection_and_retained_gap_are_separate(self) -> None:
        audio = np.concatenate(
            [
                np.full((1, 100), 0.25, dtype=np.float32),
                np.zeros((1, 1200), dtype=np.float32),
                np.full((1, 100), -0.25, dtype=np.float32),
            ],
            axis=-1,
        )

        processed = remove_silence(
            audio,
            1000,
            mid_sil=500,
            keep_mid_sil=200,
            lead_sil=0,
            trail_sil=0,
        )

        self.assertEqual(processed.shape[-1], 400)
        self.assertEqual(np.count_nonzero(processed), 200)

    def test_float_and_legacy_defaults_retain_the_same_timing(self) -> None:
        sample_rate = 24_000
        audio = np.concatenate(
            [
                np.full((1, 2_400), 0.25, dtype=np.float32),
                np.zeros((1, 28_800), dtype=np.float32),
                np.full((1, 2_400), -0.25, dtype=np.float32),
            ],
            axis=-1,
        )

        preserved = remove_silence(
            audio,
            sample_rate,
            mid_sil=500,
            keep_mid_sil=1000,
            lead_sil=100,
            trail_sil=100,
            preserve_float=True,
        )
        legacy = remove_silence(
            audio,
            sample_rate,
            mid_sil=500,
            keep_mid_sil=1000,
            lead_sil=100,
            trail_sil=100,
            preserve_float=False,
        )

        self.assertEqual(preserved.shape, legacy.shape)

    def test_fractional_millisecond_endpoint_is_retained(self) -> None:
        audio = np.full((1, 24_001), 0.2, dtype=np.float32)

        processed = remove_silence(
            audio,
            24_000,
            mid_sil=500,
            keep_mid_sil=1000,
            lead_sil=0,
            trail_sil=0,
        )

        self.assertEqual(processed.shape[-1], audio.shape[-1])
        self.assertEqual(processed[0, -1], audio[0, -1])

    def test_quiet_active_edges_are_opt_in(self) -> None:
        audio = np.concatenate(
            [
                np.full((1, 20), 0.0001, dtype=np.float32),
                np.full((1, 100), 0.2, dtype=np.float32),
                np.full((1, 20), 0.0001, dtype=np.float32),
            ],
            axis=-1,
        )

        trimmed = remove_silence(audio, 1000, mid_sil=0, lead_sil=0, trail_sil=0)
        preserved = remove_silence(
            audio,
            1000,
            mid_sil=0,
            lead_sil=0,
            trail_sil=0,
            preserve_active_edges=True,
        )

        self.assertEqual(trimmed.shape[-1], 100)
        np.testing.assert_array_equal(preserved, audio)

    def test_peak_limit_only_scales_audio_above_ceiling(self) -> None:
        audio = np.array([[0.25, -1.0, 0.5]], dtype=np.float32)

        limited = limit_audio_peak(audio, 0.8)

        self.assertAlmostEqual(float(np.max(np.abs(limited))), 0.8, places=6)
        self.assertAlmostEqual(float(limited[0, 0] / limited[0, 2]), 0.5, places=6)
        self.assertIs(limit_audio_peak(audio, None), audio)

    def test_empty_generated_audio_is_safe(self) -> None:
        model = SimpleNamespace(sampling_rate=24_000)
        output = OmniVoice._post_process_audio(
            model,
            np.zeros((1, 0), dtype=np.float32),
            ref_rms=None,
            gen_config=OmniVoiceGenerationConfig(),
        )
        self.assertEqual(output.shape, (1, 0))

    def test_duration_rounding_and_validation(self) -> None:
        self.assertEqual(_duration_to_target_tokens(29 / 25, 25), 29)
        self.assertEqual(_duration_to_target_tokens(1.17, 25), 29)
        self.assertEqual(_normalize_duration_values(1.0, 2), [1.0, 1.0])
        self.assertEqual(_normalize_duration_values([1.0, None], 2), [1.0, None])
        with self.assertRaises(ValueError):
            _normalize_duration_values([1.0], 2)
        with self.assertRaises(TypeError):
            _normalize_duration_values(True, 1)
        with self.assertRaises(ValueError):
            _duration_to_target_tokens(float("nan"), 25)


if __name__ == "__main__":
    unittest.main()
