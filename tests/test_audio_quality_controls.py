from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from omnivoice.models.omnivoice import (
    OmniVoice,
    OmniVoiceGenerationConfig,
    _duration_to_target_tokens,
    _normalize_duration_values,
)
from omnivoice.utils.audio import limit_audio_peak, remove_silence


class AudioQualityControlTests(unittest.TestCase):
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
