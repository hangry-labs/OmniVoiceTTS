from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.request
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TTS_URL = os.getenv("OMNIVOICE_SSML_H_BENCHMARK_TTS_URL", "http://127.0.0.1:7861")
DEFAULT_ASR_URL = os.getenv("OMNIVOICE_SSML_H_BENCHMARK_ASR_URL", "http://127.0.0.1:8000")
DEFAULT_CALLS = int(os.getenv("OMNIVOICE_SSML_H_BENCHMARK_CALLS", "20"))
DEFAULT_RESULTS = ROOT / "benchmarks" / "ssml" / "runs.json"
DEFAULT_MARKDOWN = ROOT / "benchmarks" / "ssml" / "BENCHMARKS.md"
DEFAULT_DETAILS = ROOT / "benchmarks" / "ssml" / "DETAILS.md"
EXPECTED_TEXT = "Are we ready? Yes, all preparations are complete."
EXPECTED_WORDS = ("are", "we", "ready", "yes", "all", "preparations", "are", "complete")
POLICY_LABEL = "fixed internal sample + stable contiguous prosody turn + bounded retry"
KNOWN_PRE_FIX_FAILURE_SEED = 2_717_518_076
FIXED_SEEDS = (
    KNOWN_PRE_FIX_FAILURE_SEED,
    2_717_518_077,
    2_717_518_078,
    412_095_174,
    3_888_510_638,
    1_485_887_814,
    2_163_181_999,
    3_432_834_366,
    1_257_281_928,
    3_509_819_213,
    992_516_492,
    2_908_409_029,
    1_816_140_917,
    3_707_527_105,
    635_817_482,
    2_342_177_711,
    1_074_398_955,
    3_146_820_204,
    1_593_680_337,
    2_593_145_086,
)
SSML_H_SAMPLE = """<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0" xml:lang="en-US">
  <metadata>
    <h:extensions version="1.0">
      <h:voice-definition name="Bob" gender="male" age="elderly" accent="american" scope="request" seed="4242">
        <h:sample xml:lang="en-US">My name is Bob. I am ready for this conversation.</h:sample>
      </h:voice-definition>
      <h:voice-definition name="Elisabeth" gender="female" age="elderly" accent="american" scope="request" seed="8241"/>
    </h:extensions>
  </metadata>
  <voice name="Bob">Are we ready?</voice>
  <break time="300ms"/>
  <voice name="Elisabeth"><prosody rate="slow">Yes, all preparations are complete.</prosody></voice>
</speak>"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_json(url: str, timeout: int = 30) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(tts_url: str, asr_url: str) -> None:
    deadline = time.monotonic() + 240
    pending = {"TTS": f"{tts_url}/tts/ping", "ASR": f"{asr_url}/health/ready"}
    while pending and time.monotonic() < deadline:
        for name, url in list(pending.items()):
            try:
                request_json(url, timeout=5)
                del pending[name]
            except Exception:
                pass
        if pending:
            time.sleep(2)
    if pending:
        raise RuntimeError(f"Services did not become ready: {', '.join(pending)}")


def generate_audio(tts_url: str, seed: int) -> tuple[bytes, dict[str, str], float]:
    payload = {
        "input_type": "ssml-h",
        "text": SSML_H_SAMPLE,
        "language": "English",
        "output_format": "wav",
        "seed": seed,
        "randomize_seed": False,
        "num_step": 32,
        "speed": 1.0,
        "pad_duration": 0.1,
        "fade_duration": 0.1,
    }
    request = urllib.request.Request(
        f"{tts_url}/tts/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        audio = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
    elapsed = time.perf_counter() - started
    if len(audio) < 1_000:
        raise RuntimeError(f"TTS returned only {len(audio)} bytes for seed {seed}.")
    return audio, headers, elapsed


def multipart_body(audio: bytes) -> tuple[bytes, str]:
    boundary = f"----OmniVoiceTTSBenchmark{uuid.uuid4().hex}"
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
    add_field("language", "en")
    add_field("response_format", "json")
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="ssml-h-reliability.wav"\r\n',
            b"Content-Type: audio/wav\r\n\r\n",
            audio,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts), boundary


def transcribe_audio(asr_url: str, audio: bytes) -> tuple[str, float]:
    body, boundary = multipart_body(audio)
    request = urllib.request.Request(
        f"{asr_url}/v1/audio/transcriptions",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("text", "")).strip(), time.perf_counter() - started


def wav_duration(audio: bytes) -> float:
    with wave.open(io.BytesIO(audio), "rb") as source:
        return source.getnframes() / source.getframerate()


def normalized_words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.casefold()))


def is_complete(transcript: str) -> bool:
    return normalized_words(transcript) == EXPECTED_WORDS


def seeds_for_calls(calls: int) -> list[int]:
    if calls < 1:
        raise ValueError("--calls must be at least 1")
    return [FIXED_SEEDS[index % len(FIXED_SEEDS)] for index in range(calls)]


def generate_call(tts_url: str, seed: int, staging_dir: Path) -> dict[str, Any]:
    audio, headers, tts_seconds = generate_audio(tts_url, seed)
    staged_audio = staging_dir / f"{seed}.wav"
    staged_audio.write_bytes(audio)
    return {
        "seed": seed,
        "tts_seconds": round(tts_seconds, 3),
        "audio_seconds": round(wav_duration(audio), 3),
        "bytes": len(audio),
        "sha256": hashlib.sha256(audio).hexdigest(),
        "response_seed": headers.get("x-omnivoicetts-seed"),
        "staged_audio": str(staged_audio),
    }


def transcribe_call(asr_url: str, result: dict[str, Any]) -> dict[str, Any]:
    transcript, asr_seconds = transcribe_audio(asr_url, Path(result["staged_audio"]).read_bytes())
    result.update(
        {
            "passed": is_complete(transcript),
            "transcript": transcript,
            "asr_seconds": round(asr_seconds, 3),
        }
    )
    result.pop("staged_audio", None)
    return result


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
    return f"{timestamp:%d.%m.%Y %H:%M:%S} - {run['tts_version']}"


def append_markdown(path: Path, run: dict[str, Any]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            """# ssml_h_reliability

