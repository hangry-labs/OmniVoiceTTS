"""Conservative Vietnamese structured-text verbalization rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable


@dataclass(frozen=True)
class VietnameseNormalizationCandidate:
    kind: str
    start: int
    end: int
    spoken: str


@dataclass(frozen=True)
class VietnameseNormalizationCandidates:
    candidates: tuple[VietnameseNormalizationCandidate, ...]
    warnings: tuple[str, ...]


_DIGITS = (
    "không",
    "một",
    "hai",
    "ba",
    "bốn",
    "năm",
    "sáu",
    "bảy",
    "tám",
    "chín",
)
_SCALES = ("", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ")
_UNITS = {
    "km/h": "ki lô mét trên giờ",
    "m/s": "mét trên giây",
    "kwh": "ki lô oát giờ",
    "mhz": "mê ga héc",
    "ghz": "gi ga héc",
    "km": "ki lô mét",
    "cm": "xen ti mét",
    "mm": "mi li mét",
    "kg": "ki lô gam",
    "mg": "mi li gam",
    "ml": "mi li lít",
    "gb": "gi ga bai",
    "mb": "mê ga bai",
    "tb": "tê ra bai",
    "°c": "độ xê",
    "°f": "độ ép",
    "m": "mét",
    "g": "gam",
    "l": "lít",
    "w": "oát",
    "v": "vôn",
    "hz": "héc",
}
_CURRENCIES = {
    "₫": "đồng",
    "đ": "đồng",
    "vnd": "đồng",
    "vnđ": "đồng",
    "đồng": "đồng",
    "$": "đô la Mỹ",
    "usd": "đô la Mỹ",
    "€": "euro",
    "eur": "euro",
}
_MAX_DIGITS = 18

_SIGN = r"[+\-−]?"
_PLAIN_INTEGER = r"\d+"
_DOT_GROUPED_INTEGER = r"\d{1,3}(?:\.\d{3})+"
_NUMBER_TOKEN = (
    rf"{_SIGN}(?:{_DOT_GROUPED_INTEGER}(?:,\d+)?|"
    rf"{_PLAIN_INTEGER}(?:,\d+|\.\d{{1,2}}|\.\d{{4,}})?)"
)
_CURRENCY_TOKEN = r"VND|VNĐ|USD|EUR|đồng|₫|đ|\$|€"
_UNIT_TOKEN = "|".join(sorted((re.escape(unit) for unit in _UNITS), key=len, reverse=True))

_CURRENCY_PREFIX_RE = re.compile(
    rf"(?<![\w.])(?P<currency>{_CURRENCY_TOKEN})\s*"
    rf"(?P<value>{_NUMBER_TOKEN})(?:\s*(?P<multiplier>triệu|tỷ))?"
    r"(?!\w)(?![.,]\d)",
    re.IGNORECASE,
)
_CURRENCY_SUFFIX_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*"
    rf"(?:(?P<multiplier>triệu|tỷ)\s*)?(?P<currency>{_CURRENCY_TOKEN})(?!\w)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*%(?!\w)",
    re.IGNORECASE,
)
_UNIT_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*(?P<unit>{_UNIT_TOKEN})(?!\w)",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(
    r"(?<!\w)(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(?!\w)"
)
_TIME_RE = re.compile(
    r"(?<![\w:])(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"(?::(?P<second>\d{2}))?(?![\w:])"
)
_DECIMAL_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_SIGN}(?:{_DOT_GROUPED_INTEGER},\d+|"
    r"\d+(?:,\d+|\.\d{1,2}|\.\d{4,})))(?![\w.])(?![.,]\d)"
)
_INTEGER_RE = re.compile(rf"(?<![\w.])(?P<value>{_SIGN}\d+)(?![\w.])(?![.,]\d)")

_SLASH_VALUE_RE = re.compile(r"(?<!\w)\d+(?:\s*/\s*\d+)+(?!\w)")
_DOTTED_AMBIGUOUS_RE = re.compile(
    rf"(?<![\w.]){_SIGN}{_DOT_GROUPED_INTEGER}(?!\w)(?![.,]\d)"
)
_COMMA_AMBIGUOUS_RE = re.compile(
    rf"(?<![\w.,]){_SIGN}\d+,\d{{3}}(?!\w)(?![.,]\d)"
)
_TIME_LIKE_RE = re.compile(r"(?<![\w:])\d{1,2}:\d{2}(?::\d{2})?(?![\w:])")
_LEADING_ZERO_RE = re.compile(r"(?<![\w:])0\d+(?![\w:.-])")
_LONG_DIGIT_SEQUENCE_RE = re.compile(r"(?<!\w)\d{7,}(?!\w)")
_SEPARATED_DIGIT_SEQUENCE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]){1,}\d{3,4}(?!\w)"
)
_IDENTIFIER_CONTEXT_RE = re.compile(
    r"(?:mã(?:\s+số|\s+sinh\s+viên|\s+đơn\s+hàng)?|cccd|số\s+tài\s+khoản|phòng)"
    r"\s*(?:là|:)?\s*(?P<value>\d+)",
    re.IGNORECASE,
)
_PUNCTUATED_NUMBER_RE = re.compile(
    rf"(?<![\w.,]){_SIGN}\d[\d.,]*\d(?!\w)(?![.,]\d)"
)


def _read_three_digits(number: int, *, force_hundreds: bool = False) -> str:
    hundreds = number // 100
    tens = (number % 100) // 10
    ones = number % 10
    words: list[str] = []

    if hundreds:
        words.extend((_DIGITS[hundreds], "trăm"))
    elif force_hundreds and (tens or ones):
        words.extend(("không", "trăm"))

    if tens >= 2:
        words.extend((_DIGITS[tens], "mươi"))
        if ones == 1:
            words.append("mốt")
        elif ones == 4:
            words.append("tư")
        elif ones == 5:
            words.append("lăm")
        elif ones:
            words.append(_DIGITS[ones])
    elif tens == 1:
        words.append("mười")
        if ones == 5:
            words.append("lăm")
        elif ones:
            words.append(_DIGITS[ones])
    elif ones:
        if hundreds or force_hundreds:
            words.append("linh")
        words.append(_DIGITS[ones])

    return " ".join(words)


def number_to_vietnamese(value: int | str) -> str:
    """Convert a signed integer of at most 18 digits to Vietnamese words."""
    raw = str(value).strip().replace("−", "-")
    negative = raw.startswith("-")
    if raw[:1] in {"+", "-"}:
        raw = raw[1:]
    if not raw or not raw.isdigit() or len(raw) > _MAX_DIGITS:
        raise ValueError("Vietnamese cardinal must contain at most 18 digits.")

    number = int(raw)
    if number == 0:
        return _DIGITS[0]

    groups: list[int] = []
    while number:
        groups.append(number % 1000)
        number //= 1000
    if len(groups) > len(_SCALES):
        raise ValueError("Vietnamese cardinal exceeds the supported scale.")

    words: list[str] = []
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        if not group:
            continue
        words.append(
            _read_three_digits(group, force_hundreds=any(groups[index + 1 :]))
        )
        if _SCALES[index]:
            words.append(_SCALES[index])
    spoken = " ".join(words)
    return f"âm {spoken}" if negative else spoken


def _parse_number(value: str, *, allow_grouped_dot: bool = True) -> tuple[str, str | None]:
    raw = value.strip().replace("−", "-")
    sign = raw[:1] if raw[:1] in {"+", "-"} else ""
    if sign:
        raw = raw[1:]

    fraction: str | None = None
    if "," in raw:
        if raw.count(",") != 1:
            raise ValueError("Malformed Vietnamese decimal.")
        integer, fraction = raw.split(",")
        if not fraction.isdigit():
            raise ValueError("Malformed Vietnamese decimal fraction.")
        if "." not in integer and len(fraction) == 3:
            raise ValueError("Ambiguous comma-separated number.")
        if "." in integer:
            if not re.fullmatch(_DOT_GROUPED_INTEGER, integer):
                raise ValueError("Malformed Vietnamese digit grouping.")
            integer = integer.replace(".", "")
    elif "." in raw:
        if re.fullmatch(_DOT_GROUPED_INTEGER, raw):
            if not allow_grouped_dot:
                raise ValueError("Ambiguous dotted number.")
            integer = raw.replace(".", "")
        else:
            if raw.count(".") != 1:
                raise ValueError("Malformed Vietnamese decimal.")
            integer, fraction = raw.split(".")
            if len(fraction) == 3 or not fraction.isdigit():
                raise ValueError("Ambiguous or malformed dotted number.")
    else:
        integer = raw

    if not integer.isdigit() or len(integer) > _MAX_DIGITS:
        raise ValueError("Vietnamese number is outside the supported range.")
    return f"{sign}{integer}", fraction


def _verbalize_number(value: str, *, allow_grouped_dot: bool = True) -> str:
    integer, fraction = _parse_number(value, allow_grouped_dot=allow_grouped_dot)
    words = number_to_vietnamese(integer)
    if fraction is not None:
        words = f"{words} phẩy {' '.join(_DIGITS[int(digit)] for digit in fraction)}"
    return words


def _overlaps(start: int, end: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start < other_end and end > other_start for other_start, other_end in spans)


def collect_vietnamese_candidates(
    text: str,
    protected_spans: Iterable[tuple[int, int]] = (),
) -> VietnameseNormalizationCandidates:
    """Collect source-relative Vietnamese replacements without guessing context."""
    candidates: list[VietnameseNormalizationCandidate] = []
    occupied = list(protected_spans)
    warnings: list[str] = []

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
                VietnameseNormalizationCandidate(kind, match.start(), match.end(), spoken)
            )
            occupied.append(match.span())

    def date_words(match: re.Match[str]) -> str:
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
        parsed = date(year, month, day)
        prefix = (
            ""
            if re.search(r"\bngày\s*$", text[: match.start()], re.IGNORECASE)
            else "ngày "
        )
        return (
            f"{prefix}{number_to_vietnamese(parsed.day)} tháng "
            f"{number_to_vietnamese(parsed.month)} năm {number_to_vietnamese(parsed.year)}"
        )

    def time_words(match: re.Match[str]) -> str:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        second_raw = match.group("second")
        if hour > 23 or minute > 59 or (second_raw is not None and int(second_raw) > 59):
            raise ValueError("Invalid time.")
        spoken = f"{number_to_vietnamese(hour)} giờ {number_to_vietnamese(minute)} phút"
        if second_raw is not None:
            spoken += f" {number_to_vietnamese(int(second_raw))} giây"
        return spoken

    def currency_words(match: re.Match[str]) -> str:
        spoken = _verbalize_number(match.group("value"))
        multiplier = match.group("multiplier")
        if multiplier:
            spoken += f" {multiplier.lower()}"
        return f"{spoken} {_CURRENCIES[match.group('currency').lower()]}"

    collect(_ISO_DATE_RE, "date", date_words)
    collect(_TIME_RE, "time", time_words)
    collect(_CURRENCY_PREFIX_RE, "currency", currency_words)
    collect(_CURRENCY_SUFFIX_RE, "currency", currency_words)
    collect(
        _PERCENT_RE,
        "percentage",
        lambda match: f"{_verbalize_number(match.group('value'))} phần trăm",
    )
    collect(
        _UNIT_RE,
        "unit",
        lambda match: (
            f"{_verbalize_number(match.group('value'))} "
            f"{_UNITS[match.group('unit').lower()]}"
        ),
    )

    invalid_iso_dates = [
        match.span()
        for match in _ISO_DATE_RE.finditer(text)
        if not _overlaps(match.start(), match.end(), occupied)
    ]
    if invalid_iso_dates:
        occupied.extend(invalid_iso_dates)
        warnings.append("Invalid ISO dates were preserved.")

    valid_times = {
        match.span()
        for match in _TIME_RE.finditer(text)
        if not _overlaps(match.start(), match.end(), occupied)
        and int(match.group("hour")) <= 23
        and int(match.group("minute")) <= 59
        and (match.group("second") is None or int(match.group("second")) <= 59)
    }
    invalid_times = [
        match.span()
        for match in _TIME_LIKE_RE.finditer(text)
        if match.span() not in valid_times and not _overlaps(*match.span(), occupied)
    ]
    if invalid_times:
        occupied.extend(invalid_times)
        warnings.append("Invalid time-like values were preserved.")

    guarded_patterns = (
        (
            _SLASH_VALUE_RE,
            "Slash-form numeric values were preserved because their meaning is ambiguous.",
        ),
        (
            _DOTTED_AMBIGUOUS_RE,
            "Unmarked dotted values were preserved because decimal and grouping forms are ambiguous.",
        ),
        (
            _COMMA_AMBIGUOUS_RE,
            "Single-comma values with three trailing digits were preserved as ambiguous.",
        ),
        (
            _SEPARATED_DIGIT_SEQUENCE_RE,
            "Separated digit sequences were preserved as possible phone numbers or identifiers.",
        ),
        (
            _LEADING_ZERO_RE,
            "Leading-zero digit sequences were preserved as possible identifiers.",
        ),
        (
            _LONG_DIGIT_SEQUENCE_RE,
            "Long digit sequences were preserved as possible phone numbers or identifiers.",
        ),
    )
    for pattern, warning in guarded_patterns:
        spans = [
            match.span()
            for match in pattern.finditer(text)
            if not _overlaps(match.start(), match.end(), occupied)
        ]
        if spans:
            occupied.extend(spans)
            warnings.append(warning)

    identifier_spans = [
        match.span("value")
        # Input is capped at MAX_NORMALIZATION_CHARACTERS by normalize_structured_text.
        # codeql[py/polynomial-redos]
        for match in _IDENTIFIER_CONTEXT_RE.finditer(text)
        if not _overlaps(*match.span("value"), occupied)
    ]
    if identifier_spans:
        occupied.extend(identifier_spans)
        warnings.append("Numbers in explicit identifier contexts were preserved.")

    supported_numeric_spans = {
        match.span() for match in _DECIMAL_RE.finditer(text)
    }
    malformed_numeric_spans = [
        match.span()
        for match in _PUNCTUATED_NUMBER_RE.finditer(text)
        if any(character in match.group() for character in ".,")
        and match.span() not in supported_numeric_spans
        and not _overlaps(match.start(), match.end(), occupied)
    ]
    if malformed_numeric_spans:
        occupied.extend(malformed_numeric_spans)
        warnings.append("Malformed or unsupported numeric punctuation was preserved.")

    collect(
        _DECIMAL_RE,
        "decimal",
        lambda match: _verbalize_number(match.group("value"), allow_grouped_dot=False),
    )
    collect(_INTEGER_RE, "integer", lambda match: _verbalize_number(match.group("value")))
    return VietnameseNormalizationCandidates(tuple(candidates), tuple(warnings))


__all__ = [
    "VietnameseNormalizationCandidate",
    "VietnameseNormalizationCandidates",
    "collect_vietnamese_candidates",
    "number_to_vietnamese",
]
