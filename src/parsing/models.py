"""Data models for parsed event drafts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Literal


ParseStatus = Literal["complete", "needs_clarification", "invalid"]
ParserSource = Literal["local", "gemini"]


@dataclass(frozen=True, slots=True)
class ParsedEventDraft:
    source_text: str
    title: str | None
    event_date: date | None
    event_time: time | None
    event_datetime: datetime | None
    status: ParseStatus
    missing_fields: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    confidence: float = 0.0
    parser_source: ParserSource = "local"
