"""Timezone management for user profiles."""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from db.repository import SQLiteRepository


SUPPORTED_TIMEZONES = {
    "UTC",
    "Europe/Kyiv",
    "Europe/Kiev",
    "Europe/Warsaw",
    "Europe/Berlin",
    "Europe/London",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
}


@dataclass(slots=True)
class TimezoneService:
    repository: SQLiteRepository
    default_timezone: str

    def _ensure_user(self, telegram_id: int):
        return self.repository.get_or_create_user(
            telegram_id,
            timezone=self.default_timezone,
        )

    def get_user_timezone(self, telegram_id: int) -> str:
        user = self._ensure_user(telegram_id)
        return user.timezone

    def set_user_timezone(self, telegram_id: int, timezone: str):
        self.validate_timezone(timezone)
        self._ensure_user(telegram_id)
        return self.repository.update_user_timezone(telegram_id, timezone)

    def validate_timezone(self, timezone: str) -> None:
        if timezone in SUPPORTED_TIMEZONES:
            return

        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {timezone}") from exc
