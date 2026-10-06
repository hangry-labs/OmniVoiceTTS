from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_URL = os.getenv("OMNIVOICE_GPU_MEMORY_BENCHMARK_URL", "http://127.0.0.1:7861")
DEFAULT_RESULTS = ROOT / "benchmarks" / "memory" / "gpu" / "runs.json"
DEFAULT_SUMMARY = ROOT / "benchmarks" / "memory" / "gpu" / "BENCHMARKS.md"
DEFAULT_DETAILS = ROOT / "benchmarks" / "memory" / "gpu" / "DETAILS.md"
DEFAULT_REFERENCE_AUDIO = "/app/omnivoice/runtime_assets/voices/openai_default_voice.mp3"
DEFAULT_REFERENCE_TEXT = "Hello from OmniVoice. This Docker image includes a browser UI and an HTTP API."
DEFAULT_TEXT = (
    "This GPU memory benchmark uses a realistic two-sentence request to measure warmed inference "
    "for the voice modes commonly used through the OmniVoiceTTS API."
)


@dataclass(frozen=True)
class Scenario:
    code: str
    label: str
    description: str
    payload: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(base_url: str) -> None:
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        try:
            if request_json("GET", f"{base_url}/tts/ping", timeout=5).get("msg") == "pong":
                return
        except Exception:
            time.sleep(2)
    raise RuntimeError(f"TTS service did not become ready at {base_url}")


def generate_audio(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}/tts/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=900) as response:
        audio = response.read()
        content_type = response.headers.get("Content-Type", "")
    elapsed = time.perf_counter() - started
    if not content_type.startswith("audio/") or len(audio) < 1_000:
        raise RuntimeError(f"Invalid audio response: {content_type!r}, {len(audio)} bytes")
    return {"seconds": round(elapsed, 3), "bytes": len(audio), "content_type": content_type}


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


class DeviceMemorySampler:
    def __init__(self, gpu_index: int, interval: float) -> None:
        self.gpu_index = gpu_index
        self.interval = interval
        self.samples_mib: list[int] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _sample(self) -> None:
        snapshot = gpu_snapshot(self.gpu_index)
        if snapshot is not None:
            self.samples_mib.append(int(snapshot["used_mib"]))

    def _run(self) -> None:
        while not self.stop_event.is_set():
            self._sample()
            self.stop_event.wait(self.interval)
        self._sample()

    def __enter__(self) -> "DeviceMemorySampler":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop_event.set()
        self.thread.join(timeout=15)

    @property
    def peak_mib(self) -> int | None:
        return max(self.samples_mib) if self.samples_mib else None


def build_scenarios(text: str, reference_audio: str) -> list[Scenario]:
    base = {
        "text": text,
        "language": "English",
        "format": "wav",
        "device": "cuda:0",
        "num_step": 32,
        "seed": 42_424,
        "randomize_seed": False,
    }
    return [
        Scenario("RV", "random_voice", "Random voice without prompt or reference audio.", dict(base)),
        Scenario(
            "DV",
            "design_voice",
            "Voice design from a fixed instruction.",
            {**base, "instruct": "female, young adult, moderate pitch"},
        ),
        Scenario(
            "CR",
            "direct_clone",
            "Direct clone reference with a known transcript; prompt caching disabled.",
            {**base, "ref_audio": reference_audio, "ref_text": DEFAULT_REFERENCE_TEXT},
        ),
        Scenario(
            "CC",
            "cached_clone",
            "Direct clone reference with the same known transcript and prompt caching enabled.",
            {
                **base,
                "ref_audio": reference_audio,
                "ref_text": DEFAULT_REFERENCE_TEXT,
                "cache_voice_prompt": True,
            },
        ),
    ]


def pytorch_device_stats(status: dict[str, Any]) -> dict[str, Any]:
    devices = status.get("cuda_memory") or []
    device = next((item for item in devices if item.get("device") == "cuda:0"), devices[0] if devices else {})
    result = {"device": device.get("device"), "name": device.get("name")}
    for key in ("allocated", "reserved", "max_allocated", "max_reserved"):
        value = device.get(key)
        result[f"{key}_mib"] = round(float(value) / (1024 * 1024), 1) if value is not None else None
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


def run_label(run: dict[str, Any]) -> str:
    timestamp = datetime.fromisoformat(run["started_at"]).astimezone()
    return f"{timestamp:%d.%m.%Y %H:%M:%S} - {run['version']}"


def append_summary(path: Path, run: dict[str, Any]) -> None:
    rows = {item["code"]: item for item in run["scenarios"]}
    values = [
        run_label(run),
        str(run["hardware"].get("name") or "unknown").replace("|", "/"),
        str(run["calls_per_scenario"]),
    ]
    for code in ("RV", "DV", "CR", "CC"):
        item = rows.get(code, {})
        values.extend(
            [
                str(item.get("pytorch_max_allocated_mib", "n/a")),
                str(item.get("device_peak_mib", "n/a")),
            ]
        )
    values.append(str(run.get("comment") or "").replace("|", "/"))
    with path.open("a", encoding="utf-8") as file:
        file.write("| " + " | ".join(values) + " |\n")


