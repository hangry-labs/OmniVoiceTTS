from __future__ import annotations

import tempfile
import unittest
from collections import OrderedDict
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import torch
from fastapi import HTTPException
from fastapi.testclient import TestClient

import omnivoice.app as runtime
from omnivoice.cli import infer, infer_batch
from omnivoice.service.schemas import CPUPrecisionSettingsUpdate
from omnivoice.settings import RuntimeSettingsStore


class CPUPrecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.store = RuntimeSettingsStore(Path(directory) / "settings.json")
        self.stack.enter_context(patch.object(runtime, "RUNTIME_SETTINGS", self.store))
        self.stack.enter_context(patch.object(runtime, "CPU_FP32_DEFAULT", False))
        self.stack.enter_context(patch.object(runtime, "MODEL_CACHE", {}))
        self.stack.enter_context(patch.object(runtime, "VOICE_CLONE_PROMPT_CACHE", OrderedDict()))
        self.stack.enter_context(patch.object(runtime, "GENERATION_SEMAPHORES", {}))
        self.stack.enter_context(patch.object(runtime, "MAX_CONCURRENT_GENERATIONS", 2))

    def test_server_defaults_to_half_precision_on_cpu(self) -> None:
        with patch.object(runtime.OmniVoice, "from_pretrained") as load:
            runtime.get_model("cpu")
        self.assertIs(load.call_args.kwargs["dtype"], torch.float16)
        self.assertEqual(runtime.cpu_precision_payload(), {"cpu_fp32": False, "dtype": "float16"})

    def test_saved_preference_survives_store_reload_and_selects_fp32(self) -> None:
        self.store.set("cpu_fp32", True)
        restored = RuntimeSettingsStore(self.store.path)
        with (
            patch.object(runtime, "RUNTIME_SETTINGS", restored),
            patch.object(runtime.OmniVoice, "from_pretrained") as load,
        ):
            runtime.get_model("cpu")
        self.assertIs(load.call_args.kwargs["dtype"], torch.float32)

    def test_environment_default_is_overridden_by_saved_false(self) -> None:
        with patch.object(runtime, "CPU_FP32_DEFAULT", True):
            self.assertTrue(runtime.cpu_precision_payload()["cpu_fp32"])
            self.store.set("cpu_fp32", False)
            self.assertFalse(runtime.cpu_precision_payload()["cpu_fp32"])

    def test_invalid_stored_values_do_not_enable_fp32(self) -> None:
        for invalid in ("false", "true", 1, None):
            with self.subTest(value=invalid):
                self.store.set("cpu_fp32", invalid)
                self.assertFalse(runtime.cpu_precision_payload()["cpu_fp32"])

    def test_server_gpu_and_mps_precision_is_unchanged(self) -> None:
        for enabled in (False, True):
            for device, expected in (("cuda:0", torch.float16), ("mps", torch.float32)):
                with self.subTest(enabled=enabled, device=device):
                    self.store.set("cpu_fp32", enabled)
                    with (
                        patch.object(runtime, "MODEL_CACHE", {}),
                        patch.object(runtime, "normalize_device", return_value=device),
                        patch.object(runtime.OmniVoice, "from_pretrained") as load,
                    ):
                        runtime.get_model(device)
                    self.assertIs(load.call_args.kwargs["dtype"], expected)

    def seed_caches(self) -> tuple[object, object]:
        cpu = SimpleNamespace(dtype=torch.float16)
        gpu = SimpleNamespace(dtype=torch.float16)
        runtime.MODEL_CACHE.update({"cpu": cpu, "cuda:0": gpu})
        runtime.VOICE_CLONE_PROMPT_CACHE.update({("cpu", "reference"): object(), ("cuda:0", "reference"): object()})
        return cpu, gpu

    def test_api_saves_setting_and_invalidates_only_cpu_entries(self) -> None:
        _cpu, gpu = self.seed_caches()
        self.store.set("unrelated", {"preserve": True})
        with TestClient(runtime.api) as client:
            response = client.put("/system/settings/cpu-precision", json={"cpu_fp32": True})
            settings = client.get("/system/settings").json()
            status = client.get("/tts/status").json()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["changed"])
        self.assertEqual(response.json()["purged_model_devices"], ["cpu"])
        self.assertEqual(response.json()["purged_voice_prompts"], 1)
        self.assertEqual(settings["cpu_precision"], {"cpu_fp32": True, "dtype": "float32"})
        self.assertEqual(status["loaded_model_dtypes"], {"cuda:0": "float16"})
        self.assertIs(runtime.MODEL_CACHE["cuda:0"], gpu)
        self.assertEqual(list(runtime.VOICE_CLONE_PROMPT_CACHE), [("cuda:0", "reference")])
        self.assertEqual(self.store.get("unrelated"), {"preserve": True})
        with patch.object(runtime.OmniVoice, "from_pretrained") as load:
            runtime.get_model("cpu")
        self.assertIs(load.call_args.kwargs["dtype"], torch.float32)

    def test_noop_setting_preserves_models_and_prompts(self) -> None:
        cpu, gpu = self.seed_caches()
        result = runtime.save_cpu_precision(CPUPrecisionSettingsUpdate(cpu_fp32=False))
        self.assertFalse(result["changed"])
        self.assertEqual(result["purged_model_devices"], [])
        self.assertEqual(result["purged_voice_prompts"], 0)
        self.assertIs(runtime.MODEL_CACHE["cpu"], cpu)
        self.assertIs(runtime.MODEL_CACHE["cuda:0"], gpu)
        self.assertEqual(len(runtime.VOICE_CLONE_PROMPT_CACHE), 2)

    def test_busy_cpu_rejects_change_and_releases_partial_capacity(self) -> None:
        cpu, _gpu = self.seed_caches()
        semaphore = runtime.get_generation_semaphore("cpu")
        with semaphore:
            with TestClient(runtime.api) as client:
                response = client.put("/system/settings/cpu-precision", json={"cpu_fp32": True})
            self.assertEqual(response.status_code, 409, response.text)
            self.assertIs(runtime.MODEL_CACHE["cpu"], cpu)
            self.assertFalse(runtime.cpu_precision_payload()["cpu_fp32"])
            self.assertEqual(len(runtime.VOICE_CLONE_PROMPT_CACHE), 2)
            self.assertTrue(semaphore.acquire(blocking=False))
            self.assertFalse(semaphore.acquire(blocking=False))
            semaphore.release()
        self.assertTrue(semaphore.acquire(blocking=False))
        self.assertTrue(semaphore.acquire(blocking=False))
        semaphore.release()
        semaphore.release()

    def test_storage_failure_preserves_cached_state_and_releases_capacity(self) -> None:
        cpu, _gpu = self.seed_caches()
        with patch.object(self.store, "set", side_effect=OSError("Disk full")):
            with self.assertRaisesRegex(OSError, "Disk full"):
                runtime.save_cpu_precision(CPUPrecisionSettingsUpdate(cpu_fp32=True))
        self.assertIs(runtime.MODEL_CACHE["cpu"], cpu)
        self.assertEqual(len(runtime.VOICE_CLONE_PROMPT_CACHE), 2)
        semaphore = runtime.get_generation_semaphore("cpu")
        self.assertTrue(semaphore.acquire(blocking=False))
        self.assertTrue(semaphore.acquire(blocking=False))
        semaphore.release()
        semaphore.release()

    def test_api_rejects_non_boolean_precision(self) -> None:
        with TestClient(runtime.api) as client:
            response = client.put("/system/settings/cpu-precision", json={"cpu_fp32": "false"})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertFalse(runtime.cpu_precision_payload()["cpu_fp32"])


