from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

AUDIO_EXTENSIONS = {".flac", ".m4a", ".mp3", ".ogg", ".wav"}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def parse_path_roots(value: str | None, defaults: Iterable[str | Path]) -> list[Path]:
    raw_roots = [part.strip() for part in (value or "").split(",") if part.strip()]
    roots = raw_roots or [str(path) for path in defaults]
    return [Path(root).expanduser() for root in roots]


def is_path_within_root(path: Path, root: Path) -> bool:
    path_text = os.path.realpath(os.path.expanduser(os.fspath(path)))
    root_text = os.path.realpath(os.path.expanduser(os.fspath(root)))
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def safe_existing_file_path(
    path_value: str | os.PathLike,
    allowed_roots: Iterable[str | Path],
    *,
    label: str = "File path",
    allowed_extensions: set[str] | None = None,
) -> Path:
    raw_path = os.fspath(path_value)
    if not raw_path or "\x00" in raw_path:
        raise ValueError(f"{label} is not valid.")

    roots = list(allowed_roots)
    if not roots:
        raise ValueError(f"{label} access is disabled because no safe roots are configured.")

    expanded_path = os.path.expanduser(raw_path)
    resolved_path_text = os.path.realpath(expanded_path)
    resolved_root_texts = [
        os.path.realpath(os.path.expanduser(os.fspath(root)))
        for root in roots
    ]
    try:
        is_allowed = any(
            os.path.commonpath([resolved_path_text, resolved_root_text]) == resolved_root_text
            for resolved_root_text in resolved_root_texts
        )
    except ValueError:
        is_allowed = False
    if not is_allowed:
        root_list = ", ".join(str(Path(root)) for root in roots)
        raise ValueError(f"{label} must be inside one of these safe roots: {root_list}.")

    resolved_path = Path(resolved_path_text)
    if not resolved_path.exists():
        raise ValueError(f"{label} does not exist or is not accessible.")
    if not resolved_path.is_file():
        raise ValueError(f"{label} must point to an existing file.")
    if allowed_extensions is not None and resolved_path.suffix.lower() not in allowed_extensions:
        supported = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"{label} must use one of these extensions: {supported}.")
    return resolved_path


def secure_filename_stem(value: str | os.PathLike, *, default: str = "output") -> str:
    stem = Path(value).name
    if stem.lower().endswith(".wav"):
        stem = stem[:-4]
    stem = SAFE_FILENAME_PATTERN.sub("-", stem).strip(".-_")
    return stem[:120] or default


def safe_output_file_path(
    root: str | Path,
    filename_stem: str | os.PathLike,
    *,
    suffix: str = ".wav",
) -> Path:
    if not suffix.startswith("."):
        raise ValueError("Output file suffix must start with '.'.")
    resolved_root = Path(root).expanduser().resolve(strict=False)
    filename = f"{secure_filename_stem(filename_stem)}{suffix}"
    candidate = (resolved_root / filename).resolve(strict=False)
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError("Output file path must stay inside the result directory.")
    return candidate


def default_gradio_upload_roots() -> list[Path]:
    candidates = []
    gradio_temp_dir = os.getenv("GRADIO_TEMP_DIR", "").strip()
    if gradio_temp_dir:
        candidates.append(Path(gradio_temp_dir))
    tmp_dir = os.getenv("TMPDIR", "").strip()
    if tmp_dir:
        candidates.append(Path(tmp_dir) / "gradio")
    candidates.append(Path("/tmp/gradio"))
    return candidates
