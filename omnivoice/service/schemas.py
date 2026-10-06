from __future__ import annotations

import os
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from omnivoice.utils.text import validate_synthesis_text
from omnivoice.utils.text_normalization import MAX_NORMALIZATION_CHARACTERS


MAX_RANDOM_SEED = 2**32 - 1
DEFAULT_DEVICE = os.getenv("OMNIVOICE_DEVICE", "auto")


class TTSRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., min_length=1, description="Plain text, SSML, or SSML-H document to synthesize.")
    input_type: Literal["text", "ssml", "ssml-h"] = Field(
        "text",
        description=(
            "Input interpretation. Plain text remains the default; SSML and SSML-H must be selected explicitly."
        ),
    )
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
    duration: float | None = Field(
        None,
        gt=0.0,
        description=(
            "Audio-token budget expressed in seconds. Overrides speed; final "
            "waveform length may vary."
        ),
    )
    device: str = Field(DEFAULT_DEVICE, description="auto, cpu, mps, or cuda:N.")
    use_gpu: bool | None = Field(None, description="Kokoro-compatible legacy switch. Prefer device.")
    num_step: int = Field(32, ge=4, le=64, description="Diffusion decoding steps.")
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0, description="Classifier-free guidance scale.")
    denoise: bool = Field(True, description="Use denoising prompt when applicable.")
    preprocess_prompt: bool = Field(True, description="Trim/remove silence from reference prompt audio.")
    postprocess_output: bool = Field(True, description="Remove long silences and fade/pad generated audio.")
    pad_duration: float = Field(0.1, ge=0.0, le=5.0, description="Silence padding duration per side in seconds. Set to 0 to disable.")
    fade_duration: float = Field(0.1, ge=0.0, le=5.0, description="Fade-in/out curve duration in seconds. Set to 0 to disable.")
    float_preserving_silence: bool = Field(
        True,
        description=(
            "Preserve original float samples while detecting/removing silence. "
            "Disable for legacy PCM16 behavior."
        ),
    )
    output_min_silence_ms: int = Field(
        500,
        ge=0,
        le=10_000,
        description="Minimum internal silence duration to shorten, in milliseconds.",
    )
    output_keep_silence_ms: int = Field(
        1000,
        ge=0,
        le=10_000,
        description=(
            "Maximum total silence retained around each shortened internal gap, "
            "in milliseconds."
        ),
    )
    output_lead_silence_ms: int = Field(
        100,
        ge=0,
        le=10_000,
        description="Leading silence retained during output cleanup, in milliseconds.",
    )
    output_trail_silence_ms: int = Field(
        100,
        ge=0,
        le=10_000,
        description="Trailing silence retained during output cleanup, in milliseconds.",
    )
    output_preserve_active_edges: bool = Field(
        False,
        description=(
            "Preserve nonzero outer-edge samples below the silence detector threshold."
        ),
    )
    output_peak_limit: float | None = Field(
        None,
        gt=0.0,
        le=1.0,
        description="Optional absolute peak ceiling. Omit to disable limiting.",
    )
    t_shift: float = Field(0.1, gt=0.0, le=1.0, description="Time-step shift for the noise schedule.")
    layer_penalty_factor: float = Field(5.0, ge=0.0, le=20.0, description="Penalty encouraging lower codebook layers to unmask first.")
    position_temperature: float = Field(5.0, ge=0.0, le=20.0, description="Temperature for mask-position selection.")
    class_temperature: float = Field(0.0, ge=0.0, le=5.0, description="Temperature for token sampling.")
    seed: int | None = Field(None, ge=0, le=MAX_RANDOM_SEED, description="Optional random seed for reproducible generation.")
    randomize_seed: bool = Field(False, description="Generate and use a random seed for this request.")
    normalize_text: bool = Field(
        False,
        description=(
            "Convert supported English, Malayalam, or Vietnamese structured text to a "
            "spoken form before synthesis. "
            "Plain-text input only; use /tts/text/normalize to preview the exact result."
        ),
    )
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

    @model_validator(mode="after")
    def validate_text_content(self) -> "TTSRequest":
        if self.input_type == "text":
            validate_synthesis_text(self.text)
        elif not self.text.strip():
            raise ValueError("SSML input must not be empty.")
        if self.normalize_text and self.input_type != "text":
            raise ValueError("normalize_text is available only when input_type='text'.")
        return self


