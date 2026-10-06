#!/usr/bin/env python3
"""Assemble model licenses, dependency notices, and LGPL source archives."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from importlib.metadata import distribution, distributions
from pathlib import Path


@dataclass(frozen=True)
class Download:
    path: str
    url: str
    sha256: str
    size: int
    component: str


DOWNLOADS = (
    Download(
        path="sources/num2words-0.5.14.tar.gz",
        url=(
            "https://files.pythonhosted.org/packages/f6/58/"
            "ad645bd38b4b648eb2fc2ba1b909398e54eb0cbb6a7dbd2b4953e38c9621/"
            "num2words-0.5.14.tar.gz"
        ),
        sha256="b066ec18e56b6616a3b38086b5747daafbaa8868b226a36127e0451c0cf379c6",
        size=218_213,
        component="num2words 0.5.14 source (LGPL-2.1)",
    ),
    Download(
        path="sources/soxr-1.1.0.tar.gz",
        url=(
            "https://files.pythonhosted.org/packages/ed/11/"
            "27cebce4a108f77afea7c80545115536b45e3f11ebfb914f638fdd9ba847/"
            "soxr-1.1.0.tar.gz"
        ),
        sha256="9f228ae21c78fa9359ca98d8a5e8e91f30639e438e574133dace62c5b5309e44",
        size=173_067,
        component="Python-SoXR 1.1.0 source (LGPL-2.1-or-later)",
    ),
    Download(
        path="licenses/omnivoice-model/MODEL_CARD.md",
        url=(
            "https://huggingface.co/k2-fsa/OmniVoice/resolve/"
            "c5fdb5ccb189668d56333f77ba2629f4cd7535f4/README.md"
        ),
        sha256="b5d645a1874baa96a460a0e3a7d5a262811d682d04ce235878a16d5fed287fd3",
        size=9_424,
        component="OmniVoice reviewed model card",
    ),
    Download(
        path="licenses/boson-higgs-audio-2/LICENSE",
        url=(
            "https://huggingface.co/k2-fsa/OmniVoice/resolve/"
            "c5fdb5ccb189668d56333f77ba2629f4cd7535f4/"
            "audio_tokenizer/LICENSE"
        ),
        sha256="ac933dc084d119bd20401956b90d11ae87c248b2da62622cd580d82cdf2fa049",
        size=9_171,
        component="Boson Higgs Audio 2 Community License",
    ),
    Download(
        path="licenses/meta-llama-3/LICENSE",
        url=(
            "https://raw.githubusercontent.com/meta-llama/llama3/"
            "a0940f9cf7065d45bb6675660f80d305c041a754/LICENSE"
        ),
        sha256="4fa551d4f938f68b8c1e6afa9d28befb70e3f33f75d0753248d530364aeea40f",
        size=12_403,
        component="Meta Llama 3 Community License",
    ),
    Download(
        path="licenses/openai-whisper/LICENSE",
        url=(
            "https://raw.githubusercontent.com/openai/whisper/"
            "86098128c0b4f24f0e2aa2994de830614b474227/LICENSE"
        ),
        sha256="b5d65a59060e68c4ff940e1eddfa6f94b2d68fdf58ed7f4dd57721c997e35e9d",
        size=1_063,
        component="OpenAI Whisper MIT license",
    ),
)

FFMPEG_PACKAGE_PREFIXES = (
    "libavcodec",
    "libavdevice",
    "libavfilter",
    "libavformat",
    "libavutil",
    "libpostproc",
    "libswresample",
    "libswscale",
)


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def download(item: Download, output: Path) -> None:
    destination = output / item.path
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        item.url,
        headers={"User-Agent": "HangryLabs-OmniVoiceTTS-license-bundle"},
    )
    for attempt in range(1, 4):
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.unlink(missing_ok=True)
        try:
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                temporary.open("wb") as target,
            ):
                shutil.copyfileobj(response, target)
            actual_size = temporary.stat().st_size
            actual_digest = digest(temporary)
            if actual_size != item.size or actual_digest != item.sha256:
                raise RuntimeError(
                    f"integrity mismatch for {item.path}: expected "
                    f"{item.size}/{item.sha256}, got {actual_size}/{actual_digest}"
                )
            temporary.replace(destination)
            print(f"Installed {item.component}: {item.path}", file=sys.stderr)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(attempt * 2)


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"required compliance file is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_distribution_licenses(package: str, output: Path) -> int:
    package_distribution = distribution(package)
    copied = 0
    for entry in package_distribution.files or ():
        normalized = str(entry).replace("\\", "/")
        filename = Path(normalized).name
        if not any(token in filename.upper() for token in ("LICENSE", "COPYING", "NOTICE")):
            continue
        source = Path(package_distribution.locate_file(entry))
        if not source.is_file():
            continue
        destination = output / "licenses" / "python" / package / filename
        copy_file(source, destination)
        copied += 1
    if copied == 0:
        raise RuntimeError(f"no installed license files found for {package}")
    return copied


def installed_ffmpeg_packages() -> list[tuple[str, str, str, str]]:
    result = subprocess.run(
        [
            "dpkg-query",
            "-W",
            "-f=${binary:Package}\\t${Version}\\t${source:Package}\\t${source:Version}\\n",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    packages: list[tuple[str, str, str, str]] = []
    for line in result.stdout.splitlines():
        binary, version, source, source_version = line.split("\t")
        plain_binary = binary.split(":", 1)[0]
        if plain_binary != "ffmpeg" and not plain_binary.startswith(FFMPEG_PACKAGE_PREFIXES):
            continue
        packages.append(
            (
                binary,
                version,
                source or plain_binary,
                source_version or version,
            )
        )
    if not any(package[0].split(":", 1)[0] == "ffmpeg" for package in packages):
        raise RuntimeError("ffmpeg is not installed")
    return packages


def write_source_manifest(
    output: Path, ffmpeg_packages: list[tuple[str, str, str, str]]
) -> None:
    lines = [
        "# Source And License Manifest",
        "",
        "This manifest records the exact compliance material assembled for the",
        "OmniVoiceTTS Docker image. It does not change any component's license.",
        "",
        "## Downloaded Material",
        "",
        "| Component | File | SHA-256 | Primary source |",
        "| --- | --- | --- | --- |",
    ]
    for item in DOWNLOADS:
        lines.append(
            f"| {item.component} | `{item.path}` | `{item.sha256}` | "
            f"[source]({item.url}) |"
        )
    lines.extend(
        [
            "",
            "## Project Source",
            "",
            "The corresponding Hangry Labs source and complete build inputs are at",
            "https://github.com/Hangry-Labs/OmniVoiceTTS. The image retains its",
            "Dockerfile, dependency locks, package manifest, and bundle installer",
            "under `/app/third_party/build`.",
            "",
            "## Debian FFmpeg Runtime",
            "",
            "| Binary package | Installed version | Source package | Exact source |",
            "| --- | --- | --- | --- |",
        ]
    )
    seen_sources: set[tuple[str, str]] = set()
    for binary, version, source, source_version in ffmpeg_packages:
        key = (source, source_version)
        encoded = urllib.parse.quote(source_version, safe="")
        url = f"https://sources.debian.org/src/{source}/{encoded}/"
        source_link = f"[Debian source]({url})" if key not in seen_sources else "same source"
        lines.append(
            f"| `{binary}` | `{version}` | `{source}` `{source_version}` | {source_link} |"
        )
        seen_sources.add(key)
    lines.extend(
        [
            "",
            "The installed Debian copyright record is copied under `licenses/debian`.",
            "The normal `/usr/share/doc` and `/usr/share/common-licenses` trees are",
            "also retained in the runtime image.",
            "",
            "## Verification",
            "",
            "Run `/app/third_party/build/verify_compliance_bundle.py` inside the",
            "image. `SHA256SUMS` covers every copied source and license file.",
            "",
        ]
    )
    (output / "SOURCE_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def table_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def write_python_inventory(output: Path) -> None:
    lines = [
        "# Installed Python Package License Inventory",
        "",
        "Generated from the distributions installed in this image. `UNKNOWN` means",
        "the package metadata did not declare useful license information; it does",
        "not mean that the package is unlicensed.",
        "",
        "| Package | Version | Declared license | Project |",
        "| --- | --- | --- | --- |",
    ]
    rows: list[tuple[str, str]] = []
    for package_distribution in distributions():
        metadata = package_distribution.metadata
        name = metadata.get("Name", "UNKNOWN")
        expression = metadata.get("License-Expression")
        classifiers = [
            value.removeprefix("License :: ")
            for value in metadata.get_all("Classifier", [])
            if value.startswith("License :: ")
        ]
        declared = expression or "; ".join(classifiers)
        if not declared:
            raw_license = metadata.get("License", "").strip()
            declared = raw_license if len(raw_license) <= 160 else raw_license.splitlines()[0]
        declared = declared or "UNKNOWN"

        project_url = metadata.get("Home-page", "").strip()
        if not project_url:
            for entry in metadata.get_all("Project-URL", []):
                _, separator, candidate = entry.partition(",")
                if separator and candidate.strip().startswith(("http://", "https://")):
                    project_url = candidate.strip()
                    break
        project = f"[upstream]({project_url})" if project_url else "UNKNOWN"
        rows.append(
            (
                name.casefold(),
                f"| `{table_cell(name)}` | `{package_distribution.version}` | "
                f"{table_cell(declared)} | {project} |",
            )
        )
    lines.extend(row for _, row in sorted(rows))
    lines.append("")
    (output / "PYTHON_PACKAGES.md").write_text("\n".join(lines), encoding="utf-8")


def write_checksums(output: Path) -> None:
    files = sorted(
        path
        for directory in (output / "sources", output / "licenses")
        for path in directory.rglob("*")
        if path.is_file()
    )
    lines = [f"{digest(path)}  {path.relative_to(output).as_posix()}" for path in files]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    for item in DOWNLOADS:
        download(item, output)

    for package in ("num2words", "soxr", "ssml-h-tools", "torch"):
        copy_distribution_licenses(package, output)
    for package_distribution in distributions():
        name = package_distribution.metadata.get("Name", "")
        if name.casefold().startswith("nvidia-"):
            copy_distribution_licenses(name, output)

    copy_file(Path("/app/LICENSE"), output / "licenses/project/LICENSE")
    copy_file(Path("/app/NOTICE"), output / "licenses/project/NOTICE")
    copy_file(
        Path("/app/omnivoice/standalone_ui/static/vendor/lucide/LICENSE"),
        output / "licenses/browser/lucide-and-feather-LICENSE",
    )
    copy_file(
        Path("/app/omnivoice/standalone_ui/static/vendor/wavesurfer/LICENSE"),
        output / "licenses/browser/wavesurfer-LICENSE",
    )
    copy_file(
        Path("/usr/share/doc/ffmpeg/copyright"),
        output / "licenses/debian/ffmpeg-copyright",
    )
    for name in ("GPL-2", "GPL-3", "LGPL-2.1"):
        source = Path("/usr/share/common-licenses") / name
        if source.is_file():
            copy_file(source, output / "licenses/debian" / name)

    ffmpeg_packages = installed_ffmpeg_packages()
    write_source_manifest(output, ffmpeg_packages)
    write_python_inventory(output)
    write_checksums(output)


if __name__ == "__main__":
    main()

