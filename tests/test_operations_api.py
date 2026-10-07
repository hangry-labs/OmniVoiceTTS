from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

import omnivoice.app as app_module
from omnivoice.models.omnivoice import OmniVoice
from omnivoice.service.runtime_diagnostics import GenerationDiagnostics


class _ReadyModel:
    sampling_rate = 24_000


class _PreflightModel(_ReadyModel):
    def preflight_text(self, **kwargs):
        return {
            "source_characters": len(kwargs["text"]),
            "text_tokens": 4,
            "model_text_tokens": 6,
            "estimated_audio_tokens": 50,
            "estimated_duration_seconds": 2.0,
            "chunking": {"enabled": False, "estimated_chunks": 1},
        }


class _StreamingModel(_ReadyModel):
    def generate_stream(self, **_kwargs):
        yield np.zeros(240, dtype=np.float32)


class OperationsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app_module.GENERATION_DIAGNOSTICS.reset()

    def test_request_id_is_returned_and_validation_errors_are_structured(self) -> None:
        with TestClient(app_module.api) as client:
            response = client.post(
                "/tts/generate",
                headers={"X-Request-ID": "client-request-42"},
                json={"text": ""},
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["X-Request-ID"], "client-request-42")
        self.assertEqual(response.json()["error"]["request_id"], "client-request-42")
        self.assertEqual(response.json()["error"]["code"], "validation_error")
        self.assertIn("detail", response.json())

    def test_invalid_request_id_is_replaced(self) -> None:
        with TestClient(app_module.api) as client:
            response = client.get("/tts/ping", headers={"X-Request-ID": "not allowed / value"})

        request_id = response.headers["X-Request-ID"]
        self.assertTrue(request_id.startswith("req_"))
        self.assertEqual(len(request_id), 36)

    def test_custom_validation_error_does_not_echo_input_or_exception_objects(self) -> None:
        with TestClient(app_module.api) as client:
            response = client.post("/tts/generate", json={"text": "!!!"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "validation_error")
        self.assertNotIn("input", payload["detail"][0])
        self.assertNotIn("ctx", payload["detail"][0])

    def test_readiness_loads_and_reports_the_resolved_model(self) -> None:
        with (
            patch.object(app_module, "DEFAULT_DEVICE", "cpu"),
            patch.object(app_module, "MODEL_CACHE", {}),
            patch.object(app_module, "get_model", return_value=_ReadyModel()) as get_model,
        ):
            with TestClient(app_module.api) as client:
                response = client.get("/tts/ready")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["ready"])
        self.assertEqual(response.json()["device"], "cpu")
        self.assertFalse(response.json()["model_loaded_before_check"])
        get_model.assert_called_once_with("cpu")

    def test_readiness_returns_503_when_model_loading_fails(self) -> None:
        with (
            patch.object(app_module, "DEFAULT_DEVICE", "cpu"),
            patch.object(app_module, "MODEL_CACHE", {}),
            patch.object(app_module, "get_model", side_effect=RuntimeError("missing model")),
        ):
            with TestClient(app_module.api) as client:
                response = client.get("/tts/ready")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ready"])
        self.assertEqual(response.json()["error_type"], "RuntimeError")
        self.assertNotIn("missing model", response.json()["reason"])

    def test_preflight_uses_model_tokenizer_estimate(self) -> None:
        with (
            patch.object(app_module, "MODEL_CACHE", {}),
            patch.object(app_module, "get_model", return_value=_PreflightModel()),
        ):
            with TestClient(app_module.api) as client:
                response = client.post(
                    "/tts/preflight",
                    json={"text": "Hello world!", "device": "cpu", "audio_chunk_threshold": 30},
                )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["estimate"]["text_tokens"], 4)
        self.assertEqual(response.json()["estimate"]["estimated_audio_tokens"], 50)
        self.assertFalse(response.json()["model_loaded_before_request"])

    def test_model_preflight_uses_generation_text_rules(self) -> None:
        class _Tokenizer:
            def __call__(self, text, **_kwargs):
                return SimpleNamespace(input_ids=list(range(len(text.split()))))

        class _DurationEstimator:
            @staticmethod
            def estimate_duration(text, _ref_text, _ref_tokens):
                return len(text)

        model = OmniVoice.__new__(OmniVoice)
        model.text_tokenizer = _Tokenizer()
        model.audio_tokenizer = SimpleNamespace(config=SimpleNamespace(frame_rate=25))
        model.duration_estimator = _DurationEstimator()

        result = model.preflight_text(
            "Are we ready?",
            language="English",
            speed=1.0,
            audio_chunk_duration=0.2,
            audio_chunk_threshold=0.1,
        )

        self.assertTrue(result["terminal_punctuation_adjusted"])
        self.assertGreater(result["text_tokens"], 0)
        self.assertGreater(result["estimated_audio_tokens"], 0)
        self.assertTrue(result["chunking"]["enabled"])
        self.assertGreaterEqual(result["chunking"]["estimated_chunks"], 1)

    def test_upload_generation_uses_and_removes_temporary_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voice.wav"
            sf.write(source, np.full(24_000, 0.1, dtype=np.float32), 24_000)
            observed_paths: list[Path] = []

            def synthesize(**kwargs):
                observed = Path(kwargs["ref_audio"])
                self.assertTrue(observed.is_file())
                observed_paths.append(observed)
                return 24_000, np.zeros(2_400, dtype=np.float32)

            with (
                patch.object(app_module, "UI_UPLOAD_DIR", root / "uploads"),
                patch.object(app_module, "synthesize_array", side_effect=synthesize),
            ):
                with TestClient(app_module.api) as client, source.open("rb") as stream:
                    response = client.post(
                        "/tts/generate-upload",
                        files={"audio": ("voice.wav", stream, "audio/wav")},
                        data={
                            "request": '{"text":"Use this uploaded voice.","ref_text":"Reference transcript.","device":"cpu","format":"wav"}'
                        },
                    )

            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(observed_paths), 1)
            self.assertFalse(observed_paths[0].exists())

    def test_generation_diagnostics_tracks_queue_and_outcomes(self) -> None:
        diagnostics = GenerationDiagnostics(capacity=1)
        completed = diagnostics.queued("cuda:0", "req_done")
        diagnostics.started(completed)
        diagnostics.finished(completed, "completed")
        failed = diagnostics.queued("cuda:0", "req_failed")
        diagnostics.started(failed)
        diagnostics.finished(failed, "failed")

        snapshot = diagnostics.snapshot()
        device = snapshot["devices"]["cuda:0"]
        self.assertEqual(device["accepted"], 2)
        self.assertEqual(device["completed"], 1)
        self.assertEqual(device["failed"], 1)
        self.assertEqual(device["active"], 0)
        self.assertEqual(device["queued"], 0)
        self.assertEqual(device["last_request_id"], "req_failed")
        self.assertEqual(snapshot["totals"]["started"], 2)

    def test_progressive_generation_tracks_prompt_preparation_and_request_id(self) -> None:
        observed_active: list[int] = []

        def prepare_prompt(*_args, **_kwargs):
            observed_active.append(
                app_module.GENERATION_DIAGNOSTICS.snapshot()["devices"]["cpu"]["active"]
            )
            return None

        context_token = app_module.REQUEST_ID_CONTEXT.set("stream-request")
        try:
            with (
                patch.object(app_module, "get_model", return_value=_StreamingModel()),
                patch.object(
                    app_module,
                    "get_cached_voice_clone_prompt",
                    side_effect=prepare_prompt,
                ),
            ):
                sample_rate, chunks = app_module.synthesize_chunks(
                    "Stream this sentence.",
                    device="cpu",
                )
                rendered = list(chunks)
        finally:
            app_module.REQUEST_ID_CONTEXT.reset(context_token)

        self.assertEqual(sample_rate, 24_000)
        self.assertEqual(len(rendered), 1)
        self.assertEqual(observed_active, [1])
        stats = app_module.GENERATION_DIAGNOSTICS.snapshot()["devices"]["cpu"]
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["last_request_id"], "stream-request")


if __name__ == "__main__":
    unittest.main()
