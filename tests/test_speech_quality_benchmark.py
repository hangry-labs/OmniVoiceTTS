from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "benchmarks" / "speech-quality" / "run_benchmark.py"
SPEC = importlib.util.spec_from_file_location("benchmark_speech_quality", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)

JUDGE_LANGUAGES = {
    "Arabic", "Chinese", "Dutch", "English", "French", "German", "Hindi", "Indonesian",
    "Italian", "Japanese", "Korean", "Polish", "Portuguese", "Russian", "Spanish", "Thai",
    "Turkish", "Vietnamese",
}


class SpeechQualityBenchmarkTests(unittest.TestCase):
    def test_normalization_ignores_case_punctuation_and_spacing(self) -> None:
        self.assertEqual(
            benchmark.normalize_transcript("Hello, WORLD! 42"),
            benchmark.normalize_transcript("hello world 42"),
        )
        self.assertEqual(benchmark.transcript_similarity("Jesteśmy gotowi?", "jesteśmy gotowi !"), 100.0)

    def test_manifest_workload_uses_clone_warmup_and_fixed_first_two_sentences(self) -> None:
        warmups, measurements = benchmark.load_workload(
            ROOT / "examples" / "assets" / "manifest.json",
            sentence_count=2,
            repeats=5,
            supported_languages=JUDGE_LANGUAGES,
        )
        self.assertEqual(len(warmups), 18)
        self.assertEqual(len(measurements), 180)
        self.assertNotIn("bengali", {item["language_slug"] for item in measurements})
        self.assertNotIn("urdu", {item["language_slug"] for item in measurements})
        self.assertEqual(measurements[0]["case_id"], "english_random_01")
        self.assertEqual(measurements[4]["repeat"], 5)
        self.assertEqual(measurements[0]["seed"], measurements[4]["seed"])
        self.assertNotEqual(measurements[0]["seed"], measurements[5]["seed"])

    def test_language_filter_accepts_slug_and_qwen_arabic_alias(self) -> None:
        warmups, measurements = benchmark.load_workload(
            ROOT / "examples" / "assets" / "manifest.json",
            sentence_count=1,
            repeats=1,
            supported_languages=JUDGE_LANGUAGES,
            language_filter={"standard_arabic"},
        )
        self.assertEqual(len(warmups), 1)
        self.assertEqual(len(measurements), 1)
        self.assertEqual(
            benchmark.resolved_asr_language("Standard Arabic", {"Arabic", "English"}),
            "Arabic",
        )
        self.assertIsNone(benchmark.resolved_asr_language("Bengali", {"Arabic", "English"}))

    def test_unsupported_language_filter_is_rejected_before_generation(self) -> None:
        with self.assertRaisesRegex(ValueError, "No judge-supported manifest languages matched"):
            benchmark.load_workload(
                ROOT / "examples" / "assets" / "manifest.json",
                sentence_count=1,
                repeats=1,
                supported_languages=JUDGE_LANGUAGES,
                language_filter={"bengali"},
            )

    def test_summary_rows_are_inserted_before_following_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "BENCHMARKS.md"
            path.write_text(
                f"| header |\n{benchmark.SUMMARY_ROWS_MARKER}\n\n## Guidance\n",
                encoding="utf-8",
            )
            benchmark.insert_summary_row(path, "| result |\n")
            content = path.read_text(encoding="utf-8")
        self.assertLess(content.index("| result |"), content.index(benchmark.SUMMARY_ROWS_MARKER))
        self.assertLess(content.index(benchmark.SUMMARY_ROWS_MARKER), content.index("## Guidance"))

    def test_case_summary_detects_repeat_inconsistency(self) -> None:
        calls = [
            {
                "case_id": "english_random_01",
                "language_slug": "english",
                "language": "English",
                "sentence_index": 1,
                "text": "Hello world.",
                "transcript": transcript,
                "transcript_normalized": benchmark.normalize_transcript(transcript),
                "similarity_percent": benchmark.transcript_similarity("Hello world.", transcript),
                "exact": transcript == "Hello world.",
            }
            for transcript in ("Hello world.", "Hello word.")
        ]
        summary = benchmark.summarize_cases(calls, repeats=2)[0]
        self.assertFalse(summary["consistent"])
        self.assertEqual(summary["unique_normalized_transcripts"], 2)
        self.assertEqual(summary["exact_repeats"], 1)


if __name__ == "__main__":
    unittest.main()
