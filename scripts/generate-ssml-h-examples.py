from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "examples" / "assets" / "ssml-h"
EXAMPLES = (
    ("mother-daughter", "Mother and daughter"),
    ("model-meeting", "Morning model meeting"),
    ("moon-navigation", "Turn left at the moon"),
)


def generate(base_url: str, slug: str, title: str, timeout: int) -> None:
    document = (EXAMPLES_DIR / f"{slug}.ssml").read_text(encoding="utf-8")
    payload = json.dumps(
        {
            "text": document,
            "input_type": "ssml-h",
            "language": "english",
            "device": "auto",
            "output_format": "mp3",
            "num_step": 32,
            "seed": 24680,
            "randomize_seed": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/tts/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"Generating {title}...", flush=True)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{title} failed with HTTP {exc.code}: {detail}") from exc
    output = EXAMPLES_DIR / f"{slug}.mp3"
    output.write_bytes(audio)
    print(f"  wrote {output.relative_to(ROOT)} ({len(audio):,} bytes)", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the public OmniVoiceTTS SSML-H examples.")
    parser.add_argument("--base-url", default="http://localhost:7861")
    parser.add_argument("--name", choices=[slug for slug, _ in EXAMPLES])
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    selected = [item for item in EXAMPLES if not args.name or item[0] == args.name]
    try:
        for slug, title in selected:
            generate(args.base_url, slug, title, args.timeout)
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
