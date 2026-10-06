from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from omnivoice.cli import infer, infer_batch
from omnivoice.cli.audio_output import resolve_audio_output_path
from omnivoice.service.audio import (
    OUTPUT_FORMATS,
    audio_to_wav_bytes,
    encode_audio_bytes,
    write_audio_bytes_atomic,
)


class CliAudioOutputTests(unittest.TestCase):
    def test_output_path_infers_or_applies_the_requested_format(self) -> None:
        self.assertEqual(
            resolve_audio_output_path("speech"),
            (Path("speech.wav"), "wav"),
        )
        self.assertEqual(
            resolve_audio_output_path("speech.mp3"),
            (Path("speech.mp3"), "mp3"),
        )
        self.assertEqual(
            resolve_audio_output_path("speech.wav", "flac"),
            (Path("speech.flac"), "flac"),
        )
        with self.assertRaisesRegex(ValueError, "Unsupported output format"):
            resolve_audio_output_path("speech.aac")

    def test_both_cli_parsers_advertise_every_runtime_format(self) -> None:
        for output_format in OUTPUT_FORMATS:
            single = infer.get_parser().parse_args(
                [
                    "--text",
                    "Hello",
                    "--output",
                    "speech.wav",
                    "--format",
                    output_format,
                ]
            )
            batch = infer_batch.get_parser().parse_args(
                [
                    "--test_list",
                    "samples.jsonl",
                    "--res_dir",
                    "results",
                    "--format",
                    output_format,
                ]
            )
            self.assertEqual(single.output_format, output_format)
            self.assertEqual(batch.output_format, output_format)

    def test_wav_encoder_interleaves_channel_first_audio(self) -> None:
        audio = np.array(
            [[0.5, 0.25, 0.0], [-0.5, -0.25, 0.0]],
            dtype=np.float32,
        )
        encoded = audio_to_wav_bytes(audio, 24_000)
        with wave.open(io.BytesIO(encoded), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 2)
            self.assertEqual(wav_file.getnframes(), 3)
            samples = np.frombuffer(wav_file.readframes(3), dtype="<i2").reshape(-1, 2)

        np.testing.assert_array_equal(
            samples,
            np.array(
                [[16383, -16383], [8191, -8191], [0, 0]],
                dtype=np.int16,
            ),
        )

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required for codec tests")
    def test_shared_encoder_produces_every_advertised_format(self) -> None:
        time_axis = np.arange(2_400, dtype=np.float32) / 24_000
        audio = (0.2 * np.sin(2 * np.pi * 440 * time_axis)).astype(np.float32)
        signatures = {
            "wav": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WAVE",
            "mp3": lambda data: data.startswith(b"ID3") or data.startswith(b"\xff"),
            "flac": lambda data: data.startswith(b"fLaC"),
            "ogg": lambda data: data.startswith(b"OggS"),
        }

        for output_format in OUTPUT_FORMATS:
            with self.subTest(output_format=output_format):
                encoded = encode_audio_bytes(audio, output_format, 24_000)
                self.assertTrue(signatures[output_format](encoded))

    def test_atomic_writer_preserves_the_previous_file_on_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "speech.wav"
            output.write_bytes(b"previous")
            with (
                patch("omnivoice.service.audio.os.replace", side_effect=OSError("blocked")),
                self.assertRaisesRegex(OSError, "blocked"),
            ):
                write_audio_bytes_atomic(output, b"replacement")

            self.assertEqual(output.read_bytes(), b"previous")
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])

    def test_single_cli_uses_shared_encoder_and_normalized_extension(self) -> None:
        model = SimpleNamespace(
            sampling_rate=24_000,
            generate=Mock(return_value=[np.zeros(240, dtype=np.float32)]),
        )
        with (
            patch.object(
                sys,
                "argv",
                [
                    "omnivoice-infer",
                    "--text",
                    "Hello",
                    "--output",
                    "speech.wav",
                    "--format",
                    "mp3",
                    "--device",
                    "cpu",
                ],
            ),
            patch.object(infer.OmniVoice, "from_pretrained", return_value=model),
            patch.object(infer, "write_encoded_audio_file") as writer,
        ):
            infer.main()

        writer.assert_called_once()
        self.assertEqual(writer.call_args.args[1], Path("speech.mp3"))
        self.assertEqual(writer.call_args.args[2], "mp3")
        self.assertEqual(writer.call_args.args[3], 24_000)

    def test_batch_stages_every_encoding_before_committing_outputs(self) -> None:
        model = SimpleNamespace(
            sampling_rate=24_000,
            generate=Mock(
                return_value=[
                    np.zeros(240, dtype=np.float32),
                    np.ones(240, dtype=np.float32),
                ]
            ),
        )
        samples = [
            ("first.wav", None, None, "One", "en", None, None, None),
            ("second.mp3", None, None, "Two", "en", None, None, None),
        ]
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(infer_batch, "worker_model", model),
                patch.object(
                    infer_batch,
                    "encode_audio_bytes",
                    side_effect=[b"first", RuntimeError("encode failed")],
                ),
                self.assertRaisesRegex(RuntimeError, "encode failed"),
            ):
                infer_batch.run_inference_batch(
                    samples,
                    directory,
                    output_format="ogg",
                )

            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_batch_normalizes_input_ids_to_the_selected_extension(self) -> None:
        model = SimpleNamespace(
            sampling_rate=24_000,
            generate=Mock(return_value=[np.zeros(240, dtype=np.float32)]),
        )
        sample = [("sample.wav", None, None, "One", "en", None, None, None)]
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(infer_batch, "worker_model", model),
                patch.object(infer_batch, "encode_audio_bytes", return_value=b"encoded"),
            ):
                results = infer_batch.run_inference_batch(
                    sample,
                    directory,
                    output_format="flac",
                )

            self.assertEqual((Path(directory) / "sample.flac").read_bytes(), b"encoded")
            self.assertEqual(results[0][0], "sample.wav")

    def test_batch_cli_reports_worker_failures_with_a_nonzero_exit(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "2 of 5 inference batches failed"):
            infer_batch._raise_for_failed_batches(2, 5)

        infer_batch._raise_for_failed_batches(0, 5)


if __name__ == "__main__":
    unittest.main()
