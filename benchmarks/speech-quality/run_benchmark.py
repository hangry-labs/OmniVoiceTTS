from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
import statistics
import subprocess
import tempfile
import time
import unicodedata
import urllib.request
import uuid
import wave
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TTS_URL = os.getenv("OMNIVOICE_QUALITY_BENCHMARK_TTS_URL", "http://127.0.0.1:7861")
DEFAULT_ASR_URL = os.getenv("OMNIVOICE_QUALITY_BENCHMARK_ASR_URL", "http://127.0.0.1:8000")
DEFAULT_MANIFEST = ROOT / "examples" / "assets" / "manifest.json"
DEFAULT_RESULTS = ROOT / "benchmarks" / "speech-quality" / "runs.json"
DEFAULT_SUMMARY = ROOT / "benchmarks" / "speech-quality" / "BENCHMARKS.md"
DEFAULT_DETAILS = ROOT / "benchmarks" / "speech-quality" / "DETAILS.md"
DEFAULT_ARTIFACTS = ROOT / ".ai" / "benchmark-speech-quality"
DEFAULT_REFERENCE_AUDIO = "/app/omnivoice/runtime_assets/voices/openai_default_voice.mp3"
DEFAULT_REFERENCE_TEXT = "Hello from OmniVoice. This Docker image includes a browser UI and an HTTP API."
DEFAULT_SENTENCES = 2
DEFAULT_REPEATS = 5
DEFAULT_NUM_STEP = 32
BASE_SEED = 24_681_000
ARABIC_LANGUAGE_NAMES = {"standard arabic", "arabic"}
SUMMARY_ROWS_MARKER = "<!-- benchmark-rows:end -->"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(tts_url: str, asr_url: str) -> None:
    deadline = time.monotonic() + 240
    pending = {"TTS": f"{tts_url}/tts/ping", "ASR": f"{asr_url}/health/ready"}
    while pending and time.monotonic() < deadline:
        for name, url in list(pending.items()):
            try:
                request_json("GET", url, timeout=5)
                del pending[name]
            except Exception:
                pass
        if pending:
            time.sleep(2)
    if pending:
        raise RuntimeError(f"Services did not become ready: {', '.join(pending)}")


def normalize_transcript(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(character for character in normalized if unicodedata.category(character)[0] in {"L", "N"})


def transcript_similarity(expected: str, actual: str) -> float:
    expected_normalized = normalize_transcript(expected)
    actual_normalized = normalize_transcript(actual)
    if not expected_normalized and not actual_normalized:
        return 100.0
    return round(100.0 * difflib.SequenceMatcher(None, expected_normalized, actual_normalized).ratio(), 2)


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * percentile_value + 99) // 100) - 1))
    return ordered[index]


def parse_language_filter(value: str) -> set[str]:
    return {item.strip().casefold() for item in value.split(",") if item.strip()}


