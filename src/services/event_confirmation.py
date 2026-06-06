"""Event preview, confirmation, and cancellation flow."""

from __future__ import annotations

from dataclasses import dataclass, field

from db.models import EventRecord
from db.repository import SQLiteRepository
from parsing.models import ParsedEventDraft
from services.timezone_service import TimezoneService


@dataclass(slots=True)
class EventConfirmationService:
    repository: SQLiteRepository
    timezone_service: TimezoneService
    default_timezone: str
    _pending_events: dict[int, ParsedEventDraft] = field(default_factory=dict)
    _pending_deletes: dict[int, int] = field(default_factory=dict)

    def _get_user_timezone(self, telegram_id: int) -> str:
        user = self.repository.get_or_create_user(
            telegram_id,
            timezone=self.default_timezone,
        )
        return user.timezone

    def build_preview_text(self, draft: ParsedEventDraft, timezone: str) -> str:
        lines = ["Попередній перегляд:"]
        lines.append(f"Назва: {draft.title or 'Без назви'}")

        if draft.event_datetime is not None:
            local_event = self.timezone_service.format_local_isoformat(
                draft.event_datetime,
                timezone,
            )
            utc_event = self.timezone_service.to_utc_isoformat(
                draft.event_datetime,
                timezone,
            )
            lines.append(f"Коли: {local_event}")
            lines.append(f"UTC: {utc_event}")
        else:
            lines.append("Коли: неповні дані")

        lines.append(f"Часовий пояс: {timezone}")
        lines.append("")
        lines.append("Надішліть /confirm, щоб зберегти, або /cancel, щоб скасувати.")

        if draft.source_text:
            lines.append("")
            lines.append(f"Джерело: {draft.source_text}")

        return "\n".join(lines)

    def build_clarification_text(self, draft: ParsedEventDraft) -> str:
        missing = ", ".join(draft.missing_fields) if draft.missing_fields else "деталі"
        return (
            "Потрібно трохи більше інформації.\n\n"
            f"Бракує: {missing}\n"
            "Надішліть більш зрозумілий текст події."
        )

    def set_pending(self, telegram_id: int, draft: ParsedEventDraft) -> None:
        self._pending_events[telegram_id] = draft

    def get_pending(self, telegram_id: int) -> ParsedEventDraft | None:
        return self._pending_events.get(telegram_id)

    def has_pending_event(self, telegram_id: int) -> bool:
        return telegram_id in self._pending_events

    def clear_pending(self, telegram_id: int) -> None:
        self._pending_events.pop(telegram_id, None)

    def list_events_for_user(self, telegram_id: int) -> list[EventRecord]:
        return self.repository.list_events_for_user(telegram_id)

    def build_events_list_text(self, telegram_id: int) -> str:
        events = self.list_events_for_user(telegram_id)
        if not events:
            return "У вас немає найближчих подій."

        lines = ["Найближчі події:"]
        for event in events:
            lines.append(
                f"{event.id}. {event.title} | {event.event_at} | {event.timezone}"
            )

        lines.append("")
        lines.append("Використайте /delete <id>, щоб видалити подію.")
        return "\n".join(lines)

    def build_delete_preview_text(self, event: EventRecord) -> str:
        return (
            "Видалити цю подію?\n\n"
            f"ID: {event.id}\n"
            f"Назва: {event.title}\n"
            f"Коли: {event.event_at}\n"
            f"Часовий пояс: {event.timezone}\n\n"
            "Надішліть /confirm, щоб видалити, або /cancel, щоб скасувати."
        )

    def set_pending_delete(self, telegram_id: int, event_id: int) -> None:
        self._pending_deletes[telegram_id] = event_id

    def get_pending_delete(self, telegram_id: int) -> int | None:
        return self._pending_deletes.get(telegram_id)

    def has_pending_delete(self, telegram_id: int) -> bool:
        return telegram_id in self._pending_deletes

    def clear_pending_delete(self, telegram_id: int) -> None:
        self._pending_deletes.pop(telegram_id, None)

    def request_delete(self, telegram_id: int, event_id: int) -> str | None:
        event = self.repository.get_event_for_user(telegram_id, event_id)
        if event is None:
            return None

        self.set_pending_delete(telegram_id, event_id)
        return self.build_delete_preview_text(event)

    def create_event_from_pending(self, telegram_id: int):
        draft = self._pending_events.get(telegram_id)
        if draft is None or draft.event_datetime is None:
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
            title=draft.title or "Без назви",
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

    def confirm_pending_delete(self, telegram_id: int) -> EventRecord | None:
        event_id = self.get_pending_delete(telegram_id)
        if event_id is None:
            return None

        deleted_event = self.repository.delete_event_for_user(telegram_id, event_id)
        self.clear_pending_delete(telegram_id)
        return deleted_event

    def cancel_pending(self, telegram_id: int) -> bool:
        existed = telegram_id in self._pending_events or telegram_id in self._pending_deletes
        self.clear_pending(telegram_id)
        self.clear_pending_delete(telegram_id)
        return existed
