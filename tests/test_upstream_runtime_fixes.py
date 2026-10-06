from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf
import torch

from omnivoice.cli.infer_batch import _get_audio_duration
from omnivoice.models.omnivoice import OmniVoice


class UpstreamRuntimeFixTests(unittest.TestCase):
    def test_batch_duration_uses_audio_metadata_without_decoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audio_path = Path(directory) / "reference.wav"
            sf.write(audio_path, np.zeros(24_000, dtype=np.float32), 24_000)

            with patch(
                "omnivoice.cli.infer_batch.load_audio",
                side_effect=AssertionError("full decode should not run"),
            ):
                duration = _get_audio_duration(str(audio_path))

        self.assertAlmostEqual(duration, 1.0, places=3)

    def test_asr_loader_uses_configured_model_and_device(self) -> None:
        model = SimpleNamespace(
            _asr_model_name="local/custom-whisper",
            _asr_model_revision="reviewed-revision",
            _asr_device="cpu",
            device=torch.device("cuda:0"),
            _asr_pipe=None,
        )
        pipeline = object()
        pipeline_factory = Mock(return_value=pipeline)
        transformers_module = ModuleType("transformers")
        transformers_module.pipeline = pipeline_factory

        with (
            patch(
                "omnivoice.models.omnivoice._resolve_model_path",
                return_value="/models/custom-whisper",
            ) as resolve_model_path,
            patch.dict(sys.modules, {"transformers": transformers_module}),
        ):
            OmniVoice.load_asr_model(model)

        resolve_model_path.assert_called_once_with(
            "local/custom-whisper",
            revision="reviewed-revision",
        )

        pipeline_factory.assert_called_once_with(
            "automatic-speech-recognition",
            model="/models/custom-whisper",
            dtype=torch.float32,
            device="cpu",
        )
        self.assertIs(model._asr_pipe, pipeline)


if __name__ == "__main__":
    unittest.main()
