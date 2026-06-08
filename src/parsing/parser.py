"""Heuristic parser for simple natural-language event texts."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re
from typing import Iterable

from .models import ParsedEventDraft, ParseStatus


_RELATIVE_DATE_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (
        re.compile(
            r"\b(?:на\s+|у\s+|в\s+)?післязавтра\b",
            re.IGNORECASE,
        ),
        2,
    ),
    (
        re.compile(r"\b(?:на\s+|у\s+|в\s+)?завтра\b", re.IGNORECASE),
        1,
    ),
    (
        re.compile(r"\b(?:на\s+|у\s+|в\s+)?сьогодні\b", re.IGNORECASE),
        0,
    ),
)

_WEEKDAY_ALIASES: dict[str, int] = {
    "понеділок": 0,
    "понеділка": 0,
    "вівторок": 1,
    "вівторка": 1,
    "середа": 2,
    "середу": 2,
    "четвер": 3,
    "четверга": 3,
    "п'ятниця": 4,
    "п'ятницю": 4,
    "субота": 5,
    "суботу": 5,
    "неділя": 6,
    "неділю": 6,
}

_WEEKDAY_PATTERN = re.compile(
    r"\b(?:на\s+|у\s+|в\s+)?"
    r"(?P<weekday>понеділок|понеділка|вівторок|вівторка|середа|середу|"
    r"четвер|четверга|п'ятниця|п'ятницю|субота|суботу|неділя|неділю)\b",
    re.IGNORECASE,
)

_NUMERIC_DATE_PATTERN = re.compile(
    r"\b(?:на\s+)?(?P<day>0?[1-9]|[12]\d|3[01])"
    r"[./](?P<month>0?[1-9]|1[0-2])"
    r"(?:[./](?P<year>\d{4}))?\b",
    re.IGNORECASE,
)

_DAY_OF_MONTH_PATTERN = re.compile(
    r"\b(?:на\s+)?(?P<day>0?[1-9]|[12]\d|3[01])\s+числа\b",
    re.IGNORECASE,
)

_MONTH_NAMES = {
    "січня": 1,
    "лютого": 2,
    "березня": 3,
    "квітня": 4,
    "травня": 5,
    "червня": 6,
    "липня": 7,
    "серпня": 8,
    "вересня": 9,
    "жовтня": 10,
    "листопада": 11,
    "грудня": 12,
}

_MONTH_NAME_PATTERN = re.compile(
    r"\b(?:на\s+)?(?P<day>0?[1-9]|[12]\d|3[01])\s+"
    r"(?P<month_name>січня|лютого|березня|квітня|травня|червня|липня|"
    r"серпня|вересня|жовтня|листопада|грудня)"
    r"(?:\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)

_TIME_PATTERN = re.compile(
    r"\b(?:(?:о|в)\s+)?(?P<hour>[01]?\d|2[0-3])[:.](?P<minute>[0-5]\d)\b",
    re.IGNORECASE,
)

_WHITESPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCTUATION_RE = re.compile(r"\s+([,.;:!?])")
_SURROUNDING_PUNCTUATION_RE = re.compile(r"^[,.;:!?-]+|[,.;:!?-]+$")
_TITLE_PREFIX_RE = re.compile(
    r"^(?:нагадай|нагадати|нагадування|створи|створити)\s+",
    re.IGNORECASE,
)


def parse_event_text(
    text: str,
    *,
    reference_date: date | None = None,
    reference_datetime: datetime | None = None,
) -> ParsedEventDraft:
    source_text = text.strip()
    if not source_text:
        return ParsedEventDraft(
            source_text=text,
            title=None,
            event_date=None,
            event_time=None,
            event_datetime=None,
            status="invalid",
            errors=("empty_text",),
        )

    reference = reference_date or (reference_datetime.date() if reference_datetime else date.today())
    reference_dt = reference_datetime or datetime.combine(reference, datetime.now().time())
    removed_spans: list[tuple[int, int]] = []

    event_datetime, relative_span = _extract_relative_datetime(source_text, reference_dt)
    date_error = None
    time_error = None

    if event_datetime is not None:
        event_date = event_datetime.date()
        event_time = event_datetime.time().replace(microsecond=0)
        removed_spans.append(relative_span)
    else:
        event_date, date_span, date_error = _extract_date(source_text, reference)
        if date_span is not None:
            removed_spans.append(date_span)

        event_time, time_span, time_error = _extract_time(source_text)
        if time_span is not None:
            removed_spans.append(time_span)

    title = _extract_title(source_text, removed_spans)

    missing_fields: list[str] = []
    errors: list[str] = []

    if event_date is None:
        missing_fields.append("date")
        if date_error is not None:
            errors.append(date_error)

    if event_time is None:
        missing_fields.append("time")
        if time_error is not None:
            errors.append(time_error)

    if not title:
        missing_fields.append("title")
        errors.append("missing_title")

    status: ParseStatus
    if errors and source_text:
        status = "needs_clarification" if missing_fields else "invalid"
    elif missing_fields:
        status = "needs_clarification"
    else:
        status = "complete"

    if event_datetime is None:
        event_datetime = (
            datetime.combine(event_date, event_time)
            if event_date is not None and event_time is not None
            else None
        )

    confidence = _calculate_confidence(
        status=status,
        event_datetime=event_datetime,
        title=title,
        errors=errors,
        missing_fields=missing_fields,
    )

    return ParsedEventDraft(
        source_text=source_text,
        title=title or None,
        event_date=event_date,
        event_time=event_time,
        event_datetime=event_datetime,
        status=status,
        missing_fields=tuple(missing_fields),
        errors=tuple(dict.fromkeys(errors)),
        confidence=confidence,
        parser_source="local",
    )


def _extract_relative_datetime(
    text: str,
    reference_datetime: datetime,
) -> tuple[datetime | None, tuple[int, int] | None]:
    marker = re.search(r"\bчерез\b", text, re.IGNORECASE)
    if marker is None:
        return None, None

    position = marker.end()
    hours = 0
    minutes = 0
    matched_end = position
    tail = text[position:]

    half_hour_match = re.match(r"\s*(?:пів\s*години|півгодини)\b", tail, re.IGNORECASE)
    if half_hour_match is not None:
        minutes = 30
        matched_end = position + half_hour_match.end()
        return (
            reference_datetime.replace(microsecond=0) + timedelta(minutes=minutes),
            (marker.start(), matched_end),
        )

    component_pattern = re.compile(
        r"\s*(?:(?P<number>\d+)\s*)?"
        r"(?P<unit>год(?:\.|ину|ини|ин)?|хв(?:\.|илину|илини|илин)?)\b",
        re.IGNORECASE,
    )

    while True:
        component = component_pattern.match(text, matched_end)
        if component is None:
            break

        unit = component.group("unit").lower().rstrip(".")
        number_raw = component.group("number")
        if number_raw is None:
            if unit.startswith("год"):
                amount = 1
            else:
                break
        else:
            amount = int(number_raw)

        if unit.startswith("год"):
            hours += amount
        else:
            minutes += amount

        matched_end = component.end()

    if hours == 0 and minutes == 0:
        return None, None

    return (
        reference_datetime.replace(microsecond=0) + timedelta(hours=hours, minutes=minutes),
        (marker.start(), matched_end),
    )


def _extract_date(
    text: str,
    reference_date: date,
) -> tuple[date | None, tuple[int, int] | None, str | None]:
    for pattern, delta_days in _RELATIVE_DATE_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return reference_date + timedelta(days=delta_days), match.span(), None

    weekday_match = _WEEKDAY_PATTERN.search(text)
    if weekday_match is not None:
        weekday_name = weekday_match.group("weekday").lower()
        weekday = _WEEKDAY_ALIASES[weekday_name]
        days_ahead = (weekday - reference_date.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return reference_date + timedelta(days=days_ahead), weekday_match.span(), None

    numeric_match = _NUMERIC_DATE_PATTERN.search(text)
    if numeric_match is not None:
        try:
            event_date = _build_date(
                year=int(numeric_match.group("year") or reference_date.year),
                month=int(numeric_match.group("month")),
                day=int(numeric_match.group("day")),
                reference_date=reference_date,
                year_was_explicit=numeric_match.group("year") is not None,
            )
        except ValueError:
            return None, numeric_match.span(), "invalid_date"
        return event_date, numeric_match.span(), None

    month_match = _MONTH_NAME_PATTERN.search(text)
    if month_match is not None:
        month_name = month_match.group("month_name").lower()
        try:
            event_date = _build_date(
                year=int(month_match.group("year") or reference_date.year),
                month=_MONTH_NAMES[month_name],
                day=int(month_match.group("day")),
                reference_date=reference_date,
                year_was_explicit=month_match.group("year") is not None,
            )
        except ValueError:
            return None, month_match.span(), "invalid_date"
        return event_date, month_match.span(), None

    day_match = _DAY_OF_MONTH_PATTERN.search(text)
    if day_match is not None:
        try:
            event_date = _build_day_of_month_date(
                day=int(day_match.group("day")),
                reference_date=reference_date,
            )
        except ValueError:
            return None, day_match.span(), "invalid_date"
        return event_date, day_match.span(), None

    return None, None, None


def _build_date(
    *,
    year: int,
    month: int,
    day: int,
    reference_date: date,
    year_was_explicit: bool,
) -> date:
    event_date = date(year, month, day)
    if not year_was_explicit and event_date < reference_date:
        event_date = date(year + 1, month, day)
    return event_date


def _build_day_of_month_date(*, day: int, reference_date: date) -> date:
    year = reference_date.year
    month = reference_date.month

    try:
        event_date = date(year, month, day)
    except ValueError:
        event_date = _next_month_date(year=year, month=month, day=day)

    if event_date < reference_date:
        event_date = _next_month_date(year=year, month=month, day=day)

    return event_date


def _next_month_date(*, year: int, month: int, day: int) -> date:
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    return date(next_year, next_month, day)


def _extract_time(text: str) -> tuple[time | None, tuple[int, int] | None, str | None]:
    match = _TIME_PATTERN.search(text)
    if match is None:
        return None, None, None

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    try:
        event_time = time(hour=hour, minute=minute)
    except ValueError:
        return None, match.span(), "invalid_time"
    return event_time, match.span(), None


def _extract_title(text: str, removed_spans: Iterable[tuple[int, int]]) -> str:
    if not removed_spans:
        return _normalize_title(text)

    characters = list(text)
    for start, end in removed_spans:
        for index in range(start, end):
            characters[index] = " "

    cleaned = "".join(characters)
    cleaned = _SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    cleaned = cleaned.strip()
    cleaned = _SURROUNDING_PUNCTUATION_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    cleaned = re.sub(r"^(?:о|в|у|на)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = _SURROUNDING_PUNCTUATION_RE.sub("", cleaned).strip()
    cleaned = _TITLE_PREFIX_RE.sub("", cleaned).strip()
    return cleaned or ""


def _normalize_title(text: str) -> str:
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    normalized = _SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", normalized)
    normalized = _TITLE_PREFIX_RE.sub("", normalized).strip()
    return normalized


def _calculate_confidence(
    *,
    status: ParseStatus,
    event_datetime: datetime | None,
    title: str | None,
    errors: list[str],
    missing_fields: list[str],
) -> float:
    if status == "invalid":
        return 0.0
    if status == "complete" and event_datetime is not None and title:
        return 0.92
    if status == "needs_clarification":
        penalty = 0.2 * len(missing_fields) + 0.1 * len(errors)
        return max(0.2, 0.75 - penalty)
    return 0.4
