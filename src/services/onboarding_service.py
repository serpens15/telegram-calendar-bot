"""Onboarding flow for first bot launch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db.models import UserRecord
from db.repository import SQLiteRepository
from services.timezone_service import TimezoneService


_LANGUAGE_TO_TIMEZONE: dict[str, str] = {
    "uk": "Europe/Kyiv",
    "ru": "Europe/Kyiv",
    "be": "Europe/Kyiv",
    "pl": "Europe/Warsaw",
    "de": "Europe/Berlin",
    "en-gb": "Europe/London",
    "en-us": "America/New_York",
}


@dataclass(frozen=True, slots=True)
class OnboardingResult:
    user: UserRecord
    timezone: str
    needs_timezone_selection: bool
    is_new_user: bool
    was_auto_detected: bool


@dataclass(slots=True)
class OnboardingService:
    repository: SQLiteRepository
    timezone_service: TimezoneService
    default_timezone: str

    def _get_attr(self, telegram_user: Any, name: str) -> str | int | None:
        return getattr(telegram_user, name, None)

    def detect_timezone(self, telegram_user: Any) -> str | None:
        language_code = self._get_attr(telegram_user, "language_code")
        if not isinstance(language_code, str):
            return None

        normalized = language_code.strip().lower()
        if not normalized:
            return None

        if normalized in _LANGUAGE_TO_TIMEZONE:
            return _LANGUAGE_TO_TIMEZONE[normalized]

        if normalized.startswith(("uk", "ru", "be")):
            return "Europe/Kyiv"

        if normalized.startswith("en-"):
            return "Europe/London"

        return None

    def start(self, telegram_user: Any) -> OnboardingResult:
        telegram_id = self._get_attr(telegram_user, "id")
        if not isinstance(telegram_id, int):
            raise ValueError("Telegram user id is required")

        self.repository.allow_user(telegram_id)

        username = self._get_attr(telegram_user, "username")
        first_name = self._get_attr(telegram_user, "first_name")
        last_name = self._get_attr(telegram_user, "last_name")
        detected_timezone = self.detect_timezone(telegram_user)

        existing_user = self.repository.get_user_by_telegram_id(telegram_id)
        if existing_user is None:
            user = self.repository.upsert_user_profile(
                telegram_id,
                username=username if isinstance(username, str) else None,
                first_name=first_name if isinstance(first_name, str) else None,
                last_name=last_name if isinstance(last_name, str) else None,
                timezone_name=detected_timezone or self.default_timezone,
            )
            if detected_timezone is None:
                return OnboardingResult(
                    user=user,
                    timezone=user.timezone,
                    needs_timezone_selection=True,
                    is_new_user=True,
                    was_auto_detected=False,
                )

            user = self.repository.update_user_timezone(telegram_id, detected_timezone)
            return OnboardingResult(
                user=user,
                timezone=user.timezone,
                needs_timezone_selection=False,
                is_new_user=True,
                was_auto_detected=True,
            )

        user = existing_user
        if detected_timezone and detected_timezone != existing_user.timezone:
            user = self.repository.update_user_timezone(telegram_id, detected_timezone)

        return OnboardingResult(
            user=user,
            timezone=user.timezone,
            needs_timezone_selection=False,
            is_new_user=False,
            was_auto_detected=detected_timezone is not None,
        )

    def set_timezone(self, telegram_id: int, timezone: str) -> UserRecord:
        self.timezone_service.validate_timezone(timezone)
        self.repository.allow_user(telegram_id)
        self.repository.upsert_user_profile(telegram_id, timezone_name=self.default_timezone)
        return self.repository.update_user_timezone(telegram_id, timezone)