def append_details(path: Path, run: dict[str, Any]) -> None:
    lines = [
        "",
        f"## {run_label(run)}",
        "",
        f"- TTS endpoint: `{run['base_url']}`",
        f"- GPU: `{run['hardware'].get('name', 'unknown')}`; driver `{run['hardware'].get('driver', 'unknown')}`",
        f"- Calls per scenario: `{run['calls_per_scenario']}` after `{run['warmup_calls']}` scenario warmup call(s)",
        f"- Comment: {run.get('comment') or 'None'}",
        "",
        "| Scenario | Average seconds | Process allocated | Process reserved | Process peak | Device peak | Samples |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in run["scenarios"]:
        lines.append(
            f"| {item['code']} - {item['label']} | {item['average_seconds']:.3f} | "
            f"{item['pytorch_allocated_mib']} MiB | {item['pytorch_reserved_mib']} MiB | "
            f"{item['pytorch_max_allocated_mib']} MiB | {item['device_peak_mib']} MiB | "
            f"{item['device_samples']} |"
        )
    existing = path.read_text(encoding="utf-8").rstrip("\n")
    path.write_text(existing + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure warmed OmniVoiceTTS GPU memory by API voice mode.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--calls", type=int, default=5)
    parser.add_argument("--warmup-calls", type=int, default=1)
    parser.add_argument("--sample-interval", type=float, default=0.1)
    parser.add_argument("--limit-scenarios", type=int, default=0)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--reference-audio", default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("--comment", default="")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    if args.calls < 1 or args.warmup_calls < 0:
        parser.error("--calls must be at least 1 and --warmup-calls must not be negative")

    wait_ready(args.base_url)
    initial_status = request_json("GET", f"{args.base_url}/tts/status")
    if not initial_status.get("cuda_memory"):
        raise RuntimeError("The TTS service does not report a CUDA device. Start it in GPU mode.")
    hardware = gpu_snapshot(args.gpu_index) or {
        "name": initial_status["cuda_memory"][0].get("name", "unknown"),
        "index": args.gpu_index,
    }
    scenarios = build_scenarios(args.text, args.reference_audio)
    if args.limit_scenarios:
        scenarios = scenarios[: args.limit_scenarios]

    scenario_results = []
    total = len(scenarios) * (args.warmup_calls + args.calls)
    progress = 0
    for scenario in scenarios:
        for warmup in range(args.warmup_calls):
            progress += 1
            print(f"[{progress}/{total}] {scenario.code} warmup {warmup + 1}/{args.warmup_calls}", flush=True)
            generate_audio(args.base_url, scenario.payload)
        request_json("POST", f"{args.base_url}/tts/cache/clear", {"reset_peak_stats": True})
        measurements = []
        with DeviceMemorySampler(args.gpu_index, args.sample_interval) as sampler:
            for call in range(args.calls):
                progress += 1
                result = generate_audio(args.base_url, scenario.payload)
                measurements.append(result)
                print(
                    f"[{progress}/{total}] {scenario.code} call {call + 1}/{args.calls} "
                    f"{result['seconds']:.3f}s {result['bytes']} bytes",
                    flush=True,
                )
        stats = pytorch_device_stats(request_json("GET", f"{args.base_url}/tts/status"))
        scenario_results.append(
            {
                "code": scenario.code,
                "label": scenario.label,
                "description": scenario.description,
                "calls": args.calls,
                "average_seconds": round(statistics.fmean(item["seconds"] for item in measurements), 3),
                "total_seconds": round(sum(item["seconds"] for item in measurements), 3),
                "bytes": sum(item["bytes"] for item in measurements),
                "pytorch_allocated_mib": stats["allocated_mib"],
                "pytorch_reserved_mib": stats["reserved_mib"],
                "pytorch_max_allocated_mib": stats["max_allocated_mib"],
                "pytorch_max_reserved_mib": stats["max_reserved_mib"],
                "device_peak_mib": sampler.peak_mib,
                "device_samples": len(sampler.samples_mib),
                "measurements": measurements,
            }
        )

    final_status = request_json("GET", f"{args.base_url}/tts/status")
    run = {
        "started_at": now_iso(),
        "version": str(final_status.get("version") or "unknown"),
        "build_id": str(final_status.get("build_id") or "unknown"),
        "base_url": args.base_url,
        "hardware": hardware,
        "text": args.text,
        "text_chars": len(args.text),
        "calls_per_scenario": args.calls,
        "warmup_calls": args.warmup_calls,
        "sample_interval_seconds": args.sample_interval,
        "comment": args.comment,
        "initial_pytorch": pytorch_device_stats(initial_status),
        "final_pytorch": pytorch_device_stats(final_status),
        "scenarios": scenario_results,
    }
    if not args.no_write:
        append_json(args.results, run)
        append_summary(args.summary, run)
        append_details(args.details, run)
        print(f"Appended results to {args.results}, {args.summary}, and {args.details}.", flush=True)
    else:
        print("Benchmark completed without updating official history.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