def load_workload(
    manifest_path: Path,
    sentence_count: int,
    repeats: int,
    supported_languages: set[str],
    language_filter: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if sentence_count < 1:
        raise ValueError("--sentences must be at least 1")
    if repeats < 1:
        raise ValueError("--repeats must be at least 1")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    languages = manifest.get("languages", [])
    warmups: list[dict[str, Any]] = []
    measurements: list[dict[str, Any]] = []
    selected = 0
    for manifest_index, language_entry in enumerate(languages):
        slug = str(language_entry.get("slug") or "").strip()
        language = str(language_entry.get("language") or "").strip()
        if language_filter and slug.casefold() not in language_filter and language.casefold() not in language_filter:
            continue
        if resolved_asr_language(language, supported_languages) is None:
            continue
        clone_items = language_entry.get("clone") or []
        random_items = language_entry.get("random") or []
        if not clone_items or not str(clone_items[0].get("text") or "").strip():
            raise ValueError(f"Manifest language {slug or language!r} has no clone warmup sentence.")
        if len(random_items) < sentence_count:
            raise ValueError(
                f"Manifest language {slug or language!r} has {len(random_items)} random sentences; "
                f"{sentence_count} are required."
            )
        selected += 1
        warmups.append(
            {
                "case_id": f"{slug}_clone_01_warmup",
                "language_slug": slug,
                "language": language,
                "text": str(clone_items[0]["text"]).strip(),
                "seed": BASE_SEED + 50_000 + manifest_index,
                "warmup": True,
            }
        )
        for sentence_index, item in enumerate(random_items[:sentence_count], start=1):
            text = str(item.get("text") or "").strip()
            if not text:
                raise ValueError(f"Manifest case {slug}_random_{sentence_index:02d} has empty text.")
            seed = BASE_SEED + manifest_index * 100 + sentence_index
            for repeat in range(1, repeats + 1):
                measurements.append(
                    {
                        "case_id": f"{slug}_random_{sentence_index:02d}",
                        "call_id": f"{slug}_random_{sentence_index:02d}_r{repeat}",
                        "language_slug": slug,
                        "language": language,
                        "sentence_index": sentence_index,
                        "repeat": repeat,
                        "text": text,
                        "seed": seed,
                        "warmup": False,
                    }
                )
    if not selected:
        requested = ", ".join(sorted(language_filter or [])) or "all"
        raise ValueError(f"No judge-supported manifest languages matched: {requested}")
    return warmups, measurements


def resolved_asr_language(language: str, supported_languages: set[str]) -> str | None:
    candidate = "Arabic" if language.casefold() in ARABIC_LANGUAGE_NAMES else language
    supported_by_casefold = {item.casefold(): item for item in supported_languages}
    return supported_by_casefold.get(candidate.casefold())


def generate_audio(
    tts_url: str,
    item: dict[str, Any],
    reference_audio: str,
    reference_text: str,
    num_step: int,
) -> tuple[bytes, dict[str, str], float]:
    payload = {
        "text": item["text"],
        "language": item["language"],
        "ref_audio": reference_audio,
        "ref_text": reference_text,
        "cache_voice_prompt": True,
        "output_format": "wav",
        "seed": item["seed"],
        "randomize_seed": False,
        "num_step": num_step,
        "speed": 1.0,
        "pad_duration": 0.1,
        "fade_duration": 0.1,
    }
    request = urllib.request.Request(
        f"{tts_url}/tts/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        audio = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
    elapsed = time.perf_counter() - started
    if len(audio) < 1_000:
        raise RuntimeError(f"TTS returned only {len(audio)} bytes.")
    return audio, headers, elapsed


def multipart_body(audio: bytes, language: str | None, filename: str) -> tuple[bytes, str]:
    boundary = f"----OmniVoiceTTSQuality{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )

    add_field("model", "qwen3-asr")
    add_field("response_format", "verbose_json")
    add_field("temperature", "0")
    if language:
        add_field("language", language)
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}.wav"\r\n'.encode(),
            b"Content-Type: audio/wav\r\n\r\n",
            audio,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts), boundary


def transcribe_audio(
    asr_url: str,
    audio: bytes,
    language: str | None,
    filename: str,
) -> tuple[dict[str, Any], float]:
    body, boundary = multipart_body(audio, language, filename)
    request = urllib.request.Request(
        f"{asr_url}/v1/audio/transcriptions",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload, time.perf_counter() - started


def wav_duration(audio: bytes) -> float:
    with wave.open(io.BytesIO(audio), "rb") as source:
        return source.getnframes() / source.getframerate()


def gpu_snapshot(gpu_index: int) -> dict[str, Any] | None:
    command = [
        "nvidia-smi",
        f"--id={gpu_index}",
        "--query-gpu=index,name,driver_version,memory.total,memory.used",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=True)
        line = next(line for line in result.stdout.splitlines() if line.strip())
        index, name, driver, total, used = (part.strip() for part in line.split(",", 4))
        return {
            "index": int(index),
            "name": name,
            "driver": driver,
            "total_mib": int(total),
            "used_mib": int(used),
        }
    except (FileNotFoundError, StopIteration, subprocess.SubprocessError, ValueError):
        return None


def write_artifact(artifacts_dir: Path, run_id: str, item: dict[str, Any], audio: bytes) -> str:
    output = artifacts_dir / run_id / f"{item.get('call_id', item['case_id'])}.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio)
    return str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output)


