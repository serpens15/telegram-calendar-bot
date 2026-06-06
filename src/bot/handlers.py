"""Telegram message handlers."""

from __future__ import annotations

from datetime import date

from parsing import parse_event_text
from .messages import help_text, start_text
from security.access_control import AccessControlService
from security.messages import access_denied_text
from services.event_confirmation import EventConfirmationService
from services.timezone_service import TimezoneService


def build_router(
    access_control: AccessControlService | None = None,
    event_confirmation: EventConfirmationService | None = None,
    timezone_service: TimezoneService | None = None,
):
    from aiogram import Router
    from aiogram.filters import Command
    from aiogram.types import Message

    router = Router()

    def _is_allowed(message: Message) -> bool:
        if access_control is None:
            return True

        telegram_id = getattr(message.from_user, "id", None)
        return access_control.is_allowed(telegram_id)

    async def _deny_if_needed(message: Message) -> bool:
        if _is_allowed(message):
            return False

        await message.answer(access_denied_text())
        return True

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await message.answer(start_text())

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await message.answer(help_text())

    @router.message(Command("confirm"))
    async def handle_confirm(message: Message) -> None:
        if await _deny_if_needed(message):
            return

        if event_confirmation is None:
            await message.answer("Nothing to confirm yet.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        event = event_confirmation.confirm_pending(telegram_id)
        if event is None:
            await message.answer("Nothing to confirm yet.")
            return

        await message.answer(
            "Event created.\n\n"
            f"Title: {event.title}\n"
            f"When: {event.event_at}\n"
            f"Timezone: {event.timezone}"
        )

    @router.message(Command("cancel"))
    async def handle_cancel(message: Message) -> None:
        if await _deny_if_needed(message):
            return

        if event_confirmation is None:
            await message.answer("Nothing to cancel.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        cancelled = event_confirmation.cancel_pending(telegram_id)
        if cancelled:
            await message.answer("Event draft cancelled.")
        else:
            await message.answer("Nothing to cancel.")

    @router.message(Command("timezone"))
    async def handle_timezone(message: Message) -> None:
        if await _deny_if_needed(message):
            return

        if timezone_service is None:
            await message.answer("Timezone management is not configured yet.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        text = getattr(message, "text", "") or ""
        parts = text.split(maxsplit=1)

        if len(parts) == 1:
            current_timezone = timezone_service.get_user_timezone(telegram_id)
            await message.answer(
                "Your current timezone is "
                f"{current_timezone}.\n\n"
                "Use /timezone <IANA timezone> to change it."
            )
            return

        requested_timezone = parts[1].strip()
        if not requested_timezone:
            await message.answer(
                "Please provide a timezone, for example /timezone Europe/Kyiv."
            )
            return

        try:
            user = timezone_service.set_user_timezone(telegram_id, requested_timezone)
        except ValueError:
            await message.answer(
                "Unknown timezone.\n\n"
                "Use a valid IANA timezone, for example Europe/Kyiv."
            )
            return

        await message.answer(f"Timezone updated to {user.timezone}.")

    @router.message()
    async def handle_text(message: Message) -> None:
        if await _deny_if_needed(message):
            return

        text = getattr(message, "text", None) or ""
        if not text.strip() or text.startswith("/"):
            return

        if event_confirmation is None:
            await message.answer("Event processing is not configured yet.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        draft = parse_event_text(text, reference_date=date.today())
        preview_text = event_confirmation.preview_or_clarify(telegram_id, draft)
        await message.answer(preview_text)

    return router
