from __future__ import annotations

from pathlib import Path

from omnivoice.service.audio import OUTPUT_FORMATS, normalize_audio_format


def resolve_audio_output_path(
    output_path: str | Path,
    output_format: str | None = None,
) -> tuple[Path, str]:
    """Resolve a CLI output format and keep the filename extension consistent."""
    path = Path(output_path).expanduser()
    if output_format is None:
        if path.suffix:
            normalized_format = normalize_audio_format(path.suffix)
        else:
            normalized_format = "wav"
    else:
        normalized_format = normalize_audio_format(output_format)

    extension = f".{OUTPUT_FORMATS[normalized_format]['extension']}"
    if path.suffix.lower() != extension:
        path = path.with_suffix(extension)
    return path, normalized_format