def generate_call(
    *,
    tts_url: str,
    item: dict[str, Any],
    reference_audio: str,
    reference_text: str,
    num_step: int,
    supported_languages: set[str],
    gpu_index: int,
    artifacts_dir: Path,
    run_id: str,
    staging_dir: Path,
) -> dict[str, Any]:
    result = {**item}
    asr_language = resolved_asr_language(item["language"], supported_languages)
    result["asr_forced_language"] = asr_language
    result["asr_judge_language_supported"] = asr_language is not None
    try:
        audio, headers, tts_seconds = generate_audio(
            tts_url,
            item,
            reference_audio,
            reference_text,
            num_step,
        )
    except Exception as exc:
        result.update(
            {
                "error_stage": "tts",
                "error": f"{type(exc).__name__}: {exc}",
                "gpu": gpu_snapshot(gpu_index),
            }
        )
        return result

    try:
        audio_seconds = wav_duration(audio)
    except Exception as exc:
        result.update(
            {
                "error_stage": "audio",
                "error": f"{type(exc).__name__}: {exc}",
                "tts_seconds": round(tts_seconds, 3),
                "bytes": len(audio),
                "sha256": hashlib.sha256(audio).hexdigest(),
                "artifact": write_artifact(artifacts_dir, run_id, item, audio),
                "gpu": gpu_snapshot(gpu_index),
            }
        )
        return result
    result.update(
        {
            "tts_seconds": round(tts_seconds, 3),
            "audio_seconds": round(audio_seconds, 3),
            "bytes": len(audio),
            "sha256": hashlib.sha256(audio).hexdigest(),
            "response_seed": headers.get("x-omnivoicetts-seed"),
        }
    )
    staged_audio = staging_dir / f"{item.get('call_id', item['case_id'])}.wav"
    staged_audio.parent.mkdir(parents=True, exist_ok=True)
    staged_audio.write_bytes(audio)
    result["staged_audio"] = str(staged_audio)
    result["gpu_after_tts"] = gpu_snapshot(gpu_index)
    return result


