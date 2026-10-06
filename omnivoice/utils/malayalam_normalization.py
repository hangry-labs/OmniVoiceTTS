"""Conservative Malayalam structured-text verbalization rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class MalayalamNormalizationCandidate:
    kind: str
    start: int
    end: int
    spoken: str


@dataclass(frozen=True)
class MalayalamNormalizationCandidates:
    candidates: tuple[MalayalamNormalizationCandidate, ...]
    warnings: tuple[str, ...]


_ONES = {
    0: "പൂജ്യം",
    1: "ഒന്ന്",
    2: "രണ്ട്",
    3: "മൂന്ന്",
    4: "നാല്",
    5: "അഞ്ച്",
    6: "ആറ്",
    7: "ഏഴ്",
    8: "എട്ട്",
    9: "ഒമ്പത്",
}
_TEENS = {
    10: "പത്ത്",
    11: "പതിനൊന്ന്",
    12: "പന്ത്രണ്ട്",
    13: "പതിമൂന്ന്",
    14: "പതിനാല്",
    15: "പതിനഞ്ച്",
    16: "പതിനാറ്",
    17: "പതിനേഴ്",
    18: "പതിനെട്ട്",
    19: "പത്തൊമ്പത്",
}
_TENS = {
    20: "ഇരുപത്",
    30: "മുപ്പത്",
    40: "നാല്പത്",
    50: "അമ്പത്",
    60: "അറുപത്",
    70: "എഴുപത്",
    80: "എൺപത്",
    90: "തൊണ്ണൂറ്",
}
_TENS_CONNECTIVE = {
    20: "ഇരുപത്തി",
    30: "മുപ്പത്തി",
    40: "നാല്പത്തി",
    50: "അമ്പത്തി",
    60: "അറുപത്തി",
    70: "എഴുപത്തി",
    80: "എൺപത്തി",
    90: "തൊണ്ണൂറ്റി",
}
_HUNDREDS = {
    1: "നൂറ്",
    2: "ഇരുനൂറ്",
    3: "മുന്നൂറ്",
    4: "നാനൂറ്",
    5: "അഞ്ഞൂറ്",
    6: "അറുനൂറ്",
    7: "എഴുനൂറ്",
    8: "എണ്ണൂറ്",
    9: "തൊള്ളായിരം",
}
_HUNDREDS_CONNECTIVE = {
    1: "നൂറ്റി",
    2: "ഇരുനൂറ്റി",
    3: "മുന്നൂറ്റി",
    4: "നാനൂറ്റി",
    5: "അഞ്ഞൂറ്റി",
    6: "അറുനൂറ്റി",
    7: "എഴുനൂറ്റി",
    8: "എണ്ണൂറ്റി",
    9: "തൊള്ളായിരത്തി",
}
_THOUSANDS = {
    1: "ആയിരം",
    2: "രണ്ടായിരം",
    3: "മൂവ്വായിരം",
    4: "നാലായിരം",
    5: "അയ്യായിരം",
    6: "ആറായിരം",
    7: "ഏഴായിരം",
    8: "എട്ടായിരം",
    9: "ഒമ്പതിനായിരം",
}
_THOUSANDS_CONNECTIVE = {
    1: "ആയിരത്തി",
    2: "രണ്ടായിരത്തി",
    3: "മൂവ്വായിരത്തി",
    4: "നാലായിരത്തി",
    5: "അയ്യായിരത്തി",
    6: "ആറായിരത്തി",
    7: "ഏഴായിരത്തി",
    8: "എട്ടായിരത്തി",
    9: "ഒമ്പതിനായിരത്തി",
}
_LAKHS = {
    1: "ഒരു ലക്ഷം",
    2: "രണ്ട് ലക്ഷം",
    3: "മൂന്ന് ലക്ഷം",
    4: "നാല് ലക്ഷം",
    5: "അഞ്ച് ലക്ഷം",
    6: "ആറ് ലക്ഷം",
    7: "ഏഴ് ലക്ഷം",
    8: "എട്ട് ലക്ഷം",
    9: "ഒമ്പത് ലക്ഷം",
}
_LAKHS_CONNECTIVE = {
    1: "ഒരു ലക്ഷത്തി",
    2: "രണ്ട് ലക്ഷത്തി",
    3: "മൂന്ന് ലക്ഷത്തി",
    4: "നാല് ലക്ഷത്തി",
    5: "അഞ്ച് ലക്ഷത്തി",
    6: "ആറ് ലക്ഷത്തി",
    7: "ഏഴ് ലക്ഷത്തി",
    8: "എട്ട് ലക്ഷത്തി",
    9: "ഒമ്പത് ലക്ഷത്തി",
}
_UNITS = {
    "km": "കിലോമീറ്റർ",
    "kg": "കിലോഗ്രാം",
    "mg": "മില്ലിഗ്രാം",
    "cm": "സെന്റീമീറ്റർ",
    "mm": "മില്ലിമീറ്റർ",
    "ml": "മില്ലിലിറ്റർ",
    "m": "മീറ്റർ",
    "g": "ഗ്രാം",
    "l": "ലിറ്റർ",
}
_FRACTIONS = {
    "1/4": "കാൽ",
    "1/2": "അര",
    "3/4": "മുക്കാൽ",
}
_LETTERS = {
    "A": "എ",
    "B": "ബി",
    "C": "സി",
    "D": "ഡി",
    "E": "ഇ",
    "F": "എഫ്",
    "G": "ജി",
    "H": "എച്ച്",
    "I": "ഐ",
    "J": "ജെ",
    "K": "കെ",
    "L": "എൽ",
    "M": "എം",
    "N": "എൻ",
    "O": "ഒ",
    "P": "പി",
    "Q": "ക്യൂ",
    "R": "ആർ",
    "S": "എസ്",
    "T": "ടി",
    "U": "യു",
    "V": "വി",
    "W": "ഡബ്ല്യൂ",
    "X": "എക്സ്",
    "Y": "വൈ",
    "Z": "സെഡ്",
}
_CURRENCIES = {
    "₹": "രൂപ",
    "Rs": "രൂപ",
    "Rs.": "രൂപ",
    "$": "ഡോളർ",
    "£": "പൗണ്ട്",
    "€": "യൂറോ",
    "¥": "യെൻ",
}

_INTEGER_TOKEN = r"[0-9](?:[0-9,]*[0-9])?"
_NUMBER_TOKEN = rf"{_INTEGER_TOKEN}(?:\.[0-9]+)?"
_CURRENCY_TOKEN = r"Rs\.|Rs|₹|\$|£|€|¥"
_UNIT_TOKEN = "|".join(sorted(_UNITS, key=len, reverse=True))

_CURRENCY_PREFIX_RE = re.compile(
    rf"(?<![\w.])(?P<currency>{_CURRENCY_TOKEN})\s*(?P<value>{_NUMBER_TOKEN})(?!\w)(?![.,][0-9])"
)
_CURRENCY_SUFFIX_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*(?P<currency>{_CURRENCY_TOKEN})(?!\w)"
)
_PERCENT_RE = re.compile(rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*%(?!\w)")
_UNIT_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*(?P<unit>{_UNIT_TOKEN})(?![A-Za-z])",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"(?<![\w:])(?P<hour>[01]?[0-9]|2[0-3]):(?P<minute>[0-5][0-9])(?![\w:])")
_TIME_LIKE_RE = re.compile(r"(?<![\w:])[0-9]{1,2}:[0-9]{2}(?![\w:])")
_MIXED_FRACTION_RE = re.compile(
    rf"(?<![\w.])(?P<whole>{_INTEGER_TOKEN})\s+(?P<fraction>1/4|1/2|3/4)(?![\w/])"
)
_FRACTION_RE = re.compile(r"(?<![\w/])(?P<fraction>1/4|1/2|3/4)(?![\w/])")
_FRACTION_LIKE_RE = re.compile(r"(?<![\w/])[0-9]+/[0-9]+(?![\w/])")
_ORDINAL_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_INTEGER_TOKEN})(?:st|nd|rd|th)(?!\w)",
    re.IGNORECASE,
)
_DECIMAL_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_INTEGER_TOKEN}\.[0-9]+)(?!\w)(?!\.[0-9])"
)
_INTEGER_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_INTEGER_TOKEN})(?!\w)(?![.,][0-9])"
)
_ACRONYM_RE = re.compile(r"(?<![A-Za-z])[A-Z]{2,}(?![A-Za-z])")
_ISO_DATE_RE = re.compile(r"(?<!\w)[0-9]{4}-[0-9]{2}-[0-9]{2}(?!\w)")


def number_to_malayalam(value: int) -> str | None:
    """Convert a non-negative integer up to 99,99,999 to Malayalam words."""
    if value < 0 or value > 9_999_999:
        return None
    if value == 0:
        return _ONES[0]

    parts: list[str] = []
    if value >= 100_000:
        lakhs, remainder = divmod(value, 100_000)
        if lakhs <= 9:
            parts.append((_LAKHS if remainder == 0 else _LAKHS_CONNECTIVE)[lakhs])
        else:
            words = number_to_malayalam(lakhs)
            if words is None:
                return None
            parts.append(f"{words} {'ലക്ഷം' if remainder == 0 else 'ലക്ഷത്തി'}")
        value = remainder

    if value >= 1_000:
        thousands, remainder = divmod(value, 1_000)
        if thousands <= 9:
            parts.append(
                (_THOUSANDS if remainder == 0 else _THOUSANDS_CONNECTIVE)[thousands]
            )
        else:
            words = number_to_malayalam(thousands)
            if words is None:
                return None
            parts.append(f"{words} {'ആയിരം' if remainder == 0 else 'ആയിരത്തി'}")
        value = remainder

    if value >= 100:
        hundreds, remainder = divmod(value, 100)
        parts.append((_HUNDREDS if remainder == 0 else _HUNDREDS_CONNECTIVE)[hundreds])
        value = remainder

    if value:
        if value < 10:
            parts.append(_ONES[value])
        elif value < 20:
            parts.append(_TEENS[value])
        else:
            tens, ones = divmod(value, 10)
            tens *= 10
            parts.append(_TENS[tens] if ones == 0 else _TENS_CONNECTIVE[tens])
            if ones:
                parts.append(_ONES[ones])
    return " ".join(parts)


def _valid_grouping(value: str) -> bool:
    integer = value.partition(".")[0]
    if "," not in integer:
        return True
    return bool(
        re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+", integer)
        or re.fullmatch(r"[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}", integer)
    )


def _parse_integer(value: str) -> int:
    if not _valid_grouping(value):
        raise ValueError("invalid digit grouping")
    return int(value.replace(",", ""))


def _digit_words(value: str) -> str:
    return " ".join(_ONES[int(character)] for character in value if character.isdigit())


def _verbalize_number(value: str) -> str:
    whole, separator, fraction = value.partition(".")
    integer = _parse_integer(whole)
    words = number_to_malayalam(integer)
    if words is None:
        words = _digit_words(whole)
    if separator:
        words = f"{words} പോയിന്റ് {_digit_words(fraction)}"
    return words


def _verbalize_integer(value: str) -> str:
    integer = _parse_integer(value)
    if value.startswith("0") and len(value) > 1:
        return _digit_words(value)
    return number_to_malayalam(integer) or _digit_words(value)


def _overlaps(start: int, end: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start < other_end and end > other_start for other_start, other_end in spans)


def collect_malayalam_candidates(
    text: str,
    protected_spans: Iterable[tuple[int, int]] = (),
) -> MalayalamNormalizationCandidates:
    """Collect source-relative replacements without mutating the source text."""
    candidates: list[MalayalamNormalizationCandidate] = []
    occupied = list(protected_spans)
    warnings: list[str] = []

    valid_times = {match.span() for match in _TIME_RE.finditer(text)}
    invalid_times = [
        match.span()
        for match in _TIME_LIKE_RE.finditer(text)
        if match.span() not in valid_times
    ]
    if invalid_times:
        occupied.extend(invalid_times)
        warnings.append("Invalid time-like values were preserved.")

    supported_fractions = {match.span() for match in _FRACTION_RE.finditer(text)}
    unsupported_fractions = [
        match.span()
        for match in _FRACTION_LIKE_RE.finditer(text)
        if match.span() not in supported_fractions
    ]
    if unsupported_fractions:
        occupied.extend(unsupported_fractions)
        warnings.append("Unsupported fraction forms were preserved.")

    iso_dates = [match.span() for match in _ISO_DATE_RE.finditer(text)]
    if iso_dates:
        occupied.extend(iso_dates)
        warnings.append("ISO dates were preserved because Malayalam date verbalization is not supported yet.")

    def collect(
        pattern: re.Pattern[str],
        kind: str,
        verbalize: Callable[[re.Match[str]], str],
    ) -> None:
        for match in pattern.finditer(text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            try:
                spoken = verbalize(match)
            except (KeyError, ValueError, OverflowError):
                continue
            if not spoken or spoken == match.group():
                continue
            candidates.append(
                MalayalamNormalizationCandidate(kind, match.start(), match.end(), spoken)
            )
            occupied.append(match.span())

    def currency(match: re.Match[str]) -> str:
        return f"{_verbalize_number(match.group('value'))} {_CURRENCIES[match.group('currency')]}"

    collect(_CURRENCY_PREFIX_RE, "currency", currency)
    collect(_CURRENCY_SUFFIX_RE, "currency", currency)
    collect(
        _PERCENT_RE,
        "percentage",
        lambda match: f"{_verbalize_number(match.group('value'))} ശതമാനം",
    )
    collect(
        _UNIT_RE,
        "unit",
        lambda match: (
            f"{_verbalize_number(match.group('value'))} "
            f"{_UNITS[match.group('unit').lower()]}"
        ),
    )
    collect(
        _TIME_RE,
        "time",
        lambda match: (
            f"{_verbalize_integer(match.group('hour'))} മണി"
            if match.group("minute") == "00"
            else (
                f"{_verbalize_integer(match.group('hour'))} "
                f"{_verbalize_integer(match.group('minute').lstrip('0') or '0')}"
            )
        ),
    )
    collect(
        _MIXED_FRACTION_RE,
        "fraction",
        lambda match: (
            f"{_verbalize_integer(match.group('whole'))} "
            f"{_FRACTIONS[match.group('fraction')]}"
        ),
    )
    collect(
        _FRACTION_RE,
        "fraction",
        lambda match: _FRACTIONS[match.group("fraction")],
    )
    collect(
        _ORDINAL_RE,
        "ordinal",
        lambda match: _ordinal_words(match.group("value")),
    )
    collect(
        _ACRONYM_RE,
        "acronym",
        lambda match: " ".join(_LETTERS[character] for character in match.group()),
    )
    collect(_DECIMAL_RE, "decimal", lambda match: _verbalize_number(match.group("value")))
    collect(_INTEGER_RE, "integer", lambda match: _verbalize_integer(match.group("value")))
    return MalayalamNormalizationCandidates(tuple(candidates), tuple(warnings))


def _ordinal_words(value: str) -> str:
    words = _verbalize_integer(value)
    if words.endswith(("്", "ം")):
        words = words[:-1]
    return f"{words}ാമത്തെ"


__all__ = [
    "MalayalamNormalizationCandidate",
    "MalayalamNormalizationCandidates",
    "collect_malayalam_candidates",
    "number_to_malayalam",
]
