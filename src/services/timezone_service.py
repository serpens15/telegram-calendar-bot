"""Timezone management for user profiles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone, tzinfo
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


def _last_weekday_of_month(year: int, month: int, weekday: int) -> int:
    day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year, 12, 31)
    while day.weekday() != weekday:
        day -= timedelta(days=1)
    return day.day


def _nth_weekday_of_month(year: int, month: int, weekday: int, occurrence: int) -> int:
    day = datetime(year, month, 1)
    count = 0
    while day.month == month:
        if day.weekday() == weekday:
            count += 1
            if count == occurrence:
                return day.day
        day += timedelta(days=1)
    raise ValueError("weekday occurrence not found")


class _FallbackTimezone(tzinfo):
    def __init__(
        self,
        name: str,
        *,
        standard_offset_hours: int,
        dst_offset_hours: int | None = None,
        region: str = "fixed",
    ) -> None:
        self._name = name
        self._standard_offset = timedelta(hours=standard_offset_hours)
        self._dst_offset = (
            timedelta(hours=dst_offset_hours)
            if dst_offset_hours is not None
            else None
        )
        self._region = region

    def _is_dst(self, dt: datetime | None) -> bool:
        if dt is None or self._dst_offset is None:
            return False

        naive = dt.replace(tzinfo=None)
        year = naive.year

        if self._region == "eu":
            start_day = _last_weekday_of_month(year, 3, 6)
            end_day = _last_weekday_of_month(year, 10, 6)
            if self._name == "Europe/London":
                start = datetime(year, 3, start_day, 1, 0)
                end = datetime(year, 10, end_day, 2, 0)
            else:
                start = datetime(year, 3, start_day, 2, 0)
                end = datetime(year, 10, end_day, 3, 0)
            return start <= naive < end

        if self._region == "us":
            start_day = _nth_weekday_of_month(year, 3, 6, 2)
            end_day = _nth_weekday_of_month(year, 11, 6, 1)
            start = datetime(year, 3, start_day, 2, 0)
            end = datetime(year, 11, end_day, 2, 0)
            return start <= naive < end

        return False

    def utcoffset(self, dt: datetime | None) -> timedelta:
        if self._is_dst(dt):
            return self._dst_offset or self._standard_offset
        return self._standard_offset

    def dst(self, dt: datetime | None) -> timedelta:
        if self._is_dst(dt):
            return (self._dst_offset or self._standard_offset) - self._standard_offset
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return self._name


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

    def get_zoneinfo(self, timezone: str) -> ZoneInfo:
        self.validate_timezone(timezone)
        try:
            return ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            return self._fallback_timezone(timezone)

    def _fallback_timezone(self, timezone_name: str) -> tzinfo:
        fallbacks: dict[str, tzinfo] = {
            "UTC": _FallbackTimezone("UTC", standard_offset_hours=0),
            "Europe/Kyiv": _FallbackTimezone(
                "Europe/Kyiv",
                standard_offset_hours=2,
                dst_offset_hours=3,
                region="eu",
            ),
            "Europe/Kiev": _FallbackTimezone(
                "Europe/Kiev",
                standard_offset_hours=2,
                dst_offset_hours=3,
                region="eu",
            ),
            "Europe/Warsaw": _FallbackTimezone(
                "Europe/Warsaw",
                standard_offset_hours=1,
                dst_offset_hours=2,
                region="eu",
            ),
            "Europe/Berlin": _FallbackTimezone(
                "Europe/Berlin",
                standard_offset_hours=1,
                dst_offset_hours=2,
                region="eu",
            ),
            "Europe/London": _FallbackTimezone(
                "Europe/London",
                standard_offset_hours=0,
                dst_offset_hours=1,
                region="eu",
            ),
            "America/New_York": _FallbackTimezone(
                "America/New_York",
                standard_offset_hours=-5,
                dst_offset_hours=-4,
                region="us",
            ),
            "America/Chicago": _FallbackTimezone(
                "America/Chicago",
                standard_offset_hours=-6,
                dst_offset_hours=-5,
                region="us",
            ),
            "America/Denver": _FallbackTimezone(
                "America/Denver",
                standard_offset_hours=-7,
                dst_offset_hours=-6,
                region="us",
            ),
            "America/Los_Angeles": _FallbackTimezone(
                "America/Los_Angeles",
                standard_offset_hours=-8,
                dst_offset_hours=-7,
                region="us",
            ),
        }
        return fallbacks.get(timezone_name, _FallbackTimezone(timezone_name, standard_offset_hours=0))

    def localize_datetime(self, value: datetime, timezone: str) -> datetime:
        zoneinfo = self.get_zoneinfo(timezone)
        if value.tzinfo is None:
            return value.replace(tzinfo=zoneinfo)
        return value.astimezone(zoneinfo)

    def to_utc_datetime(self, value: datetime, timezone: str) -> datetime:
        zoneinfo = self.get_zoneinfo(timezone)
        localized = self.localize_datetime(value, timezone)
        offset = zoneinfo.utcoffset(localized) or timedelta(0)
        return (value - offset).replace(tzinfo=dt_timezone.utc)

    def to_utc_isoformat(self, value: datetime, timezone: str) -> str:
        return self.to_utc_datetime(value, timezone).isoformat()

    def format_local_isoformat(self, value: datetime, timezone: str) -> str:
        return self.localize_datetime(value, timezone).isoformat()
