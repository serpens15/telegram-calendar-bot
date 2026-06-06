"""Telegram message handlers."""

from __future__ import annotations

from .messages import help_text, start_text


def build_router():
    from aiogram import Router
    from aiogram.filters import Command
    from aiogram.types import Message

    router = Router()

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        await message.answer(start_text())

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(help_text())

    return router