class CLIPrecisionTests(unittest.TestCase):
    def test_single_cli_cpu_flag_and_gpu_defaults(self) -> None:
        model = SimpleNamespace(sampling_rate=24_000, generate=Mock(return_value=[np.zeros(240)]))
        for device, flags, expected in (
            ("cpu", [], torch.float16),
            ("cpu", ["--cpu-fp32"], torch.float32),
            ("cpu:0", ["--cpu_fp32"], torch.float32),
            ("cuda:0", ["--cpu-fp32"], torch.float16),
            ("mps", ["--cpu-fp32"], torch.float16),
        ):
            with self.subTest(device=device, flags=flags):
                with (
                    patch("sys.argv", ["omnivoice-infer", "--text", "Hello.", "--output", "test.wav", "--device", device, *flags]),
                    patch.object(infer.OmniVoice, "from_pretrained", return_value=model) as load,
                    patch.object(infer, "write_encoded_audio_file"),
                ):
                    infer.main()
                self.assertIs(load.call_args.kwargs["dtype"], expected)

    def test_batch_worker_cpu_opt_in_is_forwarded_before_warmup(self) -> None:
        for device, enabled, expected in (
            ("cpu", False, torch.float16),
            ("cpu", True, torch.float32),
            ("cuda", True, torch.float16),
            ("mps", True, torch.float16),
        ):
            with self.subTest(device=device, enabled=enabled):
                queue = Mock(get=Mock(return_value=(device, 0)))
                model = Mock()
                with (
                    patch.object(infer_batch, "worker_model", None),
                    patch.object(infer_batch.torch, "set_num_threads"),
                    patch.object(infer_batch.torch, "set_num_interop_threads"),
                    patch.object(infer_batch.OmniVoice, "from_pretrained", return_value=model) as load,
                ):
                    infer_batch.process_init(queue, "checkpoint", warmup=1, cpu_fp32=enabled)
                self.assertIs(load.call_args.kwargs["dtype"], expected)
                model.generate.assert_called_once()

    def test_batch_parser_defaults_off_and_accepts_both_flag_spellings(self) -> None:
        base = ["--test_list", "input.jsonl", "--res_dir", "output"]
        self.assertFalse(infer_batch.get_parser().parse_args(base).cpu_fp32)
        for flag in ("--cpu-fp32", "--cpu_fp32"):
            self.assertTrue(infer_batch.get_parser().parse_args([*base, flag]).cpu_fp32)


if __name__ == "__main__":
    unittest.main()
