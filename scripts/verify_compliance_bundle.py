#!/usr/bin/env python3
"""Verify the source and license bundle shipped in an OmniVoiceTTS image."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tarfile
from importlib.metadata import version
from pathlib import Path


EXPECTED_PACKAGES = {
    "mcp": "2.3.0",
    "num2words": "0.5.14",
    "soxr": "1.1.0",
    "ssml-h-tools": "0.1.0",
    "torch": "2.8.0+cu128",
}

EXPECTED_ARCHIVES = {
    "sources/num2words-0.5.14.tar.gz": "num2words-0.5.14/",
    "sources/soxr-1.1.0.tar.gz": "soxr-1.1.0/",
}

REQUIRED_FILES = {
    "README.md",
    "SOURCE_MANIFEST.md",
    "PYTHON_PACKAGES.md",
    "SHA256SUMS",
    "licenses/omnivoice-model/MODEL_CARD.md",
    "licenses/boson-higgs-audio-2/LICENSE",
    "licenses/meta-llama-3/LICENSE",
    "licenses/openai-whisper/LICENSE",
    "licenses/project/LICENSE",
    "licenses/project/NOTICE",
    "licenses/browser/lucide-and-feather-LICENSE",
    "licenses/browser/wavesurfer-LICENSE",
    "licenses/python/mcp/LICENSE",
    "licenses/python/num2words/COPYING",
    "licenses/python/soxr/COPYING.LGPL",
    "licenses/python/soxr/LICENSE-libsoxr.txt",
    "licenses/python/soxr/LICENSE.txt",
    "licenses/python/ssml-h-tools/LICENSE",
    "licenses/python/ssml-h-tools/NOTICE",
    "licenses/python/torch/LICENSE",
    "licenses/python/torch/NOTICE",
    "licenses/debian/ffmpeg-copyright",
    "build/Dockerfile",
    "build/requirements.in",
    "build/requirements.txt",
    "build/pyproject.toml",
    "build/uv.lock",
    "build/install_compliance_bundle.py",
    "build/verify_compliance_bundle.py",
}

REQUIRED_ATTRIBUTION = (
    "Built with Meta Llama 3",
    "Built with Higgs Materials licensed from Boson AI USA, Inc., Copyright Boson",
    "Meta Llama 3 is licensed under the Meta Llama 3 Community License",
    "Boson Higgs Audio 2 is licensed under the Boson Community License",
)


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def verify_checksums(root: Path) -> int:
    count = 0
    for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"checksummed file is missing: {relative}")
        actual = digest(path)
        if actual != expected:
            raise RuntimeError(
                f"checksum mismatch for {relative}: expected {expected}, got {actual}"
            )
        count += 1
    return count


def installed_ffmpeg_rows() -> list[tuple[str, str]]:
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${binary:Package}\\t${Version}\\n"],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = []
    for line in result.stdout.splitlines():
        package, installed_version = line.split("\t")
        if package.split(":", 1)[0] == "ffmpeg":
            rows.append((package, installed_version))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default="/app/third_party")
    args = parser.parse_args()
    root = args.root.resolve()

    missing = sorted(relative for relative in REQUIRED_FILES if not (root / relative).is_file())
    if missing:
        raise RuntimeError(f"compliance bundle is missing: {', '.join(missing)}")

    checksummed = verify_checksums(root)
    for relative, prefix in EXPECTED_ARCHIVES.items():
        with tarfile.open(root / relative, "r:gz") as archive:
            names = archive.getnames()
        if not names or not all(
            name == prefix.rstrip("/") or name.startswith(prefix) for name in names
        ):
            raise RuntimeError(f"unexpected source archive layout: {relative}")

    for package, expected in EXPECTED_PACKAGES.items():
        actual = version(package)
        if actual != expected:
            raise RuntimeError(f"{package} version mismatch: expected {expected}, got {actual}")

    notices = (Path("/app/NOTICE")).read_text(encoding="utf-8")
    third_party_notices = (Path("/app/THIRD_PARTY_NOTICES.md")).read_text(encoding="utf-8")
    for required in REQUIRED_ATTRIBUTION:
        if required not in notices or required not in third_party_notices:
            raise RuntimeError(f"required attribution is missing: {required}")

    model_card = (root / "licenses/omnivoice-model/MODEL_CARD.md").read_text(
        encoding="utf-8"
    )
    if "pre-trained model is licensed under the CC-BY-NC" not in model_card:
        raise RuntimeError("reviewed OmniVoice model card license statement changed")

    manifest = (root / "SOURCE_MANIFEST.md").read_text(encoding="utf-8")
    for package, installed_version in installed_ffmpeg_rows():
        if f"| `{package}` | `{installed_version}` |" not in manifest:
            raise RuntimeError(f"FFmpeg package is not recorded: {package} {installed_version}")

    inventory = (root / "PYTHON_PACKAGES.md").read_text(encoding="utf-8").casefold()
    for required in ("num2words", "soxr", "ssml-h-tools", "torch", "nvidia-cublas"):
        if required not in inventory:
            raise RuntimeError(f"Python inventory does not mention {required}")

    nvidia_licenses = list((root / "licenses/python").glob("nvidia-*/License.txt"))
    if not nvidia_licenses:
        raise RuntimeError("NVIDIA wheel licenses are missing")

    print(
        f"Compliance bundle verified: {checksummed} checksums, "
        f"{len(EXPECTED_ARCHIVES)} source archives, "
        f"{len(EXPECTED_PACKAGES)} pinned Python packages, "
        f"{len(nvidia_licenses)} NVIDIA license files."
    )


if __name__ == "__main__":
    main()
