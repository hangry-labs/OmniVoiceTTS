from __future__ import annotations

import os
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


MAX_RANDOM_SEED = 2**32 - 1
DEFAULT_DEVICE = os.getenv("OMNIVOICE_DEVICE", "auto")


class TTSRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str | None = Field(
        None,
        description=(
            "Compatibility voice field. Saved voice profile names and OpenAI-style aliases such as nova/shimmer "
            "resolve to local OmniVoice clone/design behavior; unknown Kokoro speaker ids are ignored."
        ),
    )
    voice_profile: str | None = Field(
        None,
        description="Saved local voice profile name. This uses the same profiles exposed through /v1/audio/voices.",
    )
    language: str | None = Field(None, description="Language name or id. Omit for auto/language-agnostic mode.")
    ref_audio: str | None = Field(
        None,
        description=(
            "Reference audio path for voice cloning. The path must be an audio file under a configured safe root "
            "such as /data, /app/persistent/voices/openai, /app/omnivoice/runtime_assets/voices, or the browser "
            "UI upload directory."
        ),
    )
    ref_text: str | None = Field(None, description="Transcript for ref_audio. If omitted, ASR may load on demand.")
    instruct: str | None = Field(
        None,
        description=(
            "Voice design instruction, for example 'female, low pitch'. Do not combine with bracket expression "
            "tags in text; use ref_audio voice cloning or omit instruct for [laughter]/[sigh]-style tags."
        ),
    )
    speed: float | None = Field(1.0, ge=0.5, le=1.5, description="Speech speed multiplier.")
    duration: float | None = Field(None, gt=0.0, description="Fixed output duration in seconds. Overrides speed.")
    device: str = Field(DEFAULT_DEVICE, description="auto, cpu, mps, or cuda:N.")
    use_gpu: bool | None = Field(None, description="Kokoro-compatible legacy switch. Prefer device.")
    num_step: int = Field(32, ge=4, le=64, description="Diffusion decoding steps.")
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0, description="Classifier-free guidance scale.")
    denoise: bool = Field(True, description="Use denoising prompt when applicable.")
    preprocess_prompt: bool = Field(True, description="Trim/remove silence from reference prompt audio.")
    postprocess_output: bool = Field(True, description="Remove long silences and fade/pad generated audio.")
    pad_duration: float = Field(0.1, ge=0.0, le=5.0, description="Silence padding duration per side in seconds. Set to 0 to disable.")
    fade_duration: float = Field(0.1, ge=0.0, le=5.0, description="Fade-in/out curve duration in seconds. Set to 0 to disable.")
    t_shift: float = Field(0.1, gt=0.0, le=1.0, description="Time-step shift for the noise schedule.")
    layer_penalty_factor: float = Field(5.0, ge=0.0, le=20.0, description="Penalty encouraging lower codebook layers to unmask first.")
    position_temperature: float = Field(5.0, ge=0.0, le=20.0, description="Temperature for mask-position selection.")
    class_temperature: float = Field(0.0, ge=0.0, le=5.0, description="Temperature for token sampling.")
    seed: int | None = Field(None, ge=0, le=MAX_RANDOM_SEED, description="Optional random seed for reproducible generation.")
    randomize_seed: bool = Field(False, description="Generate and use a random seed for this request.")
    audio_chunk_duration: float = Field(15.0, ge=0.0, le=120.0, description="Target chunk duration for long text.")
    audio_chunk_threshold: float = Field(30.0, ge=0.0, le=300.0, description="Estimated duration threshold before long-text chunking activates.")
    pitch_semitones: float = Field(0.0, ge=-12.0, le=12.0, description="Post-synthesis pitch shift.")
    tempo: float = Field(1.0, ge=0.5, le=2.0, description="Post-synthesis tempo multiplier.")
    volume: float = Field(1.0, ge=0.0, le=2.0, description="Output volume multiplier.")
    normalize: bool = Field(False, description="Apply ffmpeg loudness normalization.")
    cache_voice_prompt: bool = Field(
        False,
        description="Internal optimization flag used for saved/built-in voice profiles.",
        exclude=True,
    )
    output_format: str = Field(
        "wav",
        alias="format",
        validation_alias=AliasChoices("format", "output_format", "response_format"),
        description="wav, mp3, flac, or ogg.",
    )


