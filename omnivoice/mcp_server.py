"""Opt-in compact and advanced Streamable HTTP MCP surfaces."""

from __future__ import annotations

import asyncio
import os
import platform
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Callable, Literal
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from omnivoice import __version__
from omnivoice.artifacts import (
    ArtifactExpiredError,
    ArtifactNotFoundError,
    ArtifactStore,
    MAX_ARTIFACT_TTL_SECONDS,
    MIN_ARTIFACT_TTL_SECONDS,
)
from omnivoice.remote_audio import RemoteAudioError, RemoteAudioFetcher
from omnivoice.service.audio import OUTPUT_FORMATS, audio_to_wav_bytes, encode_audio_bytes
from omnivoice.service.paths import AUDIO_EXTENSIONS
from omnivoice.service.schemas import MAX_RANDOM_SEED, TTSRequest
from omnivoice.service.ssml import (
    DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE,
    DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT,
)


_RUNTIME: Any | None = None
DEFAULT_MCP_INPUT_DIR = "/app/persistent/mcp-input"
DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
    "[::1]",
    "[::1]:*",
    "host.docker.internal",
    "host.docker.internal:*",
]
DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1",
    "http://127.0.0.1:*",
    "http://localhost",
    "http://localhost:*",
    "https://127.0.0.1",
    "https://127.0.0.1:*",
    "https://localhost",
    "https://localhost:*",
]
DEFAULT_AUDIO_URL_ALLOWED_HOSTS = ["*"]
ARTIFACT_CLEANUP_INTERVAL_SECONDS = 60
MAX_REFERENCE_AUDIO_BYTES = 64 * 1024 * 1024
VoiceMode = Literal["random", "cloned", "design", "reference", "document"]
InputType = Literal["text", "ssml", "ssml-h"]
OutputFormat = Literal["mp3", "wav", "flac", "ogg"]


class GeneratedSpeechLink(BaseModel):
    download_url: str
    expires_at: str
    ttl_seconds: int
    format: str
    mime_type: str
    size_bytes: int
    duration_seconds: float
    sample_rate: int
    seed: int
    voice_mode: str
    voice: str
    language: str
    created_profiles: list[str]