def transcribe_call(
    *,
    asr_url: str,
    result: dict[str, Any],
    artifacts_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    if result.get("error"):
        return result
    audio = Path(result["staged_audio"]).read_bytes()
    try:
        asr_payload, asr_seconds = transcribe_audio(
            asr_url,
            audio,
            result.get("asr_forced_language"),
            result.get("call_id", result["case_id"]),
        )
    except Exception as exc:
        result.update(
            {
                "error_stage": "asr",
                "error": f"{type(exc).__name__}: {exc}",
                "artifact": write_artifact(artifacts_dir, run_id, result, audio),
            }
        )
        result.pop("staged_audio", None)
        return result

    transcript = str(asr_payload.get("text") or "").strip()
    expected_normalized = normalize_transcript(result["text"])
    transcript_normalized = normalize_transcript(transcript)
    exact = expected_normalized == transcript_normalized
    result.update(
        {
            "transcript": transcript,
            "detected_language": asr_payload.get("language"),
            "asr_seconds": round(asr_seconds, 3),
            "expected_normalized": expected_normalized,
            "transcript_normalized": transcript_normalized,
            "exact": exact,
            "similarity_percent": transcript_similarity(result["text"], transcript),
            "real_time_factor": round(result["tts_seconds"] / result["audio_seconds"], 4)
            if result["audio_seconds"]
            else None,
        }
    )
    if not exact:
        result["artifact"] = write_artifact(artifacts_dir, run_id, result, audio)
    result.pop("staged_audio", None)
    return result


def summarize_calls(measurements: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [item for item in measurements if not item.get("error")]
    tts_times = [float(item["tts_seconds"]) for item in successful]
    asr_times = [float(item["asr_seconds"]) for item in successful]
    audio_times = [float(item["audio_seconds"]) for item in successful]
    similarities = [float(item["similarity_percent"]) for item in successful]
    exact = sum(bool(item.get("exact")) for item in successful)
    total_audio = sum(audio_times)
    total_tts = sum(tts_times)
    return {
        "calls": len(measurements),
        "completed": len(successful),
        "request_errors": len(measurements) - len(successful),
        "exact": exact,
        "exact_percent": round(100.0 * exact / len(successful), 2) if successful else 0.0,
        "mean_similarity_percent": round(statistics.fmean(similarities), 2) if similarities else 0.0,
        "min_similarity_percent": round(min(similarities), 2) if similarities else 0.0,
        "total_tts_seconds": round(total_tts, 3),
        "mean_tts_seconds": round(statistics.fmean(tts_times), 3) if tts_times else 0.0,
        "p95_tts_seconds": round(percentile(tts_times, 95), 3),
        "total_asr_seconds": round(sum(asr_times), 3),
        "mean_asr_seconds": round(statistics.fmean(asr_times), 3) if asr_times else 0.0,
        "audio_seconds": round(total_audio, 3),
        "tts_real_time_factor": round(total_tts / total_audio, 4) if total_audio else 0.0,
        "tts_realtime_speed": round(total_audio / total_tts, 2) if total_tts else 0.0,
    }


def summarize_cases(measurements: list[dict[str, Any]], repeats: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in measurements:
        grouped[item["case_id"]].append(item)
    summaries = []
    for case_id, calls in grouped.items():
        successful = [item for item in calls if not item.get("error")]
        transcript_counts = Counter(item.get("transcript_normalized", "") for item in successful)
        display_transcripts = Counter(item.get("transcript", "") for item in successful)
        similarities = [float(item["similarity_percent"]) for item in successful]
        first = calls[0]
        summaries.append(
            {
                "case_id": case_id,
                "language_slug": first["language_slug"],
                "language": first["language"],
                "sentence_index": first["sentence_index"],
                "expected": first["text"],
                "calls": len(calls),
                "completed": len(successful),
                "errors": len(calls) - len(successful),
                "exact_repeats": sum(bool(item.get("exact")) for item in successful),
                "consistent": len(successful) == repeats and len(transcript_counts) == 1,
                "unique_normalized_transcripts": len(transcript_counts),
                "mean_similarity_percent": round(statistics.fmean(similarities), 2) if similarities else 0.0,
                "min_similarity_percent": round(min(similarities), 2) if similarities else 0.0,
                "transcripts": [
                    {"count": count, "text": transcript}
                    for transcript, count in display_transcripts.most_common()
                ],
            }
        )
    return summaries


def summarize_languages(
    measurements: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped_calls: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in measurements:
        grouped_calls[item["language_slug"]].append(item)
    for item in case_summaries:
        grouped_cases[item["language_slug"]].append(item)
    rows = []
    for slug, calls in grouped_calls.items():
        call_summary = summarize_calls(calls)
        cases = grouped_cases[slug]
        first = calls[0]
        rows.append(
            {
                "language_slug": slug,
                "language": first["language"],
                "judge_supported": bool(first.get("asr_judge_language_supported")),
                **call_summary,
                "consistent_cases": sum(bool(item["consistent"]) for item in cases),
                "cases": len(cases),
            }
        )
    return rows


def append_json(path: Path, run: dict[str, Any]) -> None:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema": 1, "runs": []}
    data.setdefault("runs", []).append(run)
    data["latest"] = run
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        temporary = Path(file.name)
    temporary.replace(path)


def markdown_label(run: dict[str, Any]) -> str:
    timestamp = datetime.fromisoformat(run["started_at"]).astimezone()
    return f"{timestamp:%d.%m.%Y %H:%M:%S} - {run['tts']['version']}"


def markdown_text(value: Any) -> str:
    return str(value).replace("|", "/").replace("\r", " ").replace("\n", " ").replace("`", "'")


def insert_summary_row(path: Path, row: str) -> None:
    existing = path.read_text(encoding="utf-8")
    if SUMMARY_ROWS_MARKER not in existing:
        raise ValueError(f"Summary row marker missing from {path}: {SUMMARY_ROWS_MARKER}")
    path.write_text(existing.replace(SUMMARY_ROWS_MARKER, row + SUMMARY_ROWS_MARKER, 1), encoding="utf-8")


def append_summary_markdown(path: Path, run: dict[str, Any]) -> None:
    summary = run["summary"]
    gpu = run["vram"].get("gpu") or {}
    hardware = f"{gpu.get('name', 'CPU/unknown')} ({gpu.get('total_mib', '?')} MiB)"
    peak = run["vram"].get("tts_phase_peak_observed_used_mib")
    tts_peak = (run["vram"].get("tts_pytorch_after_benchmark") or {}).get("max_allocated_mib")
    row = (
        f"| {markdown_label(run)} | {markdown_text(run['asr']['model'])} | {markdown_text(hardware)} | "
        f"{summary['languages']} | {summary['calls']} | {summary['exact_percent']:.2f}% | "
        f"{summary['consistent_case_percent']:.2f}% | {summary['mean_similarity_percent']:.2f}% | "
        f"{summary['total_tts_seconds']:.3f} | {summary['mean_tts_seconds']:.3f} | "
        f"{summary['p95_tts_seconds']:.3f} | {summary['tts_real_time_factor']:.4f} | "
        f"{summary['mean_asr_seconds']:.3f} | {tts_peak if tts_peak is not None else 'n/a'} | "
        f"{peak if peak is not None else 'n/a'} | "
        f"{summary['request_errors']} |\n"
    )
    insert_summary_row(path, row)


def append_details_markdown(path: Path, run: dict[str, Any]) -> None:
    summary = run["summary"]
    lines = [
        "",
        f"## {markdown_label(run)}",
        "",
        f"- TTS build: `{markdown_text(run['tts']['build_id'])}`",
        f"- ASR model: `{markdown_text(run['asr']['model'])}`",
        f"- Workload: `{summary['languages']}` languages, `{run['config']['sentences_per_language']}` sentences per language, `{run['config']['repeats']}` repeats",
        f"- Measured calls: `{summary['completed']}/{summary['calls']}` completed",
        f"- Exact normalized transcripts: `{summary['exact_percent']:.2f}%`",
        f"- Repeat-consistent sentence cases: `{summary['consistent_cases']}/{summary['cases']}` (`{summary['consistent_case_percent']:.2f}%`)",
        f"- Mean normalized character similarity: `{summary['mean_similarity_percent']:.2f}%`",
        f"- Measured TTS time: `{summary['total_tts_seconds']:.3f}s`; RTF `{summary['tts_real_time_factor']:.4f}` (`{summary['tts_realtime_speed']:.2f}x` realtime)",
        f"- Benchmark wall time including ASR and diagnostics: `{summary['wall_seconds']:.3f}s`",
        f"- TTS PyTorch peak allocated / reserved: `{(run['vram'].get('tts_pytorch_after_benchmark') or {}).get('max_allocated_mib', 'n/a')} MiB / {(run['vram'].get('tts_pytorch_after_benchmark') or {}).get('max_reserved_mib', 'n/a')} MiB`",
        f"- Peak observed whole-device VRAM during the TTS phase: `{run['vram'].get('tts_phase_peak_observed_used_mib', 'n/a')} MiB` (diagnostic only; use the dedicated GPU-memory suite for clean TTS VRAM)",
        f"- ASR baseline after warmup / endpoint after final keepalive: `{(run['vram'].get('asr_baseline_after_warmup') or {}).get('used_mib', 'n/a')} MiB / {(run['vram'].get('asr_endpoint_after_keepalive') or {}).get('used_mib', 'n/a')} MiB`",
        f"- Retained non-exact/error WAV files: `{markdown_text(run['artifacts_dir'])}` (local, git-ignored)",
        f"- Comment: {markdown_text(run.get('comment') or 'None')}",
        "",
        "### Languages",
        "",
        "| Language | Qwen judge | Exact | Consistent cases | Mean similarity | Avg TTS | P95 TTS | RTF | Errors |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for language in run["language_summaries"]:
        judge = "forced" if language["judge_supported"] else "auto (unsupported)"
        lines.append(
            f"| {markdown_text(language['language'])} | {judge} | {language['exact']}/{language['completed']} | "
            f"{language['consistent_cases']}/{language['cases']} | {language['mean_similarity_percent']:.2f}% | "
            f"{language['mean_tts_seconds']:.3f}s | {language['p95_tts_seconds']:.3f}s | "
            f"{language['tts_real_time_factor']:.4f} | {language['request_errors']} |"
        )

    errors = [item for item in [*run["warmups"], *run["measurements"]] if item.get("error")]
    lines.extend(["", "### Request Errors", ""])
    if errors:
        for item in errors:
            lines.append(
                f"- `{markdown_text(item.get('call_id', item['case_id']))}` ({item['error_stage']}): "
                f"{markdown_text(item['error'])}"
            )
    else:
        lines.append("No TTS or ASR request errors were recorded.")

    warmup_observations = [item for item in run["warmups"] if item.get("error") or item.get("exact") is False]
    lines.extend(["", "### Warmup Observations", ""])
    if warmup_observations:
        for item in warmup_observations:
            if item.get("error"):
                lines.append(f"- `{item['case_id']}` failed: {markdown_text(item['error'])}")
            else:
                lines.append(
                    f"- `{item['case_id']}` scored `{item['similarity_percent']:.2f}%`: "
                    f"{markdown_text(item.get('transcript', ''))}"
                )
    else:
        lines.append("All warmup transcriptions matched after normalization.")

    problematic_cases = [
        item
        for item in run["case_summaries"]
        if item["errors"] or item["exact_repeats"] != run["config"]["repeats"] or not item["consistent"]
    ]
    lines.extend(["", "### Mismatches And Inconsistent Cases", ""])
    if not problematic_cases:
        lines.append("All measured sentence cases matched and remained repeat-consistent.")
    for case in problematic_cases:
        lines.extend(
            [
                f"#### {case['case_id']}",
                "",
                f"- Expected: {markdown_text(case['expected'])}",
                f"- Exact repeats: `{case['exact_repeats']}/{run['config']['repeats']}`",
                f"- Repeat consistent: `{'yes' if case['consistent'] else 'no'}`",
                f"- Mean / minimum similarity: `{case['mean_similarity_percent']:.2f}% / {case['min_similarity_percent']:.2f}%`",
            ]
        )
        for transcript in case["transcripts"]:
            lines.append(f"- Transcript (`{transcript['count']}x`): {markdown_text(transcript['text'])}")
        lines.append("")

    lines.append("")
    hardest = [item for item in run["measurements"] if not item.get("error")]
    hardest.sort(key=lambda item: (item["similarity_percent"], item["call_id"]))
    lines.extend(["### Hardest ASR-Judged Calls", ""])
    for item in hardest[:10]:
        lines.append(
            f"- `{item['call_id']}` - `{item['similarity_percent']:.2f}%` - expected: "
            f"{markdown_text(item['text'])} - transcript: {markdown_text(item['transcript'])}"
        )
    content = "\n".join(lines).strip("\n")
    existing = path.read_text(encoding="utf-8").rstrip("\n")
    path.write_text(existing + "\n\n" + content + "\n", encoding="utf-8")


def runtime_tts_payload(status: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "version",
        "package_version",
        "build_id",
        "runtime",
        "resolved_device",
        "model",
        "sample_rate",
        "resample_backend",
        "max_concurrent_generations",
        "loaded_model_devices",
        "voice_prompt_cache",
        "cuda_memory",
    )
    return {key: status.get(key) for key in keys}


def collect_peak_vram(snapshots: list[dict[str, Any] | None]) -> int | None:
    values = [int(snapshot["used_mib"]) for snapshot in snapshots if snapshot and snapshot.get("used_mib") is not None]
    return max(values) if values else None


def tts_cuda_memory(status: dict[str, Any], gpu_index: int) -> dict[str, Any] | None:
    expected_device = f"cuda:{gpu_index}"
    for item in status.get("cuda_memory") or []:
        if item.get("device") == expected_device:
            return {
                **item,
                "allocated_mib": round(float(item.get("allocated", 0)) / (1024 * 1024), 1),
                "reserved_mib": round(float(item.get("reserved", 0)) / (1024 * 1024), 1),
                "max_allocated_mib": round(float(item.get("max_allocated", 0)) / (1024 * 1024), 1),
                "max_reserved_mib": round(float(item.get("max_reserved", 0)) / (1024 * 1024), 1),
            }
    return None


def ensure_output_documents(summary_path: Path, details_path: Path) -> None:
    if not summary_path.exists() or not details_path.exists():
        raise FileNotFoundError(
            "Benchmark Markdown templates are missing. Expected "
            f"{summary_path} and {details_path}."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark multilingual OmniVoiceTTS generation quality through a fixed local Qwen3-ASR judge."
    )
    parser.add_argument("--tts-url", default=DEFAULT_TTS_URL)
    parser.add_argument("--asr-url", default=DEFAULT_ASR_URL)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--reference-audio", default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--reference-text", default=DEFAULT_REFERENCE_TEXT)
    parser.add_argument("--sentences", type=int, default=DEFAULT_SENTENCES)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--num-step", type=int, default=DEFAULT_NUM_STEP)
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--comment", default="")
    parser.add_argument(
        "--languages",
        default="",
        help="Optional comma-separated language names or slugs for a development smoke run.",
    )
    parser.add_argument("--skip-warmup", action="store_true")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Run the workload without appending official JSON or Markdown history.",
    )
    args = parser.parse_args()

    if not args.no_write:
        ensure_output_documents(args.summary, args.details)
    language_filter = parse_language_filter(args.languages)
    wait_ready(args.tts_url, args.asr_url)
    tts_cache_clear = request_json(
        "POST",
        f"{args.tts_url}/tts/cache/clear",
        {"reset_peak_stats": True},
    )
    tts_status_before = request_json("GET", f"{args.tts_url}/tts/status")
    asr_health = request_json("GET", f"{args.asr_url}/health/ready")
    asr_models = request_json("GET", f"{args.asr_url}/v1/models").get("data", [])
    supported_languages = set(
        request_json("GET", f"{args.asr_url}/v1/audio/supported_languages").get("languages", [])
    )
    warmup_workload, measured_workload = load_workload(
        args.manifest,
        args.sentences,
        args.repeats,
        supported_languages,
        language_filter or None,
    )
    if args.skip_warmup:
        warmup_workload = []
    run_id = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    started_at = now_iso()
    started = time.perf_counter()
    tts_phase_baseline_gpu = gpu_snapshot(args.gpu_index)
    tts_snapshots: list[dict[str, Any] | None] = [tts_phase_baseline_gpu]

    total_calls = len(warmup_workload) + len(measured_workload)
    language_count = len({item["language_slug"] for item in measured_workload})
    print(
        f"Speech-quality benchmark: {language_count} languages, {len(warmup_workload)} warmups, "
        f"{len(measured_workload)} measured calls ({args.sentences} sentences x {args.repeats} repeats).",
        flush=True,
    )

    warmups: list[dict[str, Any]] = []
    measurements: list[dict[str, Any]] = []
    progress = 0
    total_phase_calls = total_calls * 2 + (1 if total_calls else 0)
    measured_tts_seconds = 0.0
    measured_asr_seconds = 0.0
    asr_keepalive: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(prefix="omnivoicetts-quality-") as staging_root:
        staging_dir = Path(staging_root)
        print("Phase 1/2: generating every TTS WAV before ASR transcription begins.", flush=True)
        for item in warmup_workload:
            progress += 1
            result = generate_call(
                tts_url=args.tts_url,
                item=item,
                reference_audio=args.reference_audio,
                reference_text=args.reference_text,
                num_step=args.num_step,
                supported_languages=supported_languages,
                gpu_index=args.gpu_index,
                artifacts_dir=args.artifacts_dir,
                run_id=run_id,
                staging_dir=staging_dir,
            )
            warmups.append(result)
            tts_snapshots.append(result.get("gpu_after_tts") or result.get("gpu"))
            print(
                f"[{progress:03d}/{total_phase_calls:03d}] TTS warmup {item['language_slug']}: "
                f"{'ERROR' if result.get('error') else 'OK'} {result.get('tts_seconds', 0):.3f}s",
                flush=True,
            )

        post_tts_warmup_gpu = gpu_snapshot(args.gpu_index)
        tts_snapshots.append(post_tts_warmup_gpu)
        measured_tts_started = time.perf_counter()
        for item in measured_workload:
            progress += 1
            result = generate_call(
                tts_url=args.tts_url,
                item=item,
                reference_audio=args.reference_audio,
                reference_text=args.reference_text,
                num_step=args.num_step,
                supported_languages=supported_languages,
                gpu_index=args.gpu_index,
                artifacts_dir=args.artifacts_dir,
                run_id=run_id,
                staging_dir=staging_dir,
            )
            measurements.append(result)
            tts_snapshots.append(result.get("gpu_after_tts") or result.get("gpu"))
            print(
                f"[{progress:03d}/{total_phase_calls:03d}] TTS {item['call_id']}: "
                f"{'ERROR' if result.get('error') else 'OK'} {result.get('tts_seconds', 0):.3f}s",
                flush=True,
            )
        measured_tts_seconds = time.perf_counter() - measured_tts_started
        tts_phase_final_gpu = gpu_snapshot(args.gpu_index)
        tts_snapshots.append(tts_phase_final_gpu)

        keepalive_source = next(
            (item for item in [*warmups, *measurements] if not item.get("error") and item.get("staged_audio")),
            None,
        )
        keepalive_audio = Path(keepalive_source["staged_audio"]).read_bytes() if keepalive_source else None

        print("Phase 2/2: warming and measuring Qwen3-ASR from staged WAV files.", flush=True)
        for result in warmups:
            progress += 1
            transcribe_call(asr_url=args.asr_url, result=result, artifacts_dir=args.artifacts_dir, run_id=run_id)
            outcome = "ERROR" if result.get("error") else ("MATCH" if result.get("exact") else "DIFF")
            print(
                f"[{progress:03d}/{total_phase_calls:03d}] ASR warmup {result['language_slug']}: "
                f"{outcome} {result.get('asr_seconds', 0):.3f}s",
                flush=True,
            )

        asr_baseline_after_warmup = gpu_snapshot(args.gpu_index)
        measured_asr_started = time.perf_counter()
        for result in measurements:
            progress += 1
            transcribe_call(asr_url=args.asr_url, result=result, artifacts_dir=args.artifacts_dir, run_id=run_id)
            outcome = "ERROR" if result.get("error") else ("MATCH" if result.get("exact") else "DIFF")
            print(
                f"[{progress:03d}/{total_phase_calls:03d}] ASR {result['call_id']}: {outcome} "
                f"score={result.get('similarity_percent', 0):.2f}% {result.get('asr_seconds', 0):.3f}s",
                flush=True,
            )
        measured_asr_seconds = time.perf_counter() - measured_asr_started

        if keepalive_audio is not None and keepalive_source is not None:
            progress += 1
            keepalive_payload, keepalive_seconds = transcribe_audio(
                args.asr_url,
                keepalive_audio,
                keepalive_source.get("asr_forced_language"),
                "final-asr-keepalive",
            )
            asr_keepalive = {
                "seconds": round(keepalive_seconds, 3),
                "transcript": str(keepalive_payload.get("text") or "").strip(),
            }
            print(
                f"[{progress:03d}/{total_phase_calls:03d}] ASR final keepalive: {keepalive_seconds:.3f}s",
                flush=True,
            )
        asr_endpoint_after_keepalive = gpu_snapshot(args.gpu_index)

    tts_status_after = request_json("GET", f"{args.tts_url}/tts/status")
    case_summaries = summarize_cases(measurements, args.repeats)
    language_summaries = summarize_languages(measurements, case_summaries)
    summary = summarize_calls(measurements)
    summary.update(
        {
            "languages": language_count,
            "cases": len(case_summaries),
            "consistent_cases": sum(bool(item["consistent"]) for item in case_summaries),
            "consistent_case_percent": round(
                100.0 * sum(bool(item["consistent"]) for item in case_summaries) / len(case_summaries), 2
            )
            if case_summaries
            else 0.0,
            "measured_tts_phase_seconds": round(measured_tts_seconds, 3),
            "measured_asr_phase_seconds": round(measured_asr_seconds, 3),
            "measured_wall_seconds": round(measured_tts_seconds + measured_asr_seconds, 3),
            "wall_seconds": round(time.perf_counter() - started, 3),
        }
    )
    asr_model = str(asr_models[0].get("id")) if asr_models else str(asr_health.get("model") or "unknown")
    run = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": now_iso(),
        "config": {
            "manifest": str(args.manifest),
            "tts_url": args.tts_url,
            "asr_url": args.asr_url,
            "sentences_per_language": args.sentences,
            "repeats": args.repeats,
            "num_step": args.num_step,
            "seed_policy": f"fixed per sentence from base {BASE_SEED}; identical across repeats",
            "voice_policy": "baked reference audio + known transcript + cached clone prompt",
            "reference_audio": args.reference_audio,
            "reference_text": args.reference_text,
            "language_filter": sorted(language_filter),
            "warmup": not args.skip_warmup,
        },
        "tts": {
            **runtime_tts_payload(tts_status_before),
            "status_after": runtime_tts_payload(tts_status_after),
        },
        "asr": {
            "model": asr_model,
            "models": asr_models,
            "health": asr_health,
            "supported_languages": sorted(supported_languages),
            "role": "fixed comparative judge; not ground truth",
        },
        "vram": {
            "gpu": tts_phase_baseline_gpu or tts_phase_final_gpu,
            "tts_phase_baseline": tts_phase_baseline_gpu,
            "tts_phase_post_warmup": post_tts_warmup_gpu,
            "tts_phase_final": tts_phase_final_gpu,
            "tts_phase_peak_observed_used_mib": collect_peak_vram(tts_snapshots),
            "asr_baseline_after_warmup": asr_baseline_after_warmup,
            "asr_endpoint_after_keepalive": asr_endpoint_after_keepalive,
            "asr_final_keepalive": asr_keepalive,
            "tts_cache_clear_before_warmup": tts_cache_clear,
            "tts_pytorch_before_warmup": tts_cuda_memory(tts_status_before, args.gpu_index),
            "tts_pytorch_after_benchmark": tts_cuda_memory(tts_status_after, args.gpu_index),
            "scope": (
                "TTS generation and ASR transcription run in separate phases. TTS snapshots still include the "
                "resident ASR process and Windows GPU consumers; benchmarks/memory/gpu is authoritative for clean TTS VRAM."
            ),
        },
        "artifacts_dir": str(args.artifacts_dir / run_id),
        "comment": args.comment,
        "summary": summary,
        "language_summaries": language_summaries,
        "case_summaries": case_summaries,
        "warmups": warmups,
        "measurements": measurements,
    }
    if not args.no_write:
        append_json(args.results, run)
        append_summary_markdown(args.summary, run)
        append_details_markdown(args.details, run)
    print(
        f"Completed {summary['completed']}/{summary['calls']} measured calls; "
        f"exact={summary['exact_percent']:.2f}%, consistency={summary['consistent_case_percent']:.2f}%, "
        f"similarity={summary['mean_similarity_percent']:.2f}%. "
        + (f"Results: {args.results}" if not args.no_write else "No official results were written."),
        flush=True,
    )
    if summary["request_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
