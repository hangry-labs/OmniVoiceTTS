from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from ssml_h import (
    MAX_BREAK_MS,
    MAX_PHONEME_CHARACTERS,
    MAX_SSML_ELEMENTS,
    MAX_SSML_NESTING,
    MAX_SSML_SOURCE_CHARACTERS,
    MAX_SSML_UNITS,
    MAX_SSML_VOICE_DEFINITIONS,
    MAX_TOTAL_BREAK_MS,
    MAX_VOICE_DESCRIPTION_CHARACTERS,
    MAX_VOICE_SAMPLE_CHARACTERS,
    SSML_H_NAMESPACE,
    SSML_NAMESPACE,
    SSMLPlan,
    SSMLProsody,
    SSMLUnit,
    SSMLValidationError,
    SSMLVoiceDefinition,
    compile_ssml as compile_ssml_document,
    ssml_capabilities as base_ssml_capabilities,
)


ARPABET_PATTERN = re.compile(r"^[A-Z]{1,4}[0-2]?(?:\s+[A-Z]{1,4}[0-2]?)*$")
LanguageResolver = Callable[[str], str]
VoiceValidator = Callable[[str, frozenset[str]], None]
DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE = "en-US"
DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT = (
    "Hello, this is my natural speaking voice, kept clear, steady, and consistent "
    "for every conversation we share."
)


def _render_omnivoice_phoneme(
    alphabet: str,
    phonemes: str,
    source_text: str,
    language: str | None,
) -> str:
    del source_text
    if alphabet not in {"arpabet", "x-arpabet"}:
        raise ValueError(
            "OmniVoiceTTS <phoneme> supports alphabet='x-arpabet' for English ARPABET only; "
            "generic IPA is not supported."
        )
    if (language or "").split("-", 1)[0].lower() != "en":
        raise ValueError("OmniVoiceTTS ARPABET phonemes require an English language context.")
    normalized = " ".join(phonemes.upper().split())
    if not normalized or not ARPABET_PATTERN.fullmatch(normalized):
        raise ValueError(
            "ARPABET ph must contain valid space-separated symbols and at most "
            f"{MAX_PHONEME_CHARACTERS} characters."
        )
    return f"[{normalized}]"


def compile_ssml(
    document: str,
    input_type: Literal["ssml", "ssml-h"],
    *,
    default_language: str | None = None,
    default_voice: str | None = None,
    resolve_language: LanguageResolver | None = None,
    validate_voice: VoiceValidator | None = None,
) -> SSMLPlan:
    """Compile SSML using the shared parser and OmniVoice processor capabilities."""

    return compile_ssml_document(
        document,
        input_type,
        default_language=default_language,
        default_voice=default_voice,
        resolve_language=resolve_language,
        validate_voice=validate_voice,
        render_phoneme=_render_omnivoice_phoneme,
    )


def ssml_capabilities() -> dict:
    """Describe the shared profile with OmniVoice-specific feature support."""

    capabilities = base_ssml_capabilities(
        phoneme_alphabets=("x-arpabet (English)",),
        description_supported=False,
    )
    capabilities["ssml_h"]["default_voice_sample"] = {
        "language": DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE,
        "text": DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT,
        "used_when": "h:sample is omitted",
    }
    return capabilities


__all__ = [
    "MAX_BREAK_MS",
    "MAX_PHONEME_CHARACTERS",
    "MAX_SSML_ELEMENTS",
    "MAX_SSML_NESTING",
    "MAX_SSML_SOURCE_CHARACTERS",
    "MAX_SSML_UNITS",
    "MAX_SSML_VOICE_DEFINITIONS",
    "MAX_TOTAL_BREAK_MS",
    "MAX_VOICE_DESCRIPTION_CHARACTERS",
    "MAX_VOICE_SAMPLE_CHARACTERS",
    "DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE",
    "DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT",
    "SSML_H_NAMESPACE",
    "SSML_NAMESPACE",
    "SSMLPlan",
    "SSMLProsody",
    "SSMLUnit",
    "SSMLValidationError",
    "SSMLVoiceDefinition",
    "compile_ssml",
    "ssml_capabilities",
]
