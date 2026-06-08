"""Parser orchestration with local-first AI fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from .models import ParsedEventDraft
from .parser import parse_event_text


class EventTextAIParser(Protocol):
    def parse_event_text(
        self,
        text: str,
        *,
        reference_date: date | None = None,
    ) -> ParsedEventDraft | None:
        ...


@dataclass(frozen=True, slots=True)
class ParserService:
    ai_parser: EventTextAIParser | None = None
    confidence_threshold: float = 0.85

    def parse(
        self,
        text: str,
        *,
        reference_date: date | None = None,
        reference_datetime: datetime | None = None,
    ) -> ParsedEventDraft:
        local_draft = parse_event_text(
            text,
            reference_date=reference_date,
            reference_datetime=reference_datetime,
        )
        if self._is_confident(local_draft):
            return local_draft

        if self.ai_parser is None:
            return local_draft

        ai_draft = self.ai_parser.parse_event_text(
            text,
            reference_date=reference_date or (
                reference_datetime.date() if reference_datetime else None
            ),
        )
        if ai_draft is None:
            return local_draft
        if ai_draft.status == "complete" and ai_draft.confidence >= self.confidence_threshold:
            return ai_draft

        return local_draft

    def _is_confident(self, draft: ParsedEventDraft) -> bool:
        return draft.status == "complete" and draft.confidence >= self.confidence_threshold