End-to-end dialogue-completion benchmark for SSML-H dynamic voices. It generates the exact two-character sample included in the browser UI, transcribes each WAV through the local Qwen3-ASR service, and requires the normalized transcript to match `Are we ready? Yes, all preparations are complete.` exactly.

The workload uses one full TTS-to-ASR warmup followed by deterministic fixed seeds. Seed `2717518076` is retained as the first measured case because it reproducibly omitted Elisabeth's final sentence when an omitted `h:sample` was derived from dialogue text. A pre-fix diagnostic probe completed 7 of 8 calls (87.5%); the separately captured failure artifact ended at `Yes, everything.`. Current behavior uses one fixed internal reference sentence whenever `h:sample` is omitted, so dialogue content never becomes voice-training material. The browser sample keeps Elisabeth's complete reply inside one prosody scope to avoid splitting a short turn into separate model generations.

This is a semantic completion regression benchmark, not a voice-quality score. ASR can occasionally make recognition errors, so every failed row must be inspected using the detailed transcript and audio hash in `runs.json` and `DETAILS.md`.

| Run | Hardware | Calls | Policy | Passed | Completion | Total seconds | Avg TTS | Avg ASR | Min bytes | Max bytes | ASR model |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
""",
            encoding="utf-8",
        )
    summary = run["summary"]
    row = (
        f"| {markdown_label(run)} | {run['hardware'].replace('|', '/')} | {summary['calls']} | "
        f"{run['policy'].replace('|', '/')} | {summary['passed']} | {summary['completion_percent']:.1f}% | {summary['total_seconds']:.3f} | "
        f"{summary['avg_tts_seconds']:.3f} | {summary['avg_asr_seconds']:.3f} | "
        f"{summary['min_bytes']} | {summary['max_bytes']} | {run['asr_model'].replace('|', '/')} |\n"
    )
    existing = path.read_text(encoding="utf-8").rstrip("\n")
    path.write_text(existing + "\n" + row, encoding="utf-8")


def append_details(path: Path, run: dict[str, Any]) -> None:
    lines = [
        "",
        f"## {markdown_label(run)}",
        "",
        f"- Hardware: `{run['hardware']}`",
        f"- Policy: {run['policy']}",
        f"- Expected transcript: `{run['expected_text']}`",
        f"- Warmup transcript: `{run['warmup']['transcript']}`",
        f"- Comment: {run.get('comment') or 'None'}",
        "",
        "| Call | Seed | Result | TTS seconds | ASR seconds | Audio seconds | Bytes | Transcript | SHA-256 |",
        "|---:|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for index, measurement in enumerate(run["measurements"], start=1):
        transcript = str(measurement["transcript"]).replace("|", "/").replace("\n", " ")
        lines.append(
            f"| {index} | {measurement['seed']} | {'pass' if measurement['passed'] else 'FAIL'} | "
            f"{measurement['tts_seconds']:.3f} | {measurement['asr_seconds']:.3f} | "
            f"{measurement['audio_seconds']:.3f} | {measurement['bytes']} | {transcript} | "
            f"`{measurement['sha256']}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").rstrip("\n") if path.exists() else "# SSML-H Reliability Details"
    path.write_text(existing + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SSML-H dynamic-dialogue completion through local TTS and ASR.")
    parser.add_argument("--tts-url", default=DEFAULT_TTS_URL)
    parser.add_argument("--asr-url", default=DEFAULT_ASR_URL)
    parser.add_argument("--calls", type=int, default=DEFAULT_CALLS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("--comment", default="")
    parser.add_argument("--no-write", action="store_true", help="Run without changing committed benchmark history.")
    args = parser.parse_args()

    wait_ready(args.tts_url, args.asr_url)
    tts_status = request_json(f"{args.tts_url}/tts/status")
    asr_models = request_json(f"{args.asr_url}/v1/models").get("data", [])
    hardware = ", ".join(
        str(device.get("name")) for device in tts_status.get("cuda_memory", []) if device.get("name")
    ) or "CPU/unknown"
    asr_model = str(asr_models[0].get("id")) if asr_models else "unknown"

    started_at = now_iso()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="omnivoicetts-ssml-") as staging_root:
        staging_dir = Path(staging_root)
        print("Phase 1/2: generating warmup and all measured SSML-H WAV files.", flush=True)
        warmup = generate_call(args.tts_url, 4_242_424, staging_dir)
        print(f"[TTS warmup] {warmup['tts_seconds']:.3f}s {warmup['bytes']} bytes", flush=True)
        measurements = []
        for index, seed in enumerate(seeds_for_calls(args.calls), start=1):
            result = generate_call(args.tts_url, seed, staging_dir)
            measurements.append(result)
            print(
                f"[TTS {index:02d}/{args.calls:02d}] seed={seed} "
                f"tts={result['tts_seconds']:.3f}s bytes={result['bytes']}",
                flush=True,
            )

        print("Phase 2/2: warming Qwen3-ASR, then transcribing measured WAV files.", flush=True)
        transcribe_call(args.asr_url, warmup)
        print(f"[ASR warmup] transcript={warmup['transcript']!r}", flush=True)
        for index, result in enumerate(measurements, start=1):
            transcribe_call(args.asr_url, result)
            outcome = "PASS" if result["passed"] else "FAIL"
            print(
                f"[ASR {index:02d}/{args.calls:02d}] {outcome} seed={result['seed']} "
                f"asr={result['asr_seconds']:.3f}s transcript={result['transcript']!r}",
                flush=True,
            )

    passed = sum(1 for item in measurements if item["passed"])
    run = {
        "started_at": started_at,
        "tts_url": args.tts_url,
        "asr_url": args.asr_url,
        "tts_version": str(tts_status.get("version") or "unknown"),
        "tts_build_id": str(tts_status.get("build_id") or "unknown"),
        "asr_model": asr_model,
        "hardware": hardware,
        "policy": POLICY_LABEL,
        "comment": args.comment,
        "expected_text": EXPECTED_TEXT,
        "known_pre_fix_failure_seed": KNOWN_PRE_FIX_FAILURE_SEED,
        "warmup": warmup,
        "summary": {
            "calls": len(measurements),
            "passed": passed,
            "failed": len(measurements) - passed,
            "completion_percent": round(100.0 * passed / len(measurements), 1),
            "total_seconds": round(time.perf_counter() - started, 3),
            "avg_tts_seconds": round(sum(item["tts_seconds"] for item in measurements) / len(measurements), 3),
            "avg_asr_seconds": round(sum(item["asr_seconds"] for item in measurements) / len(measurements), 3),
            "min_bytes": min(item["bytes"] for item in measurements),
            "max_bytes": max(item["bytes"] for item in measurements),
        },
        "measurements": measurements,
    }
    if not args.no_write:
        append_json(args.results, run)
        append_markdown(args.markdown, run)
        append_details(args.details, run)
    else:
        print("Benchmark completed without updating official history.", flush=True)
    print(
        f"Completed {passed}/{len(measurements)} calls ({run['summary']['completion_percent']:.1f}%). "
        f"Results: {args.results}; summary: {args.markdown}",
        flush=True,
    )
    if passed != len(measurements):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
