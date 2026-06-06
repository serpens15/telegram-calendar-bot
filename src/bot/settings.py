"""Runtime settings loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class BotSettings:
    telegram_bot_token: str
    app_env: str
    log_level: str
    default_timezone: str
    allowed_telegram_ids: tuple[int, ...]


def _parse_allowed_ids(raw_value: str) -> tuple[int, ...]:
    ids: list[int] = []
    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return tuple(ids)


def load_settings() -> BotSettings:
    return BotSettings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        app_env=os.getenv("APP_ENV", "development").strip(),
        log_level=os.getenv("LOG_LEVEL", "info").strip(),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Europe/Kyiv").strip(),
        allowed_telegram_ids=_parse_allowed_ids(os.getenv("ALLOWED_TELEGRAM_IDS", "")),
    )

