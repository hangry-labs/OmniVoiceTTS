"""Conservative, inspectable structured-text normalization for TTS."""

from __future__ import annotations

import calendar
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Callable
from urllib.parse import urlsplit

from num2words import num2words

from omnivoice.utils.lang_map import LANG_NAME_TO_ID
from omnivoice.utils.malayalam_normalization import collect_malayalam_candidates
from omnivoice.utils.vietnamese_normalization import collect_vietnamese_candidates


MAX_NORMALIZATION_CHARACTERS = 20_000
SUPPORTED_NORMALIZATION_LANGUAGES = ("en", "ml", "vi")

_BRACKET_CONTROL_RE = re.compile(r"\[[^\[\]]*\]")
_AMBIGUOUS_SLASH_DATE_RE = re.compile(r"(?<!\w)\d{1,2}/\d{1,2}/\d{2,4}(?!\w)")
_VERSION_OR_IPV4_RE = re.compile(r"(?<!\w)v?\d+(?:\.\d+){2,}(?!\w)", re.IGNORECASE)
_EMAIL_RE = re.compile(
    r"(?<![\w.@])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?![\w@])"
)
_URL_RE = re.compile(r"(?<!\w)(?:https?://|www\.)[^\s<>{}\[\]]+", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"(?<!\w)(\d{4})-(\d{2})-(\d{2})(?!\w)")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[ .-])?(?:\(?\d{2,4}\)?[ .-]){2,}\d{3,4}(?![\w.])"
)
_CURRENCY_RE = re.compile(r"(?<![\w.])([$€£])\s*([-+]?\d[\d,]*(?:\.\d+)?)(?![\w.])")
_PERCENT_RE = re.compile(r"(?<![\w.])([-+]?\d[\d,]*(?:\.\d+)?)\s*%(?!\w)")
_DECIMAL_RE = re.compile(r"(?<![\w.])([-+]?\d[\d,]*\.\d+)(?![\w.])")
_ALPHANUMERIC_RE = re.compile(r"(?<!\w)[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*(?!\w)")
_INTEGER_RE = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?!\w)(?!\.\d)")

_DIGIT_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
)
_CURRENCY_NAMES = {
    "$": ("dollar", "dollars", "cent", "cents"),
    "€": ("euro", "euros", "cent", "cents"),
    "£": ("pound", "pounds", "penny", "pence"),
}
_SYMBOL_WORDS = {
    ".": "dot",
    "-": "dash",
    "_": "underscore",
    "/": "slash",
    ":": "colon",
    "?": "question mark",
    "&": "and",
    "=": "equals",
    "#": "hash",
    "+": "plus",
    "%": "percent",
    "~": "tilde",
}


