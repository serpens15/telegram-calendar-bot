"""Runtime settings loaded from environment variables and local .env."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


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


def _load_dotenv_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def load_settings() -> BotSettings:
    project_root_env = Path.cwd() / ".env"
    module_root_env = Path(__file__).resolve().parents[2] / ".env"

    _load_dotenv_file(project_root_env)
    if module_root_env != project_root_env:
        _load_dotenv_file(module_root_env)

    return BotSettings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        app_env=os.getenv("APP_ENV", "development").strip(),
        log_level=os.getenv("LOG_LEVEL", "info").strip(),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Europe/Kyiv").strip(),
        allowed_telegram_ids=_parse_allowed_ids(os.getenv("ALLOWED_TELEGRAM_IDS", "")),
    )
