from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
MANIFEST_PATH = ROOT / "examples" / "assets" / "manifest.json"
RESULTS_PATH = ROOT / "benchmarks" / "example-generation.json"
MARKDOWN_RESULTS_DIR = ROOT / "benchmarks"
MARKDOWN_INDEX_PATH = MARKDOWN_RESULTS_DIR / "BENCHMARKS.md"
MARKDOWN_ROUND_FILES = {
    "random_voice": "WARM_RANDOM.md",
    "predefined_voice": "WARM_PREDEFINED.md",
    "direct_reference_audio": "WARM_DIRECT_REFERENCE.md",
    "prewarm_random": "PREWARM_RANDOM.md",
    "prewarm_predefined": "PREWARM_PREDEFINED.md",
    "prewarm_direct_reference": "PREWARM_DIRECT_REFERENCE.md",
}
MARKDOWN_ROUND_TITLES = {
    "random_voice": "random_voice",
    "predefined_voice": "predefined_voice",
    "direct_reference_audio": "direct_reference_audio",
    "prewarm_random": "prewarm_random",
    "prewarm_predefined": "prewarm_predefined",
    "prewarm_direct_reference": "prewarm_direct_reference",
}
DEFAULT_BASE_URL = os.getenv("OMNIVOICE_BENCHMARK_BASE_URL", "http://127.0.0.1:7864")
DEFAULT_PREDEFINED_VOICE = os.getenv("OMNIVOICE_BENCHMARK_VOICE", "benchmark_original_clone")
DEFAULT_REFERENCE_AUDIO = os.getenv("OMNIVOICE_BENCHMARK_REF_AUDIO", "/app/omnivoice/assets/openai_default_voice.mp3")
DEFAULT_NUM_STEP = int(os.getenv("OMNIVOICE_BENCHMARK_NUM_STEP", "24"))
DEFAULT_OUTPUT_FORMAT = os.getenv("OMNIVOICE_BENCHMARK_FORMAT", "mp3")
DEFAULT_LANGUAGE_LIMIT = int(os.getenv("OMNIVOICE_BENCHMARK_LIMIT_LANGUAGES", "0"))
DEFAULT_ITEMS_PER_ROUND = int(os.getenv("OMNIVOICE_BENCHMARK_ITEMS", "100"))
DEFAULT_SAMPLES_PER_LANGUAGE = int(os.getenv("OMNIVOICE_BENCHMARK_SAMPLES_PER_LANGUAGE", "2"))
DEFAULT_RANDOM_WARMUP = int(os.getenv("OMNIVOICE_BENCHMARK_RANDOM_WARMUP", "10"))
DEFAULT_REFERENCE_WARMUP = int(os.getenv("OMNIVOICE_BENCHMARK_REFERENCE_WARMUP", "10"))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(base_url: str) -> None:
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        try:
            payload = request_json("GET", f"{base_url}/tts/ping", timeout=5)
            if payload.get("msg") == "pong":
                return
        except Exception:
            time.sleep(3)
    raise RuntimeError(f"API did not become ready at {base_url}")


