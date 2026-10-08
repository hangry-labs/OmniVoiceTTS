from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


speed = load_script("benchmark_speed", "benchmarks/speed/run_benchmark.py")
cpu_memory = load_script("benchmark_cpu_memory", "benchmarks/memory/cpu/run_benchmark.py")
gpu_memory = load_script("benchmark_gpu_memory", "benchmarks/memory/gpu/run_benchmark.py")
ssml = load_script("benchmark_ssml", "benchmarks/ssml/run_benchmark.py")


class BenchmarkLayoutTests(unittest.TestCase):
    def test_landing_page_documents_reproducible_methodology(self) -> None:
        readme = (ROOT / "benchmarks" / "README.md").read_text(encoding="utf-8")
        for expected in (
            "examples/assets/manifest.json",
            "examples/original_clone.mp3",
            "first two `random` entries",
            "100 calls",
            "180 measured calls",
            "Qwen3-ASR is a stable comparative judge, not ground truth",
            "2717518076",
            "task benchmark-memory-cpu",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, readme)

    def test_every_suite_has_runner_summary_and_details(self) -> None:
        suites = (
            "speed",
            "memory/cpu",
            "memory/gpu",
            "speech-quality",
            "ssml",
        )
        for suite in suites:
            directory = ROOT / "benchmarks" / suite
            with self.subTest(suite=suite):
                self.assertTrue((directory / "run_benchmark.py").is_file())
                self.assertTrue((directory / "BENCHMARKS.md").is_file())
                self.assertTrue((directory / "DETAILS.md").is_file())

    def test_runners_resolve_defaults_inside_their_suite(self) -> None:
        self.assertEqual(speed.RESULTS_PATH, ROOT / "benchmarks" / "speed" / "runs.json")
        self.assertEqual(cpu_memory.DEFAULT_RESULTS, ROOT / "benchmarks" / "memory" / "cpu" / "runs.json")
        self.assertEqual(gpu_memory.DEFAULT_RESULTS, ROOT / "benchmarks" / "memory" / "gpu" / "runs.json")
        self.assertEqual(ssml.DEFAULT_RESULTS, ROOT / "benchmarks" / "ssml" / "runs.json")

    def test_speed_workload_remains_fixed_and_deterministic(self) -> None:
        workload = speed.load_workload(
            ROOT / "examples" / "assets" / "manifest.json",
            items_per_round=100,
            samples_per_language=2,
        )
        self.assertEqual(len(workload), 100)
        self.assertEqual(workload[0]["language_slug"], "english")
        self.assertEqual(workload[0]["index"], 1)
        self.assertEqual(workload[40]["language_slug"], "english")
        self.assertEqual(workload[40]["repeat"], 1)

    def test_cpu_recommendations_keep_operational_headroom(self) -> None:
        self.assertEqual(cpu_memory.recommendation_from_limit("1536m"), "2 GB")
        self.assertEqual(cpu_memory.recommendation_from_limit("2048m"), "3 GB")
        self.assertEqual(cpu_memory.recommendation_from_limit(None), "n/a")

    def test_cpu_runner_mounts_profiles_at_current_persistent_path(self) -> None:
        source = (ROOT / "benchmarks" / "memory" / "cpu" / "run_benchmark.py").read_text(encoding="utf-8")
        self.assertIn("/app/persistent/voices/openai", source)
        self.assertNotIn(":/app/openai_voice_profiles", source)

    def test_cpu_runner_places_image_after_complete_docker_options(self) -> None:
        command = cpu_memory.build_docker_run_command(
            image="omnivoicetts:test",
            limit="2048m",
            port=7870,
            profile_dir=ROOT / "profiles",
            container="benchmark-container",
        )
        self.assertEqual(command[-1], "omnivoicetts:test")
        self.assertNotEqual(command[-2], "-v")
        self.assertEqual(command.count("-v"), 2)

    def test_gpu_scenarios_cover_all_voice_memory_paths(self) -> None:
        scenarios = gpu_memory.build_scenarios("Benchmark text.", gpu_memory.DEFAULT_REFERENCE_AUDIO)
        self.assertEqual([scenario.code for scenario in scenarios], ["RV", "DV", "CR", "CC"])
        self.assertNotIn("ref_audio", scenarios[0].payload)
        self.assertIn("instruct", scenarios[1].payload)
        self.assertFalse(scenarios[2].payload.get("cache_voice_prompt", False))
        self.assertTrue(scenarios[3].payload["cache_voice_prompt"])

    def test_ssml_first_seed_retains_known_regression_case(self) -> None:
        self.assertEqual(ssml.seeds_for_calls(1), [ssml.KNOWN_PRE_FIX_FAILURE_SEED])

    def test_taskfile_keeps_benchmarks_manual_and_exposes_smokes(self) -> None:
        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        for task in (
            "benchmark-speed-smoke:",
            "benchmark-memory-cpu-smoke:",
            "benchmark-memory-gpu-smoke:",
            "benchmark-speech-quality-smoke:",
            "benchmark-ssml-smoke:",
        ):
            self.assertIn(task, taskfile)
        validate_block = taskfile.split("  validate:", 1)[1].split("\n  ", 1)[0]
        self.assertNotIn("benchmark-", validate_block)


if __name__ == "__main__":
    unittest.main()
