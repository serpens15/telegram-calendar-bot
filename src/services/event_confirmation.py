"""Event preview, confirmation, and cancellation flow."""

from __future__ import annotations

from dataclasses import dataclass, field

from db.repository import SQLiteRepository
from parsing.models import ParsedEventDraft
from services.timezone_service import TimezoneService


@dataclass(slots=True)
class EventConfirmationService:
    repository: SQLiteRepository
    timezone_service: TimezoneService
    default_timezone: str
    _pending_events: dict[int, ParsedEventDraft] = field(default_factory=dict)

    def _get_user_timezone(self, telegram_id: int) -> str:
        user = self.repository.get_or_create_user(
            telegram_id,
            timezone=self.default_timezone,
        )
        return user.timezone

    def build_preview_text(self, draft: ParsedEventDraft, timezone: str) -> str:
        lines = ["Preview:"]
        lines.append(f"Title: {draft.title or 'Untitled'}")

        if draft.event_datetime is not None:
            local_event = self.timezone_service.format_local_isoformat(
                draft.event_datetime,
                timezone,
            )
            utc_event = self.timezone_service.to_utc_isoformat(
                draft.event_datetime,
                timezone,
            )
            lines.append(f"When: {local_event}")
            lines.append(f"UTC: {utc_event}")
        else:
            lines.append("When: incomplete")

        lines.append(f"Timezone: {timezone}")
        lines.append("")
        lines.append("Reply /confirm to save or /cancel to discard.")

        if draft.source_text:
            lines.append("")
            lines.append(f"Source: {draft.source_text}")

        return "\n".join(lines)

    def build_clarification_text(self, draft: ParsedEventDraft) -> str:
        missing = ", ".join(draft.missing_fields) if draft.missing_fields else "details"
        return (
            "I need a bit more information.\n\n"
            f"Missing: {missing}\n"
            "Please send a clearer event text."
        )

    def set_pending(self, telegram_id: int, draft: ParsedEventDraft) -> None:
        self._pending_events[telegram_id] = draft

    def get_pending(self, telegram_id: int) -> ParsedEventDraft | None:
        return self._pending_events.get(telegram_id)

    def clear_pending(self, telegram_id: int) -> None:
        self._pending_events.pop(telegram_id, None)

    def create_event_from_pending(self, telegram_id: int):
        draft = self._pending_events.get(telegram_id)
        if draft is None:
            return None

        if draft.event_datetime is None:
            return None

        timezone = self._get_user_timezone(telegram_id)
        event_at_local = self.timezone_service.format_local_isoformat(
            draft.event_datetime,
            timezone,
        )
        event_at_utc = self.timezone_service.to_utc_isoformat(
            draft.event_datetime,
            timezone,
        )
        event = self.repository.create_event(
            telegram_id,
            title=draft.title or "Untitled",
            event_at=event_at_local,
            event_at_utc=event_at_utc,
            timezone=timezone,
            source_text=draft.source_text,
        )
        self.clear_pending(telegram_id)
        return event

    def preview_or_clarify(self, telegram_id: int, draft: ParsedEventDraft) -> str:
        if draft.status == "complete":
            self.set_pending(telegram_id, draft)
            timezone = self._get_user_timezone(telegram_id)
            return self.build_preview_text(draft, timezone)

        return self.build_clarification_text(draft)

    def confirm_pending(self, telegram_id: int):
        return self.create_event_from_pending(telegram_id)

    def cancel_pending(self, telegram_id: int) -> bool:
        existed = telegram_id in self._pending_events
        self.clear_pending(telegram_id)
        return existed
