from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from omnivoice.cli import infer_batch
from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.data_utils import read_test_list


class GenerateSpeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = OmniVoice.__new__(OmniVoice)
        self.model.duration_estimator = SimpleNamespace(
            estimate_duration=Mock(return_value=60)
        )
        self.model.audio_tokenizer = SimpleNamespace(
            config=SimpleNamespace(frame_rate=25)
        )
        self.model.sampling_rate = 24_000
        self.texts = ["Hello there.", "How are you?"]

    def test_mixed_speed_list_defaults_only_none_entries(self) -> None:
        for speeds, targets, resolved in (
            ([None, 1.5], [60, 40], [1.0, 1.5]),
            ([1.5, None], [40, 60], [1.5, 1.0]),
        ):
            with self.subTest(speeds=speeds):
                original = speeds.copy()
                task = self.model._preprocess_all(self.texts, speed=speeds)
                self.assertEqual(task.target_lens, targets)
                self.assertEqual(task.speed, resolved)
                self.assertEqual(speeds, original)

    def test_all_none_entries_use_the_default_speed(self) -> None:
        task = self.model._preprocess_all(self.texts, speed=[None, None])
        self.assertEqual(task.target_lens, [60, 60])
        self.assertEqual(task.speed, [1.0, 1.0])

    def test_single_item_optional_speed_list_uses_the_default(self) -> None:
        task = self.model._preprocess_all("Default speed.", speed=[None])
        self.assertEqual(task.target_lens, [60])
        self.assertEqual(task.speed, [1.0])

    def test_scalar_omitted_and_explicit_list_speeds_keep_existing_behavior(self) -> None:
        for speed, targets, resolved in (
            (None, [60, 60], None),
            (1.0, [60, 60], [1.0, 1.0]),
            (1.5, [40, 40], [1.5, 1.5]),
            (2, [30, 30], [2.0, 2.0]),
            ([0.5, 1.5], [120, 40], [0.5, 1.5]),
        ):
            with self.subTest(speed=speed):
                task = self.model._preprocess_all(self.texts, speed=speed)
                self.assertEqual(task.target_lens, targets)
                self.assertEqual(task.speed, resolved)

    def test_zero_is_not_mistaken_for_an_omitted_speed(self) -> None:
        # Preserve existing direct-Python behavior; HTTP validation is separate.
        task = self.model._preprocess_all(self.texts, speed=[0.0, None])
        self.assertEqual(task.target_lens, [60, 60])
        self.assertEqual(task.speed, [0.0, 1.0])

    def test_duration_overrides_remain_per_item_and_use_raw_estimates(self) -> None:
        for duration, targets, resolved in (
            ([1.2, None], [30, 40], [2.0, 1.5]),
            ([None, 1.2], [60, 30], [1.0, 2.0]),
            ([1.2, 2.0], [30, 50], [2.0, 1.2]),
            ([None, None], [60, 40], [1.0, 1.5]),
            (1.2, [30, 30], [2.0, 2.0]),
        ):
            with self.subTest(duration=duration):
                original = duration.copy() if isinstance(duration, list) else duration
                task = self.model._preprocess_all(
                    self.texts, speed=[None, 1.5], duration=duration
                )
                self.assertEqual(task.target_lens, targets)
                self.assertEqual(task.speed, resolved)
                self.assertEqual(duration, original)

    def test_partial_duration_without_speed_keeps_default_for_other_items(self) -> None:
        task = self.model._preprocess_all(self.texts, duration=[1.2, None])
        self.assertEqual(task.target_lens, [30, 60])
        self.assertEqual(task.speed, [2.0, 1.0])

    def test_mixed_jsonl_speeds_reach_real_preprocessing_and_encode_outputs(self) -> None:
        records = [
            {"id": "omitted", "text": "Default speed."},
            {"id": "null", "text": "Explicit null.", "speed": None},
            {"id": "fast", "text": "Faster speech.", "speed": 1.5},
            {"id": "duration", "text": "Duration wins.", "speed": 1.5, "duration": 1.2},
        ]
        tasks = []

        def generate(**kwargs):
            tasks.append(self.model._preprocess_all(**kwargs))
            return [np.zeros(240, dtype=np.float32) for _ in kwargs["text"]]

        self.model.generate = Mock(side_effect=generate)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "output").mkdir()
            source = root / "input.jsonl"
            source.write_text(
                "\n".join(json.dumps(item) for item in records) + "\n",
                encoding="utf-8",
            )
            fields = ("id", "ref_text", "ref_audio", "text", "language_id", "duration", "speed", "instruct")
            samples = [tuple(item.get(key) for key in fields) for item in read_test_list(source)]
            with patch.object(infer_batch, "worker_model", self.model):
                results = infer_batch.run_inference_batch(samples, str(root / "output"))
            self.assertEqual([item[0] for item in results], [item["id"] for item in records])
            self.assertTrue(all(item[3] == "success" for item in results))
            for record in records:
                with wave.open(str(root / "output" / f"{record['id']}.wav"), "rb") as audio:
                    self.assertEqual(audio.getframerate(), 24_000)
                    self.assertEqual(audio.getnframes(), 240)
        self.assertEqual(tasks[0].target_lens, [60, 60, 40, 30])
        self.assertEqual(tasks[0].speed, [1.0, 1.0, 1.5, 2.0])


if __name__ == "__main__":
    unittest.main()