class PurgeRequest(BaseModel):
    device: str | None = Field(None, description="Optional cached model device to clear. Omit to clear all.")


class CacheClearRequest(BaseModel):
    reset_peak_stats: bool = Field(
        False,
        description="Reset CUDA peak memory counters after clearing unused cached blocks.",
    )


class UIGenerationDefaults(BaseModel):
    voice_mode: Literal["random", "design", "clone", "profile"] = "random"
    language: str = ""
    voice_profile: str = ""
    device: str = DEFAULT_DEVICE
    output_format: Literal["wav", "mp3", "flac", "ogg"] = "mp3"
    speed: float = Field(1.0, ge=0.5, le=1.5)
    pitch_semitones: float = Field(0.0, ge=-12.0, le=12.0)
    tempo: float = Field(1.0, ge=0.5, le=2.0)
    volume: float = Field(1.0, ge=0.0, le=2.0)
    normalize: bool = False
    num_step: int = Field(32, ge=4, le=64)
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0)
    pad_duration: float = Field(0.1, ge=0.0, le=5.0)
    fade_duration: float = Field(0.1, ge=0.0, le=5.0)
    seed: int = Field(42, ge=0, le=MAX_RANDOM_SEED)
    randomize_seed: bool = True
    denoise: bool = True
    preprocess_prompt: bool = True
    postprocess_output: bool = True
    audio_chunk_duration: float = Field(15.0, ge=0.0, le=120.0)
    audio_chunk_threshold: float = Field(30.0, ge=0.0, le=300.0)


class VoiceProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=48)
    upload_token: str = Field(..., min_length=1, max_length=64)
    ref_text: str = ""
    language: str = ""
    seed: int | None = Field(12345, ge=0, le=MAX_RANDOM_SEED)
    randomize_seed: bool = False


class OpenAISpeechRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str = Field(
        "omnivoice",
        description=(
            "OpenAI-style model id. Accepted request aliases include omnivoice, omnivoicetts, "
            "tts-1, tts-1-hd, and gpt-4o-mini-tts; aliases map to the local OmniVoice model."
        ),
    )
    input: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str = Field("default", description="OpenAI-style voice id. Compatibility aliases map to local OmniVoice clone/design behavior.")
    response_format: str = Field("mp3", description="mp3, wav, flac, or ogg. opus is accepted as an ogg alias.")
    speed: float = Field(1.0, ge=0.5, le=1.5, description="Speech speed multiplier.")
    language: str | None = Field(None, description="Optional OmniVoice extension: language name or id.")
    seed: int | None = Field(None, ge=0, le=MAX_RANDOM_SEED, description="Optional OmniVoice extension: fixed generation seed.")
    randomize_seed: bool = Field(False, description="Optional OmniVoice extension: generate a random seed.")
    device: str = Field(DEFAULT_DEVICE, description="Optional OmniVoice extension: auto, cpu, mps, or cuda:N.")
    num_step: int = Field(32, ge=4, le=64, description="Optional OmniVoice extension: diffusion decoding steps.")
    pad_duration: float = Field(0.1, ge=0.0, le=5.0, description="Optional OmniVoice extension: silence padding duration per side in seconds.")
    fade_duration: float = Field(0.1, ge=0.0, le=5.0, description="Optional OmniVoice extension: fade-in/out curve duration in seconds.")
    instructions: str | None = Field(None, description="Optional OmniVoice extension: explicit voice-design instruction.")
    ref_audio: str | None = Field(
        None,
        description=(
            "Optional OmniVoice extension: reference audio path for stable voice cloning. The path must be an "
            "audio file under a configured safe root."
        ),
    )
    ref_text: str | None = Field(None, description="Optional OmniVoice extension: transcript for ref_audio.")
    voice_profile: str | None = Field(None, description="Optional OmniVoice extension: saved OpenAI voice profile name.")
