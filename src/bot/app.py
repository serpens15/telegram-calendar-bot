"""Bot entrypoint."""

from __future__ import annotations

import asyncio
import logging

from .handlers import build_router
from config.settings import load_settings
from db.repository import SQLiteRepository
from security.access_control import AccessControlService
from services.event_confirmation import EventConfirmationService
from services.timezone_service import TimezoneService


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def run_bot() -> None:
    from aiogram import Bot, Dispatcher

    settings = load_settings()
    _configure_logging(settings.log_level)

    repository = SQLiteRepository(settings.database_path)
    repository.initialize()

    access_control = AccessControlService(
        allowed_telegram_ids=settings.allowed_telegram_ids,
        repository=repository,
    )
    access_control.sync_allow_list()

    timezone_service = TimezoneService(
        repository=repository,
        default_timezone=settings.default_timezone,
    )
    event_confirmation = EventConfirmationService(
        repository=repository,
        timezone_service=timezone_service,
        default_timezone=settings.default_timezone,
    )

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(
        build_router(access_control, event_confirmation, timezone_service)
    )

    logging.getLogger(__name__).info(
        "Starting Telegram Calendar Bot in %s mode with timezone %s",
        settings.app_env,
        settings.default_timezone,
    )
    await dispatcher.start_polling(bot)


def main() -> int:
    settings = load_settings()

    if not settings.telegram_bot_token:
        print(
            "TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and fill the token."
        )
        return 1

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        return 0

    return 0
