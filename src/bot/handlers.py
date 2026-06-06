"""Telegram message handlers."""

from __future__ import annotations

from datetime import date

from parsing import parse_event_text
from .messages import (
    ADD_BUTTON,
    CANCEL_BUTTON,
    CONFIRM_BUTTON,
    DELETE_BUTTON,
    HELP_BUTTON,
    LIST_BUTTON,
    START_BUTTON,
    TIMEZONE_BUTTON,
    WHOAMI_BUTTON,
    help_text,
    main_menu_keyboard,
    start_text,
)
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

    async def _send_start(message: Message) -> None:
        await message.answer(start_text(), reply_markup=main_menu_keyboard())

    async def _send_help(message: Message) -> None:
        await message.answer(help_text())

    async def _send_whoami(message: Message) -> None:
        telegram_id = getattr(message.from_user, "id", None)
        if telegram_id is None:
            await message.answer("Не вдалося визначити ваш Telegram ID.")
            return

        await message.answer(f"Ваш Telegram ID: {telegram_id}.")

    async def _send_list(message: Message) -> None:
        if event_confirmation is None:
            await message.answer("Список подій ще не налаштовано.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        await message.answer(event_confirmation.build_events_list_text(telegram_id))

    async def _send_confirm(message: Message) -> None:
        if event_confirmation is None:
            await message.answer("Поки немає чого підтверджувати.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        if event_confirmation.has_pending_delete(telegram_id):
            event = event_confirmation.confirm_pending_delete(telegram_id)
            if event is None:
                await message.answer("Поки немає чого підтверджувати.")
                return

            await message.answer(
                "Подію видалено.\n\n"
                f"Назва: {event.title}\n"
                f"Коли: {event.event_at}\n"
                f"Часовий пояс: {event.timezone}"
            )
            return

        event = event_confirmation.confirm_pending(telegram_id)
        if event is None:
            await message.answer("Поки немає чого підтверджувати.")
            return

        await message.answer(
            "Подію створено.\n\n"
            f"Назва: {event.title}\n"
            f"Коли: {event.event_at}\n"
            f"Часовий пояс: {event.timezone}"
        )

    async def _send_cancel(message: Message) -> None:
        if event_confirmation is None:
            await message.answer("Поки немає чого скасовувати.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        had_delete = event_confirmation.has_pending_delete(telegram_id)
        had_event = event_confirmation.has_pending_event(telegram_id)
        cancelled = event_confirmation.cancel_pending(telegram_id)
        if cancelled:
            if had_delete:
                await message.answer("Запит на видалення скасовано.")
            elif had_event:
                await message.answer("Чернетку події скасовано.")
            else:
                await message.answer("Поточну дію скасовано.")
        else:
            await message.answer("Поки немає чого скасовувати.")

    async def _send_timezone(message: Message) -> None:
        if timezone_service is None:
            await message.answer("Керування часовим поясом ще не налаштовано.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        text = getattr(message, "text", "") or ""
        parts = text.split(maxsplit=1)

        if len(parts) == 1 or text == TIMEZONE_BUTTON:
            current_timezone = timezone_service.get_user_timezone(telegram_id)
            await message.answer(
                "Ваш поточний часовий пояс: "
                f"{current_timezone}.\n\n"
                "Вкажіть /timezone <IANA timezone>, щоб змінити його."
            )
            return

        requested_timezone = parts[1].strip()
        if not requested_timezone:
            await message.answer(
                "Вкажіть часовий пояс, наприклад /timezone Europe/Kyiv."
            )
            return

        try:
            user = timezone_service.set_user_timezone(telegram_id, requested_timezone)
        except ValueError:
            await message.answer(
                "Невідомий часовий пояс.\n\n"
                "Вкажіть коректний IANA timezone, наприклад Europe/Kyiv."
            )
            return

        await message.answer(f"Часовий пояс оновлено: {user.timezone}.")

    async def _send_delete(message: Message) -> None:
        if event_confirmation is None:
            await message.answer("Видалення подій ще не налаштовано.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        text = getattr(message, "text", "") or ""
        parts = text.split(maxsplit=1)

        if len(parts) == 1 or text == DELETE_BUTTON:
            list_text = event_confirmation.build_events_list_text(telegram_id)
            if list_text == "У вас немає найближчих подій.":
                list_text += "\n\nВкажіть /delete <id>, щоб видалити подію."
            await message.answer(list_text)
            return

        event_id_text = parts[1].strip()
        try:
            event_id = int(event_id_text)
        except ValueError:
            await message.answer("Вкажіть коректний ID події, наприклад /delete 1.")
            return

        preview_text = event_confirmation.request_delete(telegram_id, event_id)
        if preview_text is None:
            await message.answer("Подію не знайдено.")
            return

        await message.answer(preview_text)

    async def _send_add_prompt(message: Message) -> None:
        await message.answer(
            "Надішліть текст події, наприклад: завтра о 15:00 зустріч."
        )

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_start(message)

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_help(message)

    @router.message(Command("whoami"))
    async def handle_whoami(message: Message) -> None:
        await _send_whoami(message)

    @router.message(Command("list"))
    async def handle_list(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_list(message)

    @router.message(Command("confirm"))
    async def handle_confirm(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_confirm(message)

    @router.message(Command("cancel"))
    async def handle_cancel(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_cancel(message)

    @router.message(Command("timezone"))
    async def handle_timezone(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_timezone(message)

    @router.message(Command("delete"))
    async def handle_delete(message: Message) -> None:
        if await _deny_if_needed(message):
            return
        await _send_delete(message)

    @router.message()
    async def handle_text(message: Message) -> None:
        if await _deny_if_needed(message):
            return

        text = getattr(message, "text", None) or ""
        if not text.strip() or text.startswith("/"):
            return

        if text == START_BUTTON:
            await _send_start(message)
            return

        if text == ADD_BUTTON:
            await _send_add_prompt(message)
            return

        if text == HELP_BUTTON:
            await _send_help(message)
            return

        if text == WHOAMI_BUTTON:
            await _send_whoami(message)
            return

        if text == LIST_BUTTON:
            await _send_list(message)
            return

        if text == DELETE_BUTTON:
            await _send_delete(message)
            return

        if text == TIMEZONE_BUTTON:
            await _send_timezone(message)
            return

        if text == CONFIRM_BUTTON:
            await _send_confirm(message)
            return

        if text == CANCEL_BUTTON:
            await _send_cancel(message)
            return

        if event_confirmation is None:
            await message.answer("Обробку подій ще не налаштовано.")
            return

        telegram_id = getattr(message.from_user, "id", None)
        if event_confirmation.has_pending_delete(telegram_id):
            await message.answer(
                "У вас є запит на видалення. Використайте Підтвердити або Скасувати."
            )
            return

        draft = parse_event_text(text, reference_date=date.today())
        preview_text = event_confirmation.preview_or_clarify(telegram_id, draft)
        await message.answer(preview_text)

    return router