@dataclass(frozen=True)
class TextNormalizationChange:
    kind: str
    original: str
    spoken: str
    start: int
    end: int

    def model_dump(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class TextNormalizationResult:
    original: str
    normalized: str
    language: str | None
    supported: bool
    changes: tuple[TextNormalizationChange, ...]
    warnings: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.original != self.normalized

    def model_dump(self) -> dict[str, object]:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "language": self.language,
            "supported": self.supported,
            "changed": self.changed,
            "changes": [change.model_dump() for change in self.changes],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class _Candidate:
    kind: str
    start: int
    end: int
    spoken: str


def _english_words(value: int, *, ordinal: bool = False, year: bool = False) -> str:
    target = "ordinal" if ordinal else "year" if year else "cardinal"
    return str(num2words(value, lang="en", to=target)).replace("-", " ")


def _digit_words(value: str) -> str:
    return " ".join(_DIGIT_WORDS[int(character)] for character in value if character.isdigit())


def _number_parts(value: str) -> tuple[str, str | None, bool]:
    cleaned = value.replace(",", "").strip()
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("+-")
    whole, separator, fraction = cleaned.partition(".")
    return whole or "0", fraction if separator else None, negative


def _verbalize_number(value: str) -> str:
    whole, fraction, negative = _number_parts(value)
    words = _english_words(int(whole))
    if fraction is not None:
        words = f"{words} point {_digit_words(fraction)}"
    if negative:
        words = f"minus {words}"
    elif value.strip().startswith("+"):
        words = f"plus {words}"
    return words


def _verbalize_currency(match: re.Match[str]) -> str:
    symbol, value = match.groups()
    whole, fraction, negative = _number_parts(value)
    major = int(whole)
    major_one, major_many, minor_one, minor_many = _CURRENCY_NAMES[symbol]
    major_name = major_one if major == 1 else major_many
    words = f"{_english_words(major)} {major_name}"
    if fraction:
        minor = int((fraction + "00")[:2])
        if minor:
            minor_name = minor_one if minor == 1 else minor_many
            words = f"{words} and {_english_words(minor)} {minor_name}"
    if negative:
        words = f"minus {words}"
    return words


def _verbalize_iso_date(match: re.Match[str]) -> str:
    year, month, day = (int(part) for part in match.groups())
    parsed = date(year, month, day)
    return f"{calendar.month_name[parsed.month]} {_english_words(parsed.day, ordinal=True)} {_english_words(parsed.year, year=True)}"


def _verbalize_symbolic(value: str, *, spell_letters: bool = False) -> str:
    words: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character.isalpha():
            end = index + 1
            while end < len(value) and value[end].isalpha():
                end += 1
            token = value[index:end]
            if spell_letters:
                words.extend(token.upper())
            else:
                words.append(token)
            index = end
            continue
        if character.isdigit():
            end = index + 1
            while end < len(value) and value[end].isdigit():
                end += 1
            words.append(_digit_words(value[index:end]))
            index = end
            continue
        spoken = _SYMBOL_WORDS.get(character)
        if spoken:
            words.append(spoken)
        index += 1
    return " ".join(words)


def _verbalize_email(match: re.Match[str]) -> str:
    local, domain = match.group().rsplit("@", 1)
    return f"{_verbalize_symbolic(local)} at {_verbalize_symbolic(domain)}"


def _verbalize_url(match: re.Match[str]) -> tuple[int, str]:
    raw = match.group()
    trailing = len(raw) - len(raw.rstrip(".,!?;:"))
    value = raw[:-trailing] if trailing else raw
    parsed_value = value if "://" in value else f"https://{value}"
    parsed = urlsplit(parsed_value)
    prefix = ""
    if "://" in value:
        prefix = f"{' '.join(parsed.scheme.upper())} colon slash slash "
    host = _verbalize_symbolic(parsed.netloc)
    suffix = _verbalize_symbolic(
        f"{parsed.path}{'?' if parsed.query else ''}{parsed.query}{'#' if parsed.fragment else ''}{parsed.fragment}"
    )
    return len(value), " ".join(part for part in (prefix.strip(), host, suffix) if part)


def _resolve_language(language: str | None, text: str) -> str | None:
    if language and language.strip().lower() not in {"auto", "none"}:
        value = language.strip().lower().replace("_", "-")
        code = LANG_NAME_TO_ID.get(value, value).split("-", 1)[0]
        return code
    if any("\u0d00" <= character <= "\u0d7f" for character in text):
        return "ml"
    has_non_ascii_letters = any(character.isalpha() and not character.isascii() for character in text)
    if re.search(r"[A-Za-z]", text) and not has_non_ascii_letters:
        return "en"
    return None


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < other_end and end > other_start for other_start, other_end in spans)


