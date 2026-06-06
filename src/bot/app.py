"""Bot entrypoint."""

from __future__ import annotations

import asyncio
import logging

from config.settings import load_settings
from db.repository import SQLiteRepository
from scheduler.reminder_scheduler import ReminderSchedulerService
from security.access_control import AccessControlService
from services.event_service import EventService
from services.event_confirmation import EventConfirmationService
from services.onboarding_service import OnboardingService
from services.timezone_service import TimezoneService

from .handlers import build_router


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def run_bot() -> None:
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage

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
    onboarding_service = OnboardingService(
        repository=repository,
        timezone_service=timezone_service,
        default_timezone=settings.default_timezone,
    )
    event_service = EventService(
        repository=repository,
        timezone_service=timezone_service,
        default_reminder_minutes=settings.default_reminder_minutes,
    )

    bot = Bot(token=settings.telegram_bot_token)
    reminder_scheduler = ReminderSchedulerService(
        repository=repository,
        timezone_service=timezone_service,
        bot=bot,
        default_reminder_minutes=settings.default_reminder_minutes,
    )
    event_confirmation = EventConfirmationService(
        repository=repository,
        timezone_service=timezone_service,
        default_timezone=settings.default_timezone,
        default_reminder_minutes=settings.default_reminder_minutes,
    )

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(
        build_router(
            access_control,
            event_confirmation,
            timezone_service,
            onboarding_service,
            event_service,
            reminder_scheduler,
        )
    )

    logging.getLogger(__name__).info(
        "Starting Telegram Calendar Bot in %s mode with timezone %s",
        settings.app_env,
        settings.default_timezone,
    )

    reminder_scheduler.start()
    try:
        await dispatcher.start_polling(bot)
    finally:
        reminder_scheduler.shutdown()
        await bot.session.close()


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
