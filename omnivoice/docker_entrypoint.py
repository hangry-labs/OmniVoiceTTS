"""Seed immutable baked model assets, then start the OmniVoiceTTS server."""

from __future__ import annotations

import filecmp
import os
import shutil
import sys
from pathlib import Path


BAKED_HF_HOME = Path("/app/baked-models/huggingface")
DEFAULT_HF_HOME = Path("/app/persistent/models/huggingface")


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def seed_baked_model_cache(source: Path, destination: Path) -> tuple[int, int]:
    """Merge baked cache files without deleting user-downloaded model assets."""
    if not source.is_dir():
        return 0, 0

    copied_files = 0
    copied_bytes = 0
    destination.mkdir(parents=True, exist_ok=True)
    for source_path in source.rglob("*"):
        relative = source_path.relative_to(source)
        destination_path = destination / relative

        if source_path.is_symlink():
            target = os.readlink(source_path)
            if destination_path.is_symlink() and os.readlink(destination_path) == target:
                continue
            if destination_path.exists() or destination_path.is_symlink():
                _remove_existing(destination_path)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.symlink_to(target, target_is_directory=source_path.is_dir())
            copied_files += 1
            continue

        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue

        if destination_path.is_file() and destination_path.stat().st_size == source_path.stat().st_size:
            if "blobs" in relative.parts or filecmp.cmp(source_path, destination_path, shallow=False):
                continue
        if destination_path.exists() or destination_path.is_symlink():
            _remove_existing(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied_files += 1
        copied_bytes += source_path.stat().st_size

    return copied_files, copied_bytes


def main() -> None:
    destination = Path(os.getenv("HF_HOME", str(DEFAULT_HF_HOME)))
    copied_files, copied_bytes = seed_baked_model_cache(BAKED_HF_HOME, destination)
    if BAKED_HF_HOME.is_dir():
        print(
            "[startup] baked_model_cache_seed="
            f"files:{copied_files} bytes:{copied_bytes} destination:{destination}",
            flush=True,
        )
    os.execv(sys.executable, [sys.executable, "-u", "omnivoice/app.py"])


if __name__ == "__main__":
    main()
