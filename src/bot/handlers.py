"""Telegram message handlers."""

from __future__ import annotations

from .messages import help_text, start_text
from security.access_control import AccessControlService
from security.messages import access_denied_text


def build_router(access_control: AccessControlService | None = None):
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

    return router
