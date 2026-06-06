"""Business logic for user-driven event creation and listing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import re

from db.models import EventRecord
from db.repository import SQLiteRepository
from services.timezone_service import TimezoneService


_DATE_PATTERNS = (
    re.compile(r"^(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})$"),
)

_TIME_PATTERN = re.compile(r"^(?P<hour>\d{1,2})[:.](?P<minute>\d{2})$")


@dataclass(frozen=True, slots=True)
class EventDraftInput:
    title: str
    event_date: date
    event_time: time


@dataclass(slots=True)
class EventService:
    repository: SQLiteRepository
    timezone_service: TimezoneService
    default_reminder_minutes: int = 15

    def parse_date(self, raw_value: str, *, reference_date: date | None = None) -> date:
        value = raw_value.strip().lower()
        if not value:
            raise ValueError("Дата не може бути порожньою")

        reference = reference_date or date.today()
        if value in {"сьогодні", "сьогоднi", "today"}:
            return reference
        if value in {"завтра", "tomorrow"}:
            return reference + timedelta(days=1)
        if value in {"післязавтра", "після завтра", "day after tomorrow"}:
            return reference + timedelta(days=2)

        for pattern in _DATE_PATTERNS:
            match = pattern.match(value)
            if match is not None:
                day = int(match.group("day"))
                month = int(match.group("month"))
                year = int(match.group("year"))
                return date(year, month, day)

        raise ValueError("Невідомий формат дати")

    def parse_time(self, raw_value: str) -> time:
        value = raw_value.strip().lower()
        if not value:
            raise ValueError("Час не може бути порожнім")

        match = _TIME_PATTERN.match(value)
        if match is None:
            raise ValueError("Невідомий формат часу")

        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        return time(hour=hour, minute=minute)

    def build_preview_text(
        self,
        *,
        title: str,
        event_date: date,
        event_time: time,
        timezone: str,
    ) -> str:
        return (
            "Подія:\n"
            f"{title}\n\n"
            f"Дата: {event_date.strftime('%d.%m.%Y')}\n"
            f"Час: {event_time.strftime('%H:%M')}\n"
            f"Часовий пояс: {timezone}\n\n"
            "Створити подію?"
        )

    def build_created_text(self, event: EventRecord) -> str:
        return (
            "✅ Подію створено.\n\n"
            f"Подія: {event.title}\n"
            f"Дата і час: {event.event_at}\n"
            f"Часовий пояс: {event.timezone}"
        )

    def build_future_events_text(self, telegram_id: int) -> str:
        events = self.repository.list_future_events_for_user(telegram_id)
        if not events:
            return "У вас поки немає подій."

        lines = ["Ваші майбутні події:"]
        for index, event in enumerate(events, start=1):
            local_text = self.format_event_local_text(event.event_at)
            lines.append(f"{index}. {event.title}")
            lines.append(local_text)
            lines.append("")

        return "\n".join(lines).strip()

    def create_event(
        self,
        telegram_id: int,
        *,
        title: str,
        event_date: date,
        event_time: time,
    ) -> EventRecord:
        timezone = self.timezone_service.get_user_timezone(telegram_id)
        local_datetime = datetime.combine(event_date, event_time)
        reminder_local_datetime = local_datetime - timedelta(
            minutes=self.default_reminder_minutes
        )

        event_at_utc = self.timezone_service.to_utc_isoformat(
            local_datetime,
            timezone,
        )
        event_at = self.timezone_service.format_local_isoformat(
            local_datetime,
            timezone,
        )
        reminder_at_utc = self.timezone_service.to_utc_isoformat(
            reminder_local_datetime,
            timezone,
        )
        reminder_at = self.timezone_service.format_local_isoformat(
            reminder_local_datetime,
            timezone,
        )

        event, _reminder = self.repository.create_event_with_reminder(
            telegram_id,
            title=title,
            event_at=event_at,
            event_at_utc=event_at_utc,
            reminder_at=reminder_at,
            reminder_at_utc=reminder_at_utc,
            timezone=timezone,
        )
        if reminder_at_utc != event_at_utc:
            self.repository.create_reminder(
                event.id,
                reminder_at=event_at,
                reminder_at_utc=event_at_utc,
            )
        return event

    def get_future_events(self, telegram_id: int) -> list[EventRecord]:
        return self.repository.list_future_events_for_user(telegram_id)

    def get_events_for_deletion(self, telegram_id: int) -> list[EventRecord]:
        return self.repository.list_events_for_user(telegram_id)

    def delete_event(self, telegram_id: int, event_id: int) -> EventRecord | None:
        return self.repository.delete_event_for_user(telegram_id, event_id)

    def _format_event_local_text(self, event_at: str) -> str:
        try:
            dt = datetime.fromisoformat(event_at)
        except ValueError:
            return event_at

        return dt.strftime("%d.%m.%Y %H:%M")

    def format_event_local_text(self, event_at: str) -> str:
        return self._format_event_local_text(event_at)