class PurgeRequest(BaseModel):
    device: str | None = Field(None, description="Optional cached model device to clear. Omit to clear all.")


class CacheClearRequest(BaseModel):
    reset_peak_stats: bool = Field(
        False,
        description="Reset CUDA peak memory counters after clearing unused cached blocks.",
    )


class TextNormalizationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_NORMALIZATION_CHARACTERS)
    language: str | None = Field(
        None,
        description=(
            "Language name or id. Structured normalization supports English, Malayalam, "
            "and Vietnamese."
        ),
    )

    @field_validator("text")
    @classmethod
    def validate_text_content(cls, value: str) -> str:
        return validate_synthesis_text(value)


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
    normalize_text: bool = False
    num_step: int = Field(32, ge=4, le=64)
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0)
    pad_duration: float = Field(0.1, ge=0.0, le=5.0)
    fade_duration: float = Field(0.1, ge=0.0, le=5.0)
    float_preserving_silence: bool = True
    output_min_silence_ms: int = Field(500, ge=0, le=10_000)
    output_keep_silence_ms: int = Field(1000, ge=0, le=10_000)
    output_lead_silence_ms: int = Field(100, ge=0, le=10_000)
    output_trail_silence_ms: int = Field(100, ge=0, le=10_000)
    output_preserve_active_edges: bool = False
    output_peak_limit: float | None = Field(None, gt=0.0, le=1.0)
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
    normalize_text: bool = Field(
        False,
        description=(
            "Optional OmniVoice extension: normalize supported English, Malayalam, or Vietnamese "
            "structured text before synthesis."
        ),
    )
    device: str = Field(DEFAULT_DEVICE, description="Optional OmniVoice extension: auto, cpu, mps, or cuda:N.")
    num_step: int = Field(32, ge=4, le=64, description="Optional OmniVoice extension: diffusion decoding steps.")
    pad_duration: float = Field(0.1, ge=0.0, le=5.0, description="Optional OmniVoice extension: silence padding duration per side in seconds.")
    fade_duration: float = Field(0.1, ge=0.0, le=5.0, description="Optional OmniVoice extension: fade-in/out curve duration in seconds.")
    float_preserving_silence: bool = Field(
        True,
        description=(
            "Optional OmniVoice extension: preserve float samples during silence cleanup."
        ),
    )
    output_min_silence_ms: int = Field(
        500,
        ge=0,
        le=10_000,
        description="Optional OmniVoice extension: silence trigger in milliseconds.",
    )
    output_keep_silence_ms: int = Field(
        1000,
        ge=0,
        le=10_000,
        description="Optional OmniVoice extension: retained internal gap in milliseconds.",
    )
    output_lead_silence_ms: int = Field(
        100,
        ge=0,
        le=10_000,
        description="Optional OmniVoice extension: retained leading silence in milliseconds.",
    )
    output_trail_silence_ms: int = Field(
        100,
        ge=0,
        le=10_000,
        description="Optional OmniVoice extension: retained trailing silence in milliseconds.",
    )
    output_preserve_active_edges: bool = Field(
        False,
        description="Optional OmniVoice extension: preserve quiet active outer edges.",
    )
    output_peak_limit: float | None = Field(
        None,
        gt=0.0,
        le=1.0,
        description="Optional OmniVoice extension: absolute peak ceiling.",
    )
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

    @field_validator("input")
    @classmethod
    def validate_input_content(cls, value: str) -> str:
        return validate_synthesis_text(value, field_name="Input")
