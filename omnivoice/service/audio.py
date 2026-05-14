from __future__ import annotations

import io
import subprocess
import tempfile
import wave
from collections.abc import Iterator

import numpy as np

SAMPLE_RATE = 24000

OUTPUT_FORMATS = {
    "wav": {
        "label": "WAV",
        "extension": "wav",
        "media_type": "audio/wav",
        "ffmpeg_args": None,
    },
    "mp3": {
        "label": "MP3",
        "extension": "mp3",
        "media_type": "audio/mpeg",
        "ffmpeg_args": ["-f", "mp3", "-codec:a", "libmp3lame", "-b:a", "192k"],
    },
    "flac": {
        "label": "FLAC",
        "extension": "flac",
        "media_type": "audio/flac",
        "ffmpeg_args": ["-f", "flac", "-codec:a", "flac"],
    },
    "ogg": {
        "label": "OGG Vorbis",
        "extension": "ogg",
        "media_type": "audio/ogg",
        "ffmpeg_args": ["-f", "ogg", "-codec:a", "libvorbis", "-q:a", "5"],
    },
}

FORMAT_ALIASES = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".ogg": "ogg",
    "mpeg": "mp3",
    "vorbis": "ogg",
    "opus": "ogg",
}


def to_int16_audio(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.int16:
        return audio
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    audio_int16 = to_int16_audio(audio)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    return buffer.getvalue()


def atempo_filters(multiplier: float) -> list[str]:
    filters = []
    current = multiplier
    while current > 2.0:
        filters.append("atempo=2.0")
        current /= 2.0
    while current < 0.5:
        filters.append("atempo=0.5")
        current /= 0.5
    filters.append(f"atempo={current:.6f}")
    return filters


def build_audio_effect_filters(
    sample_rate: int,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> list[str]:
    filters = []
    if abs(pitch_semitones) > 0.001:
        pitch_factor = 2 ** (pitch_semitones / 12)
        shifted_rate = max(1, int(round(sample_rate * pitch_factor)))
        filters.extend([f"asetrate={shifted_rate}", f"aresample={sample_rate}"])
        filters.extend(atempo_filters(1 / pitch_factor))
    if abs(tempo - 1.0) > 0.001:
        filters.extend(atempo_filters(tempo))
    if abs(volume - 1.0) > 0.001:
        filters.append(f"volume={volume:.6f}")
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    return filters


def apply_audio_effects(
    audio: np.ndarray,
    sample_rate: int,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> np.ndarray:
    filters = build_audio_effect_filters(sample_rate, pitch_semitones, tempo, volume, normalize)
    if not filters or audio.size == 0:
        return to_int16_audio(audio)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        "-af",
        ",".join(filters),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            command,
            input=audio_to_wav_bytes(audio, sample_rate),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for pitch, tempo, volume, or normalization controls") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to apply audio controls: {stderr}") from exc
    return np.frombuffer(result.stdout, dtype="<i2").astype(np.int16, copy=True)


def encode_audio_bytes(audio: np.ndarray, output_format: str = "wav", sample_rate: int = SAMPLE_RATE) -> bytes:
    normalized_format = FORMAT_ALIASES.get(output_format, output_format)
    wav_bytes = audio_to_wav_bytes(audio, sample_rate)
    ffmpeg_args = OUTPUT_FORMATS[normalized_format]["ffmpeg_args"]
    if ffmpeg_args is None:
        return wav_bytes
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        *ffmpeg_args,
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            command,
            input=wav_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for non-WAV output formats") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to encode {normalized_format}: {stderr}") from exc
    return result.stdout


def encode_audio_stream(
    chunks: Iterator[np.ndarray],
    output_format: str = "mp3",
    sample_rate: int = SAMPLE_RATE,
) -> Iterator[bytes]:
    normalized_format = FORMAT_ALIASES.get(output_format, output_format)
    ffmpeg_args = OUTPUT_FORMATS[normalized_format]["ffmpeg_args"]
    if ffmpeg_args is None:
        for chunk in chunks:
            yield audio_to_wav_bytes(chunk, sample_rate)
        return

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-i",
        "pipe:0",
        *ffmpeg_args,
        "pipe:1",
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"ffmpeg is required to stream {normalized_format}") from exc

    assert process.stdin is not None
    assert process.stdout is not None
    writer_error: list[BaseException] = []

    def write_chunks() -> None:
        try:
            for chunk in chunks:
                process.stdin.write(to_int16_audio(chunk).tobytes())
                process.stdin.flush()
        except BaseException as exc:  # noqa: BLE001 - surfaced after ffmpeg exits.
            writer_error.append(exc)
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    import threading
    writer = threading.Thread(target=write_chunks, daemon=True)
    writer.start()
    while True:
        data = process.stdout.read(65536)
        if data:
            yield data
            continue
        if process.poll() is not None:
            break

    writer.join()
    stderr = process.stderr.read().decode("utf-8", errors="replace").strip() if process.stderr else ""
    return_code = process.wait()
    if writer_error:
        raise RuntimeError(f"Audio streaming failed: {writer_error[0]}")
    if return_code != 0:
        raise RuntimeError(f"ffmpeg failed to stream {normalized_format}: {stderr}")


def encoded_audio_to_temp_file(audio: np.ndarray, output_format: str, sample_rate: int) -> str:
    normalized_format = FORMAT_ALIASES.get(output_format, output_format)
    extension = OUTPUT_FORMATS[normalized_format]["extension"]
    audio_bytes = encode_audio_bytes(audio, normalized_format, sample_rate)
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as file:
        file.write(audio_bytes)
        return file.name
