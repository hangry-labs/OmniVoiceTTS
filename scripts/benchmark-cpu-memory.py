from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
DEFAULT_LIMITS = "1024m,1536m,2048m,2304m,2560m,2816m,3072m,3584m,4096m,5120m,6144m,8192m"
DEFAULT_TEXT = (
    "This CPU memory benchmark uses a realistic two-sentence request to estimate "
    "the RAM needed for local text to speech with common voice modes."
)
DEFAULT_REF_AUDIO = "/app/omnivoice/assets/openai_default_voice.mp3"
DEFAULT_REF_TEXT = "We've got to have a dream if we are going to make a dream come true."
PROFILE_WITH_TEXT = "benchmark_cpu_with_text"
PROFILE_NO_TEXT = "benchmark_cpu_no_text"


@dataclass(frozen=True)
class Scenario:
    code: str
    label: str
    description: str
    payload: dict[str, Any]


def run(cmd: list[str], timeout: int = 60, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def now_label() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_version() -> str:
    path = ROOT / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "unknown"


def parse_size_to_mib(value: str) -> float:
    value = value.strip()
    number = ""
    unit = ""
    for char in value:
        if char.isdigit() or char == ".":
            number += char
        elif not char.isspace():
            unit += char
    if not number:
        return 0.0
    amount = float(number)
    factors = {
        "b": 1 / (1024 * 1024),
        "kb": 1000 / (1024 * 1024),
        "kib": 1 / 1024,
        "mb": 1000 * 1000 / (1024 * 1024),
        "mib": 1,
        "gb": 1000 * 1000 * 1000 / (1024 * 1024),
        "gib": 1024,
    }
    return amount * factors.get(unit.lower(), 1)


def limit_to_mib(limit: str) -> float:
    value = limit.strip().lower()
    if value.endswith("m"):
        return float(value[:-1])
    if value.endswith("g"):
        return float(value[:-1]) * 1024
    return parse_size_to_mib(value)


def recommendation_from_limit(limit: str | None) -> str:
    if not limit:
        return "n/a"
    # Add a small headroom before rounding so an exact threshold pass such as
    # 1024m is not published as a too-tight 1 GB recommendation.
    gib = math.ceil((limit_to_mib(limit) + 512) / 1024)
    return f"{gib} GB"


def docker_info() -> dict[str, Any]:
    info = run(["docker", "info", "--format", "{{json .}}"], timeout=30, check=True)
    parsed = json.loads(info.stdout)
    return {
        "server_version": parsed.get("ServerVersion"),
        "ncpu": parsed.get("NCPU"),
        "mem_total_bytes": parsed.get("MemTotal"),
        "operating_system": parsed.get("OperatingSystem"),
        "ostype": parsed.get("OSType"),
    }


def wait_ready(base_url: str, container: str, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = inspect_state(container)
        if state.get("Status") and state["Status"] != "running":
            return False
        try:
            with urllib.request.urlopen(f"{base_url}/tts/ping", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("msg") == "pong":
                return True
        except Exception:
            time.sleep(2)
    return False


def request_json(url: str, timeout: int = 20) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_audio(url: str, payload: dict[str, Any], timeout: int) -> tuple[int, int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        audio = response.read()
    return status, len(audio), content_type


def inspect_state(container: str) -> dict[str, Any]:
    result = run(["docker", "inspect", container, "--format", "{{json .State}}"], timeout=20)
    if result.returncode != 0:
        return {}
    return json.loads(result.stdout)


def container_logs(container: str) -> str:
    result = run(["docker", "logs", "--tail", "80", container], timeout=20)
    return (result.stdout + result.stderr).strip()


def remove_container(container: str) -> None:
    run(["docker", "rm", "-f", container], timeout=30)


def docker_stats_mib(container: str) -> float:
    result = run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container], timeout=20)
    if result.returncode != 0:
        return 0.0
    first = result.stdout.strip().split("/", 1)[0].strip()
    return parse_size_to_mib(first)


class MemoryMonitor:
    def __init__(self, container: str) -> None:
        self.container = container
        self.stop_event = threading.Event()
        self.peak_mib = 0.0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            self.peak_mib = max(self.peak_mib, docker_stats_mib(self.container))
            time.sleep(0.5)
        self.peak_mib = max(self.peak_mib, docker_stats_mib(self.container))

    def __enter__(self) -> "MemoryMonitor":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop_event.set()
        self.thread.join(timeout=10)


def write_profiles(profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    profiles = {
        PROFILE_WITH_TEXT: {
            "ref_audio": DEFAULT_REF_AUDIO,
            "ref_text": DEFAULT_REF_TEXT,
            "language": "english",
            "seed": 12345,
            "randomize_seed": False,
        },
        PROFILE_NO_TEXT: {
            "ref_audio": DEFAULT_REF_AUDIO,
            "ref_text": "",
            "language": "english",
            "seed": 12345,
            "randomize_seed": False,
        },
    }
    (profile_dir / "profiles.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")


def build_scenarios(text: str) -> list[Scenario]:
    base = {
        "model": "gpt-4o-mini-tts",
        "input": text,
        "response_format": "mp3",
        "speed": 1.0,
        "language": "english",
        "num_step": 32,
    }
    return [
        Scenario(
            "RV",
            "random_voice",
            "Random/no-prompt voice: no reference audio, no design instructions, no stored profile.",
            {**base, "voice": "auto"},
        ),
        Scenario(
            "DV",
            "design_voice",
            "Voice design/generate voice: explicit design instructions, no reference audio.",
            {**base, "voice": "auto", "instructions": "female, young adult, moderate pitch"},
        ),
        Scenario(
            "CR-NT",
            "clone_reference_no_text",
            "Direct clone reference without transcript. This may lazy-load ASR.",
            {**base, "voice": "auto", "ref_audio": DEFAULT_REF_AUDIO},
        ),
        Scenario(
            "CR-TX",
            "clone_reference_with_text",
            "Direct clone reference with transcript.",
            {**base, "voice": "auto", "ref_audio": DEFAULT_REF_AUDIO, "ref_text": DEFAULT_REF_TEXT},
        ),
        Scenario(
            "SV-NT",
            "stored_voice_no_transcript",
            "Stored voice profile without transcript. This may lazy-load ASR.",
            {**base, "voice": "auto", "voice_profile": PROFILE_NO_TEXT},
        ),
        Scenario(
            "SV-TX",
            "stored_voice_with_transcript",
            "Stored voice profile with transcript.",
            {**base, "voice": "auto", "voice_profile": PROFILE_WITH_TEXT},
        ),
    ]


def append_json(path: Path, run_data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = [data]
    else:
        data = []
    data.append(run_data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_markdown(path: Path, scenarios: list[Scenario]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    shortcut_lines = [f"- `{scenario.code}`: {scenario.description}" for scenario in scenarios]
    columns = " | ".join(["Date", "Text chars", "Version", *[scenario.code for scenario in scenarios]])
    separators = " | ".join(["---", "---:", "---", *["---:" for _ in scenarios]])
    path.write_text(
        "\n".join(
            [
                "# cpu_memory",
                "",
                "CPU-only Docker memory-limit benchmark for OpenAI-compatible speech requests.",
                "",
                "Each run starts one CPU container per scenario and Docker memory limit, then records the lowest passing limit as a conservative whole-GB RAM recommendation. The detailed pass/fail attempts are stored in `cpu-memory.json`.",
                "",
                "The benchmark text is intentionally one realistic short request, around 100-200 characters. Results are not a guarantee for long text, concurrent requests, larger outputs, or different host memory behavior.",
                "",
                "Scenario shortcuts:",
                "",
                *shortcut_lines,
                "",
                f"| {columns} |",
                f"| {separators} |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def append_markdown(
    path: Path,
    *,
    run_label: str,
    version: str,
    text_chars: int,
    scenarios: list[Scenario],
    recommendations: dict[str, str],
) -> None:
    ensure_markdown(path, scenarios)
    cells = [run_label, str(text_chars), version, *[recommendations.get(scenario.code, "n/a") for scenario in scenarios]]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("| " + " | ".join(cells) + " |\n")


def run_attempt(
    *,
    image: str,
    limit: str,
    port: int,
    profile_dir: Path,
    scenario: Scenario,
    container_prefix: str,
    timeout: int,
) -> dict[str, Any]:
    container = f"{container_prefix}_{scenario.code.lower().replace('-', '_')}_{limit.replace('.', '_').replace(':', '_')}"
    base_url = f"http://127.0.0.1:{port}"
    remove_container(container)
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container,
        "-p",
        f"{port}:7861",
        "--memory",
        limit,
        "--memory-swap",
        limit,
        "-e",
        "OMNIVOICE_DEVICE=cpu",
        "-e",
        "OMNIVOICE_LOAD_ASR=0",
        "-e",
        "OMNIVOICE_ALLOW_CPU_EAGER_ASR=0",
        "-e",
        "PORT=7861",
        "-e",
        "UVICORN_RELOAD=0",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "-v",
        f"{profile_dir.resolve()}:/app/openai_voice_profiles",
        "-v",
        f"{(ROOT / 'omnivoice').resolve()}:/app/omnivoice",
        "-v",
        f"{(ROOT / 'hangrylabs').resolve()}:/app/hangrylabs",
        image,
    ]
    start = run(cmd, timeout=60)
    if start.returncode != 0:
        return {
            "limit": limit,
            "limit_mib": limit_to_mib(limit),
            "result": "container-start-failed",
            "seconds": 0.0,
            "peak_mib": 0.0,
            "notes": (start.stderr or start.stdout).strip()[:240],
        }

    attempt: dict[str, Any] = {
        "limit": limit,
        "limit_mib": limit_to_mib(limit),
        "container": container,
        "port": port,
    }
    try:
        ready = wait_ready(base_url, container, timeout=120)
        if not ready:
            state = inspect_state(container)
            attempt.update(
                {
                    "result": "startup-failed",
                    "seconds": 0.0,
                    "peak_mib": docker_stats_mib(container),
                    "exit_code": state.get("ExitCode"),
                    "oom_killed": state.get("OOMKilled"),
                    "notes": container_logs(container).replace("\n", " ")[:240],
                }
            )
            return attempt

        status = request_json(f"{base_url}/tts/status", timeout=20)
        start_time = time.monotonic()
        with MemoryMonitor(container) as monitor:
            try:
                http_status, bytes_out, content_type = request_audio(
                    f"{base_url}/v1/audio/speech",
                    scenario.payload,
                    timeout=timeout,
                )
                seconds = time.monotonic() - start_time
                result = "pass" if http_status == 200 and content_type.startswith("audio/") and bytes_out > 1000 else "bad-response"
                attempt.update(
                    {
                        "result": result,
                        "http_status": http_status,
                        "bytes": bytes_out,
                        "content_type": content_type,
                        "seconds": seconds,
                        "peak_mib": monitor.peak_mib,
                        "notes": f"status load_asr={status.get('load_asr')} resolved_device={status.get('resolved_device')}",
                    }
                )
            except Exception as exc:
                seconds = time.monotonic() - start_time
                state = inspect_state(container)
                attempt.update(
                    {
                        "result": "request-failed",
                        "seconds": seconds,
                        "peak_mib": monitor.peak_mib,
                        "exit_code": state.get("ExitCode"),
                        "oom_killed": state.get("OOMKilled"),
                        "notes": f"{type(exc).__name__}: {exc}",
                    }
                )
        state = inspect_state(container)
        attempt.setdefault("exit_code", state.get("ExitCode"))
        attempt.setdefault("oom_killed", state.get("OOMKilled"))
        return attempt
    finally:
        remove_container(container)


def run_scenario(
    *,
    scenario: Scenario,
    image: str,
    limits: list[str],
    start_port: int,
    scenario_index: int,
    profile_dir: Path,
    container_prefix: str,
    timeout: int,
    passes_after_first: int,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    first_pass_index: int | None = None
    for index, limit in enumerate(limits):
        port = start_port + scenario_index * 100 + index
        print(f"[{scenario.code}] [{index + 1}/{len(limits)}] Testing CPU memory limit {limit} ...", flush=True)
        attempt = run_attempt(
            image=image,
            limit=limit,
            port=port,
            profile_dir=profile_dir,
            scenario=scenario,
            container_prefix=container_prefix,
            timeout=timeout,
        )
        attempts.append(attempt)
        print(
            "  {result} limit={limit} seconds={seconds:.3f} peak={peak:.1f}MiB notes={notes}".format(
                result=attempt.get("result"),
                limit=limit,
                seconds=attempt.get("seconds") or 0,
                peak=attempt.get("peak_mib") or 0,
                notes=attempt.get("notes", ""),
            ),
            flush=True,
        )
        if attempt.get("result") == "pass" and first_pass_index is None:
            first_pass_index = index
        if first_pass_index is not None and index >= first_pass_index + passes_after_first:
            break

    passing = [attempt for attempt in attempts if attempt.get("result") == "pass"]
    minimum_pass = passing[0] if passing else None
    return {
        "code": scenario.code,
        "label": scenario.label,
        "description": scenario.description,
        "minimum_passing_limit": minimum_pass,
        "recommendation": recommendation_from_limit(minimum_pass["limit"]) if minimum_pass else "no pass",
        "attempts": attempts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark CPU Docker memory limits for common OpenAI TTS scenarios.")
    parser.add_argument("--image", default="omnivoicetts:test")
    parser.add_argument("--limits", default=DEFAULT_LIMITS, help="Comma-separated Docker memory limits, ascending.")
    parser.add_argument("--start-port", type=int, default=7870)
    parser.add_argument("--container-prefix", default="omnivoicetts_cpu_mem")
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--passes-after-first", type=int, default=1)
    parser.add_argument("--results", default=str(ROOT / "benchmarks" / "cpu-memory.json"))
    parser.add_argument("--markdown", default=str(ROOT / "benchmarks" / "CPU_MEMORY.md"))
    args = parser.parse_args()

    limits = [item.strip() for item in args.limits.split(",") if item.strip()]
    version = read_version()
    run_label = f"{now_label()} - {version}"
    scenarios = build_scenarios(args.text)
    scenario_results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="omnivoicetts-cpu-profiles-") as profile_root:
        profile_dir = Path(profile_root)
        write_profiles(profile_dir)
        for scenario_index, scenario in enumerate(scenarios):
            scenario_results.append(
                run_scenario(
                    scenario=scenario,
                    image=args.image,
                    limits=limits,
                    start_port=args.start_port,
                    scenario_index=scenario_index,
                    profile_dir=profile_dir,
                    container_prefix=args.container_prefix,
                    timeout=args.timeout,
                    passes_after_first=args.passes_after_first,
                )
            )

    recommendations = {result["code"]: result["recommendation"] for result in scenario_results}
    run_data = {
        "run": run_label,
        "timestamp": now_iso(),
        "version": version,
        "image": args.image,
        "docker": docker_info(),
        "text": args.text,
        "text_chars": len(args.text),
        "methodology": (
            "One CPU-only Docker container per scenario and memory limit; OMNIVOICE_LOAD_ASR=0; "
            "temporary known-good saved profiles with and without ref_text; OpenAI-compatible /v1/audio/speech MP3 requests. "
            "Markdown scenario cells are conservative whole-GB recommendations derived from the lowest passing Docker memory limit."
        ),
        "recommendations": recommendations,
        "scenarios": scenario_results,
    }
    append_json(Path(args.results), run_data)
    append_markdown(
        Path(args.markdown),
        run_label=run_label,
        version=version,
        text_chars=len(args.text),
        scenarios=scenarios,
        recommendations=recommendations,
    )
    print(f"Wrote JSON results to {args.results}")
    print(f"Appended markdown results to {args.markdown}")
    for result in scenario_results:
        minimum = result.get("minimum_passing_limit")
        if minimum:
            print(
                f"{result['code']}: min={minimum['limit']} peak={minimum.get('peak_mib', 0):.1f}MiB "
                f"recommend={result['recommendation']}"
            )
        else:
            print(f"{result['code']}: no pass")
    return 0 if all(result.get("minimum_passing_limit") for result in scenario_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