def post_audio(base_url: str, route: str, payload: dict[str, Any], timeout: int = 900) -> tuple[int, dict[str, str]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{route}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        headers = {key.lower(): value for key, value in response.headers.items()}
        audio = response.read()
    if not content_type.startswith("audio/"):
        raise RuntimeError(f"Expected audio response from {route}, got {content_type}")
    if len(audio) < 1000:
        raise RuntimeError(f"Generated audio from {route} was too small: {len(audio)} bytes")
    return len(audio), headers


def load_workload(
    manifest_path: Path,
    language_limit: int = 0,
    items_per_round: int = 100,
    samples_per_language: int = 2,
) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    languages = manifest["languages"][: language_limit or None]
    base_work: list[dict[str, Any]] = []
    for language in languages:
        slug = language["slug"]
        lang_name = language["language"]
        for index, sample in enumerate(language.get("random", [])[:samples_per_language], start=1):
            base_work.append(
                {
                    "language_slug": slug,
                    "language": lang_name,
                    "type": "random",
                    "index": index,
                    "text": sample["text"],
                }
            )
    if not base_work:
        return []
    work = []
    for index in range(items_per_round):
        item = dict(base_work[index % len(base_work)])
        item["sequence"] = index + 1
        item["repeat"] = index // len(base_work)
        work.append(item)
    return work


def timed_audio_call(base_url: str, route: str, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    size, headers = post_audio(base_url, route, payload)
    elapsed = time.perf_counter() - started
    return {
        "seconds": elapsed,
        "bytes": size,
        "seed": headers.get("x-omnivoicetts-seed"),
        "duration": headers.get("x-omnivoicetts-duration"),
        "format": headers.get("x-omnivoicetts-format"),
    }


def summarize_measurements(measurements: list[dict[str, Any]]) -> dict[str, Any]:
    if not measurements:
        return {"count": 0, "seconds_total": 0.0}
    seconds = [float(item["seconds"]) for item in measurements]
    return {
        "count": len(measurements),
        "seconds_total": round(sum(seconds), 3),
        "seconds_avg": round(statistics.fmean(seconds), 3),
        "seconds_min": round(min(seconds), 3),
        "seconds_max": round(max(seconds), 3),
        "bytes_total": int(sum(int(item["bytes"]) for item in measurements)),
    }


def grouped_summary(measurements: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in measurements:
        groups[str(item[key])].append(item)
    return {name: summarize_measurements(values) for name, values in sorted(groups.items())}


def build_native_payload(item: dict[str, Any], num_step: int, output_format: str) -> dict[str, Any]:
    return {
        "text": item["text"],
        "language": item["language"],
        "format": output_format,
        "num_step": num_step,
        "speed": 1.0,
        "device": "auto",
    }


def build_openai_payload(item: dict[str, Any], voice: str, num_step: int, output_format: str) -> dict[str, Any]:
    return {
        "model": "tts-1",
        "voice": voice,
        "input": item["text"],
        "response_format": output_format,
        "language": item["language"],
        "num_step": num_step,
        "speed": 1.0,
    }


def build_direct_reference_payload(item: dict[str, Any], ref_audio: str, num_step: int, output_format: str) -> dict[str, Any]:
    payload = build_native_payload(item, num_step=num_step, output_format=output_format)
    payload["ref_audio"] = ref_audio
    return payload


def build_round_request(
    item: dict[str, Any],
    round_name: str,
    num_step: int,
    output_format: str,
    predefined_voice: str,
    reference_audio: str,
) -> tuple[str, dict[str, Any]]:
    if round_name in {"random_voice", "prewarm_random"}:
        return "/tts/generate", build_native_payload(item, num_step=num_step, output_format=output_format)
    if round_name in {"predefined_voice", "prewarm_predefined"}:
        return "/v1/audio/speech", build_openai_payload(
            item,
            voice=predefined_voice,
            num_step=num_step,
            output_format=output_format,
        )
    if round_name in {"direct_reference_audio", "prewarm_direct_reference"}:
        return "/tts/generate", build_direct_reference_payload(
            item,
            ref_audio=reference_audio,
            num_step=num_step,
            output_format=output_format,
        )
    raise ValueError(f"Unknown benchmark round: {round_name}")


def run_stage(
    base_url: str,
    workload: list[dict[str, Any]],
    round_name: str,
    call_count: int,
    num_step: int,
    output_format: str,
    predefined_voice: str,
    reference_audio: str,
    progress_offset: int,
    total_calls: int,
) -> list[dict[str, Any]]:
    results = []
    stage_workload = workload[:call_count]
    for done, item in enumerate(stage_workload, start=1):
        route, payload = build_round_request(
            item,
            round_name,
            num_step,
            output_format,
            predefined_voice,
            reference_audio,
        )
        result = timed_audio_call(base_url, route, payload)
        result.update(
            {
                "round": round_name,
                "language_slug": item["language_slug"],
                "language": item["language"],
                "type": item["type"],
                "index": item["index"],
                "sequence": item["sequence"],
                "repeat": item.get("repeat", 0),
            }
        )
        results.append(result)
        print(
            f"[{progress_offset + done:03d}/{total_calls:03d}] "
            f"{round_name} {done:03d}/{call_count:03d} "
            f"{item['language_slug']}/{item['type']}/{item['index']:02d} seq={item['sequence']:03d} "
            f"{result['seconds']:.2f}s {result['bytes']} bytes",
            flush=True,
        )
    return results


def append_results(path: Path, run: dict[str, Any]) -> None:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"schema": 1, "runs": []}
    data.setdefault("runs", []).append(run)
    data["latest"] = run
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        temp_path = Path(file.name)
    temp_path.replace(path)


def markdown_run_label(run: dict[str, Any]) -> str:
    timestamp = datetime.fromisoformat(run["started_at"]).astimezone()
    version = run.get("status_after", {}).get("version") or "unknown"
    return f"{timestamp:%d.%m.%Y %H:%M:%S} - {version}"


def ensure_category_file(path: Path, title: str) -> None:
    if path.exists():
        return
    display_title = MARKDOWN_ROUND_TITLES.get(title, title)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {display_title}",
                "",
                "| Run | Calls | Total seconds | Avg seconds | Min | Max | Bytes |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def append_category_markdown(markdown_dir: Path, run: dict[str, Any]) -> None:
    run_label = markdown_run_label(run)
    for round_name, row in sorted(run["summary"]["by_round"].items()):
        file_name = MARKDOWN_ROUND_FILES.get(round_name, f"{round_name.upper()}.md")
        path = markdown_dir / file_name
        ensure_category_file(path, round_name)
        existing = path.read_text(encoding="utf-8")
        normalized = existing.rstrip("\n")
        if normalized != existing:
            path.write_text(normalized + "\n", encoding="utf-8")
            prefix = ""
        else:
            prefix = "" if existing.endswith("\n") else "\n"
        with path.open("a", encoding="utf-8") as file:
            file.write(
                prefix
                + "| "
                + f"{run_label} | "
                + f"{row.get('count', 0)} | "
                + f"{row.get('seconds_total', 0)} | "
                + f"{row.get('seconds_avg', 0)} | "
                + f"{row.get('seconds_min', 0)} | "
                + f"{row.get('seconds_max', 0)} | "
                + f"{row.get('bytes_total', 0)} |\n"
            )


def write_markdown_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# OmniVoiceTTS Benchmarks",
                "",
                "Benchmark category logs are append-only tables. Each row is one benchmark run for one benchmark category.",
                "",
                "## Purpose",
                "",
                "These benchmarks track OmniVoiceTTS runtime performance across versions, refactors, dependency changes, Docker image changes, and future performance work. The goal is not to produce a universal score; it is to catch local improvements and regressions under a repeatable workload.",
                "",
                "More categories may be added as the product changes; keeping one append-only file per category makes version-to-version comparisons easy to scan.",
                "",
                "Current baseline hardware: NVIDIA GeForce RTX 5060 Ti. AMD ROCm support is not validated because the maintainer does not have AMD hardware; AMD testing would require an AMD GPU donation or a reliable community tester.",
                "",
                "## Methodology",
                "",
                "- Workload source: `examples/assets/manifest.json`.",
                "- Selection: first two random samples from each manifest language, repeated deterministically to the configured call count.",
                "- Default measured calls: 100 per category.",
                "- Each category is prewarmed immediately before that category is measured, so one stage's cold start or timeout does not distort later stages.",
                "- Detailed JSON results are stored in `example-generation.json`.",
                "",
                "## Categories",
                "",
                "- `warm_random` (`random_voice` in JSON): measured no-reference calls after that stage's warmup. This should usually be fastest because no voice clone prompt is prepared.",
                "- `warm_predefined` (`predefined_voice` in JSON): measured named built-in or saved OpenAI-compatible voice calls after warmup. This covers voices created in the UI Add Voice tab and the benchmark built-in clone alias. Voice clone prompt preparation is cached after warmup.",
                "- `warm_direct_reference` (`direct_reference_audio` in JSON): measured direct `ref_audio` calls after warmup. This is the original ad hoc cloning path and intentionally does not use the stored-voice cache.",
                "- `prewarm_random`: warmup calls for the no-reference path.",
                "- `prewarm_predefined`: warmup calls for the cached predefined voice path.",
                "- `prewarm_direct_reference`: warmup calls for the direct `ref_audio` path.",
                "",
                "- [warm_random](WARM_RANDOM.md)",
                "- [warm_predefined](WARM_PREDEFINED.md)",
                "- [warm_direct_reference](WARM_DIRECT_REFERENCE.md)",
                "- [prewarm_random](PREWARM_RANDOM.md)",
                "- [prewarm_predefined](PREWARM_PREDEFINED.md)",
                "- [prewarm_direct_reference](PREWARM_DIRECT_REFERENCE.md)",
                "",
                "Detailed machine-readable run data is stored in `example-generation.json`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OmniVoiceTTS example-generation workload.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--results", type=Path, default=RESULTS_PATH)
    parser.add_argument("--markdown-dir", type=Path, default=MARKDOWN_RESULTS_DIR)
    parser.add_argument("--reference-audio", default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--voice", default=DEFAULT_PREDEFINED_VOICE)
    parser.add_argument("--num-step", type=int, default=DEFAULT_NUM_STEP)
    parser.add_argument("--format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--limit-languages", type=int, default=DEFAULT_LANGUAGE_LIMIT)
    parser.add_argument("--items-per-round", type=int, default=DEFAULT_ITEMS_PER_ROUND)
    parser.add_argument("--samples-per-language", type=int, default=DEFAULT_SAMPLES_PER_LANGUAGE)
    parser.add_argument("--random-warmup", type=int, default=DEFAULT_RANDOM_WARMUP)
    parser.add_argument("--reference-warmup", type=int, default=DEFAULT_REFERENCE_WARMUP)
    parser.add_argument("--skip-prewarm", action="store_true")
    args = parser.parse_args()

    wait_ready(args.base_url)
    started = time.perf_counter()
    status_before = request_json("GET", f"{args.base_url}/tts/status")
    workload = load_workload(
        args.manifest,
        args.limit_languages,
        args.items_per_round,
        args.samples_per_language,
    )
    if not workload:
        raise RuntimeError("Benchmark workload is empty.")

    language_count = len({item["language_slug"] for item in workload})
    prewarm_count = 0
    if not args.skip_prewarm:
        prewarm_count = min(args.random_warmup, len(workload)) + min(args.reference_warmup, len(workload)) * 2
    total_calls = prewarm_count + len(workload) * 3
    print(
        f"Benchmarking manifest workload from {args.manifest}: "
        f"{len(workload)} fixed items per measured round, {language_count} languages, "
        f"{total_calls} total API calls. Selection is first {args.samples_per_language} random samples "
        "per manifest language, repeated deterministically when needed.",
        flush=True,
    )
    progress_offset = 0
    prewarm_random_results = []
    if not args.skip_prewarm:
        prewarm_random_results = run_stage(
            args.base_url,
            workload,
            "prewarm_random",
            min(args.random_warmup, len(workload)),
            args.num_step,
            args.format,
            args.voice,
            args.reference_audio,
            progress_offset,
            total_calls,
        )
        progress_offset += len(prewarm_random_results)
    random_results = run_stage(
        args.base_url,
        workload,
        "random_voice",
        len(workload),
        args.num_step,
        args.format,
        args.voice,
        args.reference_audio,
        progress_offset,
        total_calls,
    )
    progress_offset += len(random_results)
    prewarm_predefined_results = []
    if not args.skip_prewarm:
        prewarm_predefined_results = run_stage(
            args.base_url,
            workload,
            "prewarm_predefined",
            min(args.reference_warmup, len(workload)),
            args.num_step,
            args.format,
            args.voice,
            args.reference_audio,
            progress_offset,
            total_calls,
        )
        progress_offset += len(prewarm_predefined_results)
    predefined_results = run_stage(
        args.base_url,
        workload,
        "predefined_voice",
        len(workload),
        args.num_step,
        args.format,
        args.voice,
        args.reference_audio,
        progress_offset,
        total_calls,
    )
    progress_offset += len(predefined_results)
    prewarm_direct_reference_results = []
    if not args.skip_prewarm:
        prewarm_direct_reference_results = run_stage(
            args.base_url,
            workload,
            "prewarm_direct_reference",
            min(args.reference_warmup, len(workload)),
            args.num_step,
            args.format,
            args.voice,
            args.reference_audio,
            progress_offset,
            total_calls,
        )
        progress_offset += len(prewarm_direct_reference_results)
    direct_reference_results = run_stage(
        args.base_url,
        workload,
        "direct_reference_audio",
        len(workload),
        args.num_step,
        args.format,
        args.voice,
        args.reference_audio,
        progress_offset,
        total_calls,
    )
    status_after = request_json("GET", f"{args.base_url}/tts/status")
    finished = time.perf_counter()
    measurements = [
        *prewarm_random_results,
        *random_results,
        *prewarm_predefined_results,
        *predefined_results,
        *prewarm_direct_reference_results,
        *direct_reference_results,
    ]
    run = {
        "started_at": now_iso(),
        "base_url": args.base_url,
        "manifest": str(args.manifest),
        "num_step": args.num_step,
        "format": args.format,
        "predefined_voice": args.voice,
        "reference_audio": args.reference_audio,
        "samples_per_language": args.samples_per_language,
        "random_warmup": 0 if args.skip_prewarm else args.random_warmup,
        "reference_warmup": 0 if args.skip_prewarm else args.reference_warmup,
        "workload_items": len(workload),
        "language_count": len({item["language_slug"] for item in workload}),
        "seconds_wall": round(finished - started, 3),
        "status_before": status_before,
        "status_after": status_after,
        "summary": {
            "total": summarize_measurements(measurements),
            "by_round": grouped_summary(measurements, "round"),
            "by_language": grouped_summary(measurements, "language_slug"),
            "by_type": grouped_summary(measurements, "type"),
            "by_round_type": grouped_summary(
                [{**item, "round_type": f"{item['round']}.{item['type']}"} for item in measurements],
                "round_type",
            ),
        },
        "measurements": measurements,
    }
    append_results(args.results, run)
    write_markdown_index(args.markdown_dir / "BENCHMARKS.md")
    append_category_markdown(args.markdown_dir, run)
    print(f"Wrote benchmark results to {args.results}")
    print(f"Appended benchmark category summaries under {args.markdown_dir}")


if __name__ == "__main__":
    main()