class MCPAccessGate:
    def __init__(
        self,
        app: Any,
        *,
        enabled: Callable[[], bool],
        label: str,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.label = label

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http" and not self.enabled():
            response = JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "message": (
                            f"{self.label} MCP access is disabled. Enable it in the "
                            "OmniVoiceTTS System tab, then reconnect and retry."
                        ),
                        "type": "mcp_access_forbidden",
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class MCPApplicationSlot:
    """Dispatch to the MCP app created for the current ASGI lifespan."""

    def __init__(self) -> None:
        self.app: Any | None = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if self.app is None:
            response = JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "message": "MCP is starting. Reconnect and retry.",
                        "type": "mcp_not_ready",
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _runtime():
    if _RUNTIME is None:
        raise RuntimeError("MCP runtime is not configured. Mount MCP with attach_mcp first.")
    return _RUNTIME


def _enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _csv_setting(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _positive_float_setting(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def _nonnegative_int_setting(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 0:
        raise RuntimeError(f"{name} cannot be negative")
    return value


def _download_base_url() -> str:
    configured = os.getenv("OMNIVOICE_MCP_BASE_URL", "").strip()
    base_url = configured or f"http://localhost:{os.getenv('PORT', '7861')}"
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "OMNIVOICE_MCP_BASE_URL must be an absolute http:// or https:// URL"
        )
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RuntimeError(
            "OMNIVOICE_MCP_BASE_URL must not contain credentials, a path, a query, or a fragment"
        )
    return base_url.rstrip("/")


def _allowed_hosts(base_url: str) -> list[str]:
    configured = _csv_setting("OMNIVOICE_MCP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS)
    return list(dict.fromkeys([*configured, urlsplit(base_url).netloc]))


def _configured_input_directory(value: str | Path | None = None) -> Path | None:
    raw = str(value).strip() if value is not None else os.getenv(
        "OMNIVOICE_MCP_INPUT_DIR", DEFAULT_MCP_INPUT_DIR
    ).strip()
    return Path(raw).resolve() if raw else None


def _tool_error(exc: Exception, correction: str) -> ToolError:
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    else:
        detail = str(exc) or exc.__class__.__name__
    return ToolError(f"{detail} {correction}")


def _profile_catalog() -> list[dict[str, Any]]:
    catalog = []
    for profile in _runtime().voice_profile_payloads():
        description = str(profile.get("description") or "").strip()
        language = str(profile.get("language") or "").strip()
        profile_type = str(profile.get("profile_type") or "cloned")
        if not description:
            description = (
                f"Saved {profile_type} voice"
                + (f" for {language}" if language else "")
                + "."
            )
        catalog.append(
            {
                "id": profile["id"],
                "description": description,
                "profile_type": profile_type,
                "language": language or "request/default",
                "seed": profile.get("seed"),
                "randomize_seed": bool(profile.get("randomize_seed", False)),
                "has_transcript": bool(profile.get("has_transcript", False)),
            }
        )
    return catalog


def _resolve_profile(profile_id: str) -> dict[str, Any]:
    normalized = _runtime().normalize_profile_name(profile_id)
    profiles = _runtime().load_openai_voice_profiles()
    profile = profiles.get(normalized)
    if profile is None:
        raise ToolError(
            f"Saved cloned voice '{normalized}' does not exist. Call "
            "get_cloned_voices_catalog and retry with an exact returned id, or use 'auto'."
        )
    return profile


def _profile_tts_fields(profile_id: str) -> dict[str, Any]:
    profile = _resolve_profile(profile_id)
    randomize_seed = bool(profile.get("randomize_seed", False))
    raw_seed = profile.get("seed")
    seed = None if randomize_seed or raw_seed in {None, ""} else int(raw_seed)
    return {
        "voice": profile_id,
        "voice_profile": profile_id,
        "language": profile.get("language") or None,
        "seed": seed,
        "randomize_seed": randomize_seed,
    }


def _profile_exists(name: str, replace: bool) -> str:
    normalized = _runtime().normalize_profile_name(name)
    if normalized in _runtime().load_openai_voice_profiles() and not replace:
        raise ToolError(
            f"Saved voice '{normalized}' already exists. Retry with replace=true only if the user "
            "asked to replace that voice."
        )
    return normalized


def _profile_public(profile_id: str) -> dict[str, Any]:
    return next(item for item in _profile_catalog() if item["id"] == profile_id)


@asynccontextmanager
async def _materialized_audio(
    audio_location: str,
    *,
    input_directory: Path | None,
    fetcher: RemoteAudioFetcher,
):
    runtime = _runtime()
    temporary_path: Path | None = None
    reference = audio_location.strip()
    if not reference:
        raise ToolError("audio_location must not be empty.")
    try:
        if "://" in reference:
            try:
                downloaded = await fetcher.fetch(reference)
            except RemoteAudioError as exc:
                raise ToolError(str(exc)) from exc
            payload = downloaded.payload
            suffix = Path(downloaded.filename).suffix.lower()
        else:
            if input_directory is None:
                raise ToolError(
                    "Local reference paths are disabled. Configure OMNIVOICE_MCP_INPUT_DIR or use "
                    "an allowed HTTP(S) URL."
                )
            requested = Path(reference)
            resolved = (requested if requested.is_absolute() else input_directory / requested).resolve()
            try:
                resolved.relative_to(input_directory)
            except ValueError as exc:
                raise ToolError(
                    f"audio_location must stay inside the configured MCP input directory "
                    f"'{input_directory}'. Use a relative file path from that directory or an "
                    "allowed HTTP(S) URL."
                ) from exc
            if not resolved.is_file():
                raise ToolError(
                    f"The requested reference audio file was not found inside the MCP input "
                    f"directory '{input_directory}'. Place it there and retry with its relative "
                    "path, or provide an allowed HTTP(S) URL."
                )
            if resolved.stat().st_size > MAX_REFERENCE_AUDIO_BYTES:
                raise ToolError("Reference audio exceeds the configured 64 MiB limit.")
            payload = await asyncio.to_thread(resolved.read_bytes)
            suffix = resolved.suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            raise ToolError(
                "Reference audio must use WAV, MP3, FLAC, OGG, or M4A."
            )
        runtime.UI_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="mcp-reference-", suffix=suffix, dir=runtime.UI_UPLOAD_DIR
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        await asyncio.to_thread(temporary_path.write_bytes, payload)
        yield temporary_path
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _speech_payload(
    *,
    text: str,
    input_type: InputType,
    voice_mode: VoiceMode,
    voice_id: str,
    voice_instruction: str,
    reference_audio_path: str | None,
    reference_text: str,
    language: str,
    output_format: OutputFormat,
    seed: int,
    randomize_seed: bool,
    speed: float,
    pitch_semitones: float,
    tempo: float,
    volume: float,
    normalize_text: bool,
    normalize: bool,
    pad_duration: float,
    fade_duration: float,
) -> TTSRequest:
    if input_type != "text" and voice_mode != "document":
        raise ToolError("SSML and SSML-H input require voice_mode='document'.")
    if input_type == "text" and voice_mode == "document":
        raise ToolError("voice_mode='document' requires input_type='ssml' or 'ssml-h'.")
    values: dict[str, Any] = {
        "text": text,
        "input_type": input_type,
        "language": None if language.strip().lower() == "auto" else language.strip(),
        "output_format": output_format,
        "seed": seed,
        "randomize_seed": randomize_seed,
        "speed": speed,
        "pitch_semitones": pitch_semitones,
        "tempo": tempo,
        "volume": volume,
        "normalize_text": normalize_text,
        "normalize": normalize,
        "pad_duration": pad_duration,
        "fade_duration": fade_duration,
    }
    if voice_mode == "cloned":
        values.update(_profile_tts_fields(voice_id))
        if language.strip().lower() != "auto":
            values["language"] = language.strip()
        values["seed"] = seed
        values["randomize_seed"] = randomize_seed
    elif voice_mode == "design":
        if not voice_instruction.strip():
            raise ToolError("voice_instruction is required when voice_mode='design'.")
        values["instruct"] = voice_instruction.strip()
    elif voice_mode == "reference":
        if not reference_audio_path:
            raise ToolError("reference_audio_location is required when voice_mode='reference'.")
        values["ref_audio"] = reference_audio_path
        values["ref_text"] = reference_text.strip() or None
    return TTSRequest(**values)


async def _generate_link(
    payload: TTSRequest,
    *,
    artifact_store: ArtifactStore,
    base_url: str,
    ttl_seconds: int,
    voice_mode: str,
    voice: str,
) -> GeneratedSpeechLink:
    runtime = _runtime()
    try:
        output_format, sample_rate, waveform, used_seed, created_profiles = (
            await asyncio.to_thread(runtime.synthesize_complete_payload, payload)
        )
        audio = await asyncio.to_thread(
            encode_audio_bytes, waveform, output_format, sample_rate
        )
        config = OUTPUT_FORMATS[output_format]
        artifact = await asyncio.to_thread(
            artifact_store.create,
            audio,
            extension=str(config["extension"]),
            ttl_seconds=ttl_seconds,
            format=output_format,
            mime_type=str(config["media_type"]),
            duration_seconds=len(waveform) / sample_rate if sample_rate else 0,
            sample_rate=sample_rate,
            seed=used_seed,
            voice_mode=voice_mode,
            voice=voice,
            language=payload.language or "auto",
            created_profiles=created_profiles,
        )
    except Exception as exc:
        raise _tool_error(
            exc,
            "Correct the language, voice, document, reference, or control named in the error and retry.",
        ) from exc
    return GeneratedSpeechLink.model_validate(
        artifact.public_metadata(f"{base_url}/tts/artifacts/{artifact.token}")
    )


def create_mcp_server(
    *,
    artifact_store: ArtifactStore,
    base_url: str,
    advanced: bool,
    input_directory: Path | None = None,
    audio_url_transport: httpx.AsyncBaseTransport | None = None,
) -> MCPServer[Any]:
    runtime = _runtime()
    started_at = time.monotonic()
    mounted_input = _configured_input_directory(input_directory)
    if mounted_input is not None:
        mounted_input.mkdir(parents=True, exist_ok=True)
    fetcher = RemoteAudioFetcher(
        max_bytes=MAX_REFERENCE_AUDIO_BYTES,
        allowed_hosts=_csv_setting(
            "OMNIVOICE_MCP_AUDIO_URL_ALLOWED_HOSTS", DEFAULT_AUDIO_URL_ALLOWED_HOSTS
        ),
        timeout_seconds=_positive_float_setting(
            "OMNIVOICE_MCP_AUDIO_URL_TIMEOUT_SECONDS", 60.0
        ),
        max_redirects=_nonnegative_int_setting(
            "OMNIVOICE_MCP_AUDIO_URL_MAX_REDIRECTS", 3
        ),
        transport=audio_url_transport,
    )
    endpoint = "/mcp/advanced/" if advanced else "/mcp/"
    tier = "advanced" if advanced else "compact"
    instructions = (
        "Call talk_simple directly for normal plain-text MP3 speech. Use voice_id='auto' without "
        "a discovery call, or call get_cloned_voices_catalog for an exact saved voice id. "
        "Generated speech returns an expiring HTTP link and metadata, never audio bytes or base64. "
        "Use find_languages only when an exact accepted language value is uncertain."
    )
    if advanced:
        instructions += (
            " Use talk_advanced only for SSML/SSML-H, voice design, one-off reference cloning, "
            "custom formats, seeds, or mastering controls. Profile mutation tools change persistent "
            "storage and must only be called when the user requests it."
        )
    mcp: MCPServer[Any] = MCPServer(
        f"omnivoicetts-{tier}",
        title=f"OmniVoiceTTS {tier.title()} by Hangry Labs",
        description=(
            f"{tier.title()} local multilingual speech synthesis with expiring audio links"
            + (", voice design, cloning, and saved-profile management." if advanced else ".")
        ),
        instructions=instructions,
        website_url="https://hangrylabs.app/software/omnivoicetts",
        version=runtime.APP_VERSION or __version__,
    )
    read_only = ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
    generation = ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
    )
    external_generation = ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
    mutation = ToolAnnotations(
        readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
    )
    external_mutation = ToolAnnotations(
        readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
    )

    @mcp.tool(
        title="Get OmniVoiceTTS deployment health",
        description=(
            "Inspect product identity, readiness, device and memory state, model/cache state, "
            "persistent storage, formats, and both MCP endpoint settings."
        ),
        annotations=read_only,
        structured_output=True,
    )
    async def get_health() -> dict[str, Any]:
        status, gpu = await asyncio.gather(
            asyncio.to_thread(runtime.get_status_payload),
            asyncio.to_thread(runtime.GPU_MONITOR.request_snapshot),
        )
        return {
            "status": "ok",
            "product": {
                "name": "OmniVoiceTTS",
                "version": runtime.APP_VERSION,
                "package_version": __version__,
                "python_version": platform.python_version(),
                "uptime_seconds": round(time.monotonic() - started_at, 3),
            },
            "runtime": status,
            "gpu": list(gpu.get("gpus") or []),
            "mcp": {
                "tier": tier,
                "endpoint": endpoint,
                "compact_enabled": runtime.RUNTIME_SETTINGS.mcp_enabled(
                    default=_enabled("OMNIVOICE_ENABLE_MCP")
                ),
                "advanced_enabled": runtime.RUNTIME_SETTINGS.mcp_advanced_enabled(
                    default=_enabled("OMNIVOICE_ENABLE_ADVANCED_MCP")
                ),
                "download_base_url": base_url,
                "output_directory": str(artifact_store.directory),
                "input_directory": str(mounted_input) if mounted_input else None,
                "url_reference_available": fetcher.enabled,
                "minimum_ttl_seconds": MIN_ARTIFACT_TTL_SECONDS,
                "maximum_ttl_seconds": MAX_ARTIFACT_TTL_SECONDS,
                "returns_raw_audio": False,
            },
        }

    @mcp.tool(
        title="Find supported languages",
        description=(
            "Search OmniVoiceTTS's 646-language catalog by language name or id. Use this only "
            "when the exact accepted language is uncertain; talk_simple also accepts 'auto'."
        ),
        annotations=read_only,
        structured_output=True,
    )
    async def find_languages(
        query: Annotated[str, Field(max_length=100, description="Language name or id to search.")],
        limit: Annotated[
            int, Field(ge=1, le=50, description="Maximum matches to return.")
        ] = 10,
    ) -> dict[str, Any]:
        needle = query.strip().casefold()
        choices = sorted(
            (
                {"id": runtime.LANG_NAME_TO_ID[name], "name": runtime.lang_display_name(name)}
                for name in runtime.LANG_NAMES
            ),
            key=lambda item: (item["name"].casefold(), item["id"]),
        )
        matches = [
            item
            for item in choices
            if not needle
            or needle in item["name"].casefold()
            or needle in item["id"].casefold()
        ][:limit]
        return {"query": query, "count": len(matches), "languages": matches}

    @mcp.tool(
        title="Get saved cloned voices catalog",
        description=(
            "Return only reusable voices stored by this deployment, with the exact id accepted by "
            "talk_simple/talk_advanced and a human description of when to use each voice. An empty "
            "catalog means no reusable voice has been saved; use voice_id='auto' instead."
        ),
        annotations=read_only,
        structured_output=True,
    )
    async def get_cloned_voices_catalog() -> dict[str, Any]:
        voices = _profile_catalog()
        return {
            "count": len(voices),
            "voices": voices,
            "usage": "Pass an exact id as voice_id, or use 'auto' without a saved voice.",
        }

    @mcp.tool(
        title="Inspect text or speech markup without generating audio",
        description=(
            "Validate plain text, SSML, or SSML-H and return normalization, size, voice, language, "
            "speech-unit, and break metrics before expensive synthesis."
        ),
        annotations=read_only,
        structured_output=True,
    )
    async def inspect_speech(
        text: Annotated[str, Field(min_length=1, max_length=50_000)],
        input_type: InputType = "text",
        language: Annotated[
            str, Field(description="Language name/id or 'auto'.")
        ] = "auto",
        voice_id: Annotated[
            str,
            Field(description="Use 'auto' or an exact id from get_cloned_voices_catalog."),
        ] = "auto",
        normalize_text: bool = False,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {
            "text": text,
            "input_type": input_type,
            "language": None if language.strip().lower() == "auto" else language,
            "normalize_text": normalize_text,
        }
        if voice_id.strip().lower() != "auto":
            values.update(_profile_tts_fields(voice_id))
            if language.strip().lower() != "auto":
                values["language"] = language
        try:
            return await asyncio.to_thread(runtime.metrics, TTSRequest(**values))
        except Exception as exc:
            raise _tool_error(exc, "Correct the document, language, or voice id and retry.") from exc

    @mcp.tool(
        title="Talk with simple recommended settings",
        description=(
            "Preferred speech tool. Generate neutral plain-text MP3 speech using voice_id='auto' "
            "or one exact saved id from get_cloned_voices_catalog. It needs no health or catalog "
            "call when 'auto' is suitable. Returns an expiring URL, never raw audio or base64."
        ),
        annotations=generation,
        structured_output=True,
    )
    async def talk_simple(
        text: Annotated[
            str,
            Field(
                min_length=1,
                max_length=50_000,
                description="Exact speech text requested by the user. Pass it verbatim; do not paraphrase.",
            ),
        ],
        language: Annotated[
            str, Field(description="Language name/id or 'auto'.")
        ] = "auto",
        voice_id: Annotated[
            str,
            Field(description="Use 'auto' or an exact id from get_cloned_voices_catalog."),
        ] = "auto",
        ttl_seconds: Annotated[
            int,
            Field(ge=MIN_ARTIFACT_TTL_SECONDS, le=MAX_ARTIFACT_TTL_SECONDS),
        ] = 3600,
    ) -> GeneratedSpeechLink:
        values: dict[str, Any] = {
            "text": text,
            "language": None if language.strip().lower() == "auto" else language,
            "output_format": "mp3",
            "seed": 42,
            "randomize_seed": False,
        }
        mode = "random"
        selected_voice = "auto"
        if voice_id.strip().lower() != "auto":
            values.update(_profile_tts_fields(voice_id))
            if language.strip().lower() != "auto":
                values["language"] = language
            mode = "cloned"
            selected_voice = runtime.normalize_profile_name(voice_id)
        return await _generate_link(
            TTSRequest(**values),
            artifact_store=artifact_store,
            base_url=base_url,
            ttl_seconds=ttl_seconds,
            voice_mode=mode,
            voice=selected_voice,
        )

    if advanced:

        @mcp.tool(
            title="Talk with advanced OmniVoice controls",
            description=(
                "Generate text, SSML, or SSML-H using random, saved cloned, designed, one-off "
                "reference, or document-defined voices. Every argument is explicit. Empty strings "
                "are required for mode-specific fields that are not used. Prefer talk_simple for "
                "ordinary speech."
            ),
            annotations=external_generation,
            structured_output=True,
        )
        async def talk_advanced(
            text: Annotated[
                str,
                Field(
                    min_length=1,
                    max_length=50_000,
                    description=(
                        "Exact text, SSML, or SSML-H requested by the user. Pass it verbatim; "
                        "do not paraphrase or rewrite markup."
                    ),
                ),
            ],
            input_type: InputType,
            voice_mode: VoiceMode,
            voice_id: str,
            voice_instruction: Annotated[str, Field(max_length=500)],
            reference_audio_location: str,
            reference_text: Annotated[str, Field(max_length=20_000)],
            language: str,
            output_format: OutputFormat,
            ttl_seconds: Annotated[
                int,
                Field(ge=MIN_ARTIFACT_TTL_SECONDS, le=MAX_ARTIFACT_TTL_SECONDS),
            ],
            seed: Annotated[int, Field(ge=0, le=MAX_RANDOM_SEED)],
            randomize_seed: bool,
            speed: Annotated[float, Field(ge=0.5, le=1.5)],
            pitch_semitones: Annotated[float, Field(ge=-12, le=12)],
            tempo: Annotated[float, Field(ge=0.5, le=2.0)],
            volume: Annotated[float, Field(ge=0, le=2.0)],
            normalize_text: bool,
            normalize: bool,
            pad_duration: Annotated[float, Field(ge=0, le=5)],
            fade_duration: Annotated[float, Field(ge=0, le=5)],
        ) -> GeneratedSpeechLink:
            async def run(reference_path: str | None) -> GeneratedSpeechLink:
                payload = _speech_payload(
                    text=text,
                    input_type=input_type,
                    voice_mode=voice_mode,
                    voice_id=voice_id,
                    voice_instruction=voice_instruction,
                    reference_audio_path=reference_path,
                    reference_text=reference_text,
                    language=language,
                    output_format=output_format,
                    seed=seed,
                    randomize_seed=randomize_seed,
                    speed=speed,
                    pitch_semitones=pitch_semitones,
                    tempo=tempo,
                    volume=volume,
                    normalize_text=normalize_text,
                    normalize=normalize,
                    pad_duration=pad_duration,
                    fade_duration=fade_duration,
                )
                selected_voice = (
                    runtime.normalize_profile_name(voice_id)
                    if voice_mode == "cloned"
                    else voice_instruction.strip()
                    if voice_mode == "design"
                    else "reference-audio"
                    if voice_mode == "reference"
                    else "document"
                    if voice_mode == "document"
                    else "auto"
                )
                return await _generate_link(
                    payload,
                    artifact_store=artifact_store,
                    base_url=base_url,
                    ttl_seconds=ttl_seconds,
                    voice_mode=voice_mode,
                    voice=selected_voice,
                )

            if voice_mode == "reference":
                async with _materialized_audio(
                    reference_audio_location,
                    input_directory=mounted_input,
                    fetcher=fetcher,
                ) as reference_path:
                    return await run(str(reference_path))
            return await run(None)

        @mcp.tool(
            title="Create a saved cloned voice",
            description=(
                "Save a reusable cloned voice from audio in the MCP input directory or an allowed "
                "HTTP(S) URL. description tells future agents what the voice sounds like and when "
                "to use it. Supplying the exact transcript avoids loading ASR."
            ),
            annotations=external_mutation,
            structured_output=True,
        )
        async def create_cloned_voice_profile(
            name: Annotated[str, Field(min_length=1, max_length=48)],
            description: Annotated[str, Field(min_length=1, max_length=240)],
            audio_location: str,
            reference_text: Annotated[str, Field(max_length=20_000)],
            language: str,
            seed: Annotated[int, Field(ge=0, le=MAX_RANDOM_SEED)],
            replace: bool,
        ) -> dict[str, Any]:
            profile_id = _profile_exists(name, replace)
            async with _materialized_audio(
                audio_location, input_directory=mounted_input, fetcher=fetcher
            ) as reference_path:
                try:
                    analysis = await asyncio.to_thread(
                        runtime.reference_audio_analysis, reference_path
                    )
                    saved = await asyncio.to_thread(
                        runtime.save_openai_voice_profile,
                        profile_id,
                        str(reference_path),
                        reference_text,
                        language,
                        seed,
                        False,
                        description,
                        "cloned",
                    )
                    runtime.clear_voice_clone_prompt_cache()
                except Exception as exc:
                    raise _tool_error(exc, "Correct the profile metadata or reference and retry.") from exc
            return {"status": "saved", "voice": _profile_public(saved), "analysis": analysis}

        @mcp.tool(
            title="Create a saved designed voice",
            description=(
                "Generate and save a reusable voice from an OmniVoice voice-design instruction. "
                "description tells future agents what the voice represents and when to use it. An "
                "empty sample_text uses the stable internal six-second English sample."
            ),
            annotations=mutation,
            structured_output=True,
        )
        async def create_designed_voice_profile(
            name: Annotated[str, Field(min_length=1, max_length=48)],
            description: Annotated[str, Field(min_length=1, max_length=240)],
            voice_instruction: Annotated[str, Field(min_length=1, max_length=500)],
            sample_text: Annotated[str, Field(max_length=2_000)],
            language: str,
            seed: Annotated[int, Field(ge=0, le=MAX_RANDOM_SEED)],
            replace: bool,
        ) -> dict[str, Any]:
            profile_id = _profile_exists(name, replace)
            text = sample_text.strip() or DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT
            sample_language = language.strip()
            if not sample_language or sample_language.casefold() == "auto":
                sample_language = DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE
            try:
                _format, sample_rate, waveform, used_seed, _profiles = await asyncio.to_thread(
                    runtime.synthesize_complete_payload,
                    TTSRequest(
                        text=text,
                        language=sample_language,
                        instruct=voice_instruction,
                        seed=seed,
                        output_format="wav",
                        pad_duration=0,
                        fade_duration=0,
                    ),
                )
                runtime.UI_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix="mcp-designed-", suffix=".wav", dir=runtime.UI_UPLOAD_DIR
                )
                os.close(descriptor)
                temporary_path = Path(temporary_name)
                try:
                    await asyncio.to_thread(
                        temporary_path.write_bytes, audio_to_wav_bytes(waveform, sample_rate)
                    )
                    saved = await asyncio.to_thread(
                        runtime.save_openai_voice_profile,
                        profile_id,
                        str(temporary_path),
                        text,
                        sample_language,
                        used_seed,
                        False,
                        description,
                        "designed",
                    )
                finally:
                    temporary_path.unlink(missing_ok=True)
                runtime.clear_voice_clone_prompt_cache()
            except Exception as exc:
                raise _tool_error(exc, "Correct the design instruction or profile metadata and retry.") from exc
            return {"status": "saved", "voice": _profile_public(saved)}

        @mcp.tool(
            title="Delete a saved voice",
            description=(
                "Permanently remove one saved cloned or designed voice and its copied reference "
                "audio. Call only when the user explicitly asks to delete that exact catalog id."
            ),
            annotations=mutation,
            structured_output=True,
        )
        async def delete_voice_profile(
            name: Annotated[str, Field(min_length=1, max_length=48)],
        ) -> dict[str, Any]:
            profile = _resolve_profile(name)
            del profile
            try:
                deleted = await asyncio.to_thread(
                    runtime._delete_openai_voice_profile,
                    runtime.OPENAI_VOICE_PROFILE_DIR,
                    runtime.OPENAI_VOICE_PROFILE_INDEX,
                    name,
                )
                runtime.clear_voice_clone_prompt_cache()
            except Exception as exc:
                raise _tool_error(exc, "Refresh the catalog and retry with an exact saved id.") from exc
            return {"status": "deleted", "deleted": deleted}

    return mcp


def attach_mcp(
    *,
    api_app: FastAPI,
    runtime: Any,
    artifact_store: ArtifactStore | None = None,
) -> FastAPI:
    """Mount independently gated compact and complete MCP endpoints."""
    global _RUNTIME
    _RUNTIME = runtime
    store = artifact_store or ArtifactStore()
    base_url = _download_base_url()
    compact_slot = MCPApplicationSlot()
    advanced_slot = MCPApplicationSlot()

    async def download_artifact(token: str) -> FileResponse:
        try:
            artifact, path = await asyncio.to_thread(store.resolve, token)
        except ArtifactExpiredError as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from exc
        except ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(
            path,
            media_type=artifact.mime_type,
            filename=artifact.filename,
            headers={"Cache-Control": "private, no-store"},
        )

    api_app.add_api_route(
        "/tts/artifacts/{token}",
        download_artifact,
        methods=["GET", "HEAD"],
        include_in_schema=False,
        name="mcp-generated-audio",
    )
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=_enabled(
            "OMNIVOICE_MCP_DNS_REBINDING_PROTECTION", True
        ),
        allowed_hosts=_allowed_hosts(base_url),
        allowed_origins=_csv_setting(
            "OMNIVOICE_MCP_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS
        ),
    )
    def create_apps() -> tuple[MCPServer[Any], MCPServer[Any], Any, Any]:
        compact = create_mcp_server(
            artifact_store=store, base_url=base_url, advanced=False
        )
        advanced = create_mcp_server(
            artifact_store=store, base_url=base_url, advanced=True
        )
        compact_app = compact.streamable_http_app(
            streamable_http_path="/",
            json_response=True,
            stateless_http=True,
            max_request_body_size=4 * 1024 * 1024,
            transport_security=security,
        )
        advanced_app = advanced.streamable_http_app(
            streamable_http_path="/",
            json_response=True,
            stateless_http=True,
            max_request_body_size=4 * 1024 * 1024,
            transport_security=security,
        )
        return compact, advanced, compact_app, advanced_app

    original_lifespan = api_app.router.lifespan_context

    async def cleanup_expired() -> None:
        while True:
            await asyncio.sleep(ARTIFACT_CLEANUP_INTERVAL_SECONDS)
            await asyncio.to_thread(store.cleanup_expired)

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        compact, advanced, compact_app, advanced_app = create_apps()
        compact_slot.app = compact_app
        advanced_slot.app = advanced_app
        api_app.state.mcp_compact_server = compact
        api_app.state.mcp_advanced_server = advanced
        await asyncio.to_thread(store.cleanup_expired)
        cleanup_task = asyncio.create_task(cleanup_expired())
        try:
            async with (
                original_lifespan(app),
                compact.session_manager.run(),
                advanced.session_manager.run(),
            ):
                yield
        finally:
            compact_slot.app = None
            advanced_slot.app = None
            cleanup_task.cancel()
            await asyncio.gather(cleanup_task, return_exceptions=True)

    api_app.router.lifespan_context = combined_lifespan
    api_app.mount(
        "/mcp/advanced",
        MCPAccessGate(
            advanced_slot,
            enabled=lambda: runtime.RUNTIME_SETTINGS.mcp_advanced_enabled(
                default=_enabled("OMNIVOICE_ENABLE_ADVANCED_MCP")
            ),
            label="Advanced",
        ),
        name="mcp-advanced",
    )
    api_app.mount(
        "/mcp",
        MCPAccessGate(
            compact_slot,
            enabled=lambda: runtime.RUNTIME_SETTINGS.mcp_enabled(
                default=_enabled("OMNIVOICE_ENABLE_MCP")
            ),
            label="Compact",
        ),
        name="mcp",
    )
    api_app.state.mcp_compact_server = None
    api_app.state.mcp_advanced_server = None
    api_app.state.mcp_artifact_store = store
    api_app.state.mcp_output_directory = store.directory
    api_app.state.mcp_base_url = base_url
    return api_app