def normalize_structured_text(text: str, language: str | None = None) -> TextNormalizationResult:
    """Return a conservative spoken form and every applied replacement."""
    if len(text) > MAX_NORMALIZATION_CHARACTERS:
        raise ValueError(
            f"Text normalization accepts at most {MAX_NORMALIZATION_CHARACTERS} characters."
        )

    resolved_language = _resolve_language(language, text)
    if resolved_language not in SUPPORTED_NORMALIZATION_LANGUAGES:
        return TextNormalizationResult(
            original=text,
            normalized=text,
            language=resolved_language,
            supported=False,
            changes=(),
            warnings=(
                "Structured-text normalization currently supports English, Malayalam, and Vietnamese plain text.",
            ),
        )

    protected = [match.span() for match in _BRACKET_CONTROL_RE.finditer(text)]
    warnings: list[str] = []
    for pattern, warning in (
        (_AMBIGUOUS_SLASH_DATE_RE, "Ambiguous slash-form dates were preserved; use YYYY-MM-DD for deterministic speech."),
        (_VERSION_OR_IPV4_RE, "Version-like or IPv4-style dotted values were preserved."),
    ):
        matches = list(pattern.finditer(text))
        if matches:
            warnings.append(warning)
            protected.extend(match.span() for match in matches)

    candidates: list[_Candidate] = []
    occupied = list(protected)

    def collect(
        pattern: re.Pattern[str],
        kind: str,
        verbalize: Callable[[re.Match[str]], str],
        accept: Callable[[re.Match[str]], bool] | None = None,
    ) -> None:
        # Input is capped at MAX_NORMALIZATION_CHARACTERS above. These conservative
        # recognizers are retained to preserve normalization behavior.
        # codeql[py/polynomial-redos]
        for match in pattern.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            if accept is not None and not accept(match):
                continue
            try:
                spoken = verbalize(match)
            except (ValueError, OverflowError):
                continue
            if not spoken or spoken == match.group():
                continue
            candidates.append(_Candidate(kind, match.start(), match.end(), spoken))
            occupied.append(match.span())

    if resolved_language == "ml":
        malayalam = collect_malayalam_candidates(text, occupied)
        candidates.extend(
            _Candidate(item.kind, item.start, item.end, item.spoken)
            for item in malayalam.candidates
        )
        warnings.extend(malayalam.warnings)
    elif resolved_language == "vi":
        vietnamese = collect_vietnamese_candidates(text, occupied)
        candidates.extend(
            _Candidate(item.kind, item.start, item.end, item.spoken)
            for item in vietnamese.candidates
        )
        warnings.extend(vietnamese.warnings)
    else:
        collect(_EMAIL_RE, "email", _verbalize_email)

        for match in _URL_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            length, spoken = _verbalize_url(match)
            if length and spoken:
                candidates.append(_Candidate("url", match.start(), match.start() + length, spoken))
                occupied.append((match.start(), match.start() + length))

        collect(_ISO_DATE_RE, "date", _verbalize_iso_date)
        collect(
            _PHONE_RE,
            "phone",
            lambda match: ("plus " if match.group().lstrip().startswith("+") else "")
            + _digit_words(match.group()),
            lambda match: sum(character.isdigit() for character in match.group()) >= 7,
        )
        collect(_CURRENCY_RE, "currency", _verbalize_currency)
        collect(_PERCENT_RE, "percentage", lambda match: f"{_verbalize_number(match.group(1))} percent")
        collect(_DECIMAL_RE, "decimal", lambda match: _verbalize_number(match.group(1)))
        collect(
            _ALPHANUMERIC_RE,
            "identifier",
            lambda match: _verbalize_symbolic(match.group(), spell_letters=True),
            lambda match: (
                any(character.isdigit() for character in match.group())
                and any(character.isalpha() for character in match.group())
                and (
                    re.search(r"[-_]", match.group()) is not None
                    or match.group().upper() == match.group()
                )
            ),
        )
        collect(_INTEGER_RE, "integer", lambda match: _verbalize_number(match.group()))

    normalized = text
    changes: list[TextNormalizationChange] = []
    for candidate in sorted(candidates, key=lambda item: item.start, reverse=True):
        original = text[candidate.start : candidate.end]
        normalized = normalized[: candidate.start] + candidate.spoken + normalized[candidate.end :]
        changes.append(
            TextNormalizationChange(
                kind=candidate.kind,
                original=original,
                spoken=candidate.spoken,
                start=candidate.start,
                end=candidate.end,
            )
        )

    return TextNormalizationResult(
        original=text,
        normalized=normalized,
        language=resolved_language,
        supported=True,
        changes=tuple(sorted(changes, key=lambda item: item.start)),
        warnings=tuple(warnings),
    )


__all__ = [
    "MAX_NORMALIZATION_CHARACTERS",
    "SUPPORTED_NORMALIZATION_LANGUAGES",
    "TextNormalizationChange",
    "TextNormalizationResult",
    "normalize_structured_text",
]
