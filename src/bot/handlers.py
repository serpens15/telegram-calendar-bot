"""Telegram message and callback handlers."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from parsing import ParserService, parse_event_text
from security.access_control import AccessControlService
from security.messages import access_denied_text
from services.event_confirmation import EventConfirmationService
from services.event_service import EventService
from services.onboarding_service import OnboardingService
from services.timezone_service import TimezoneService

from .keyboards import (
    EVENT_CREATE_CANCEL_CALLBACK,
    EVENT_CREATE_DATE_CALLBACK_PREFIX,
    EVENT_CREATE_EDIT_DATE_CALLBACK,
    EVENT_CREATE_EDIT_TIME_CALLBACK,
    EVENT_CREATE_CONFIRM_CALLBACK,
    EVENT_CREATE_RELATIVE_CALLBACK_PREFIX,
    EVENT_CREATE_TIME_CALLBACK_PREFIX,
    EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX,
    EVENT_CREATE_TIME_SLIDER_DONE_CALLBACK,
    EVENT_DELETE_CALLBACK_PREFIX,
    EVENT_DELETE_CANCEL_CALLBACK,
    EVENT_DELETE_CONFIRM_CALLBACK_PREFIX,
    DeleteEventKeyboardItem,
    START_BUTTON,
    delete_confirmation_keyboard,
    delete_events_keyboard,
    event_confirmation_keyboard,
    event_date_selection_keyboard,
    event_time_selection_keyboard,
    event_time_slider_keyboard,
    main_menu_keyboard,
    start_keyboard,
    timezone_selection_keyboard,
)
from .messages import (
    ADD_BUTTON,
    CANCEL_BUTTON,
    CONFIRM_BUTTON,
    DELETE_BUTTON,
    HELP_BUTTON,
    LIST_BUTTON,
    TIMEZONE_BUTTON,
    WHOAMI_BUTTON,
    help_text,
    registration_completed_text,
    start_text,
    timezone_selection_text,
)
from .states import EventCreationStates, OnboardingStates


def build_router(
    access_control: AccessControlService | None = None,
    event_confirmation: EventConfirmationService | None = None,
    timezone_service: TimezoneService | None = None,
    onboarding_service: OnboardingService | None = None,
    event_service: EventService | None = None,
    reminder_scheduler=None,
    parser_service: ParserService | None = None,
):
    from aiogram import Router
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    router = Router()

    def _telegram_id(message_or_query) -> int | None:
        return getattr(getattr(message_or_query, "from_user", None), "id", None)

    def _is_allowed(telegram_id: int | None) -> bool:
        if access_control is None:
            return True
        return access_control.is_allowed(telegram_id)

    def _is_public_text(text: str) -> bool:
        normalized = text.strip()
        return normalized in {
            "/start",
            START_BUTTON,
            "/help",
            HELP_BUTTON,
            "/whoami",
            WHOAMI_BUTTON,
        }

    async def _deny_if_needed(message: Message) -> bool:
        telegram_id = _telegram_id(message)
        text = getattr(message, "text", "") or ""
        if _is_allowed(telegram_id) or _is_public_text(text):
            return False

        await message.answer(access_denied_text(), reply_markup=start_keyboard())
        return True

    async def _show_start_screen(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(start_text(), reply_markup=start_keyboard())

    async def _run_onboarding(message: Message, state: FSMContext) -> None:
        if onboarding_service is None:
            await message.answer(start_text(), reply_markup=start_keyboard())
            return

        telegram_user = message.from_user
        result = onboarding_service.start(telegram_user)

        if result.needs_timezone_selection:
            await state.set_state(OnboardingStates.choosing_timezone)
            await message.answer(
                timezone_selection_text(),
                reply_markup=timezone_selection_keyboard(),
            )
            return

        await state.clear()
        text = registration_completed_text(result.user.telegram_id, result.timezone)
        await message.answer(text, reply_markup=main_menu_keyboard())

    async def _show_help(message: Message) -> None:
        await message.answer(help_text())

    async def _show_whoami(message: Message) -> None:
        telegram_id = _telegram_id(message)
        if telegram_id is None:
            await message.answer("Не вдалося визначити ваш Telegram ID.")
            return
        await message.answer(f"Ваш Telegram ID: {telegram_id}")

    async def _show_main_menu(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Головне меню:", reply_markup=main_menu_keyboard())

    async def _start_add_flow(message: Message, state: FSMContext) -> None:
        await state.set_state(EventCreationStates.waiting_title)
        await message.answer("Вкажіть назву події.")

    async def _show_event_creation_preview(
        message: Message,
        state: FSMContext,
        *,
        title: str,
        event_date: date,
        event_time: time,
        telegram_id: int | None = None,
    ) -> None:
        user_telegram_id = telegram_id if telegram_id is not None else _telegram_id(message)
        timezone = timezone_service.get_user_timezone(user_telegram_id) if timezone_service else "Europe/Kyiv"
        preview_text = (
            event_service.build_preview_text(
                title=title,
                event_date=event_date,
                event_time=event_time,
                timezone=timezone,
            )
            if event_service
            else "Підтвердіть подію."
        )
        await state.update_data(
            event_title=title,
            event_date=event_date.isoformat(),
            event_time=event_time.isoformat(),
        )
        await state.set_state(EventCreationStates.confirming)
        await message.answer(preview_text, reply_markup=event_confirmation_keyboard())

    async def _show_time_slider(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        event_time_raw = data.get("event_time")
        selected_time = time(12, 0)
        if isinstance(event_time_raw, str):
            try:
                selected_time = time.fromisoformat(event_time_raw)
            except ValueError:
                selected_time = time(12, 0)

        await state.update_data(
            slider_hour=selected_time.hour,
            slider_minute=selected_time.minute,
        )
        await message.answer(
            "Змініть час події:",
            reply_markup=event_time_slider_keyboard(
                selected_time.hour,
                selected_time.minute,
            ),
        )

    async def _handle_natural_language_event(message: Message, state: FSMContext) -> None:
        if event_service is None:
            await message.answer("Створення подій ще не налаштовано.")
            return

        text = getattr(message, "text", "") or ""
        service = parser_service or ParserService()
        draft = service.parse(text, reference_datetime=datetime.now().replace(microsecond=0))

        if draft.status != "complete" or draft.event_date is None or draft.event_time is None or not draft.title:
            if event_confirmation is not None:
                await message.answer(event_confirmation.build_clarification_text(draft))
            else:
                await message.answer("Не вдалося впевнено розпізнати подію. Спробуйте уточнити дату, час і назву.")
            return

        await _show_event_creation_preview(
            message,
            state,
            title=draft.title,
            event_date=draft.event_date,
            event_time=draft.event_time,
        )

    async def _show_future_events(message: Message) -> None:
        if event_service is None:
            await message.answer("Список подій ще не налаштовано.")
            return

        telegram_id = _telegram_id(message)
        await message.answer(event_service.build_future_events_text(telegram_id))

    async def _show_delete_menu(message: Message) -> None:
        if event_service is None:
            await message.answer("Видалення подій ще не налаштовано.")
            return

        telegram_id = _telegram_id(message)
        events = event_service.get_events_for_deletion(telegram_id)
        if not events:
            await message.answer("У вас поки немає подій.")
            return

        items = [
            DeleteEventKeyboardItem(
                event_id=event.id,
                title=event.title,
                event_at=event.event_at,
            )
            for event in events
        ]
        lines = ["Оберіть подію для видалення:"]
        for index, event in enumerate(events, start=1):
            lines.append(f"{index}. {event.title}")
            lines.append(event_service.format_event_local_text(event.event_at))
            lines.append("")

        await message.answer(
            "\n".join(lines).strip(),
            reply_markup=delete_events_keyboard(items),
        )

    async def _handle_timezone_command(message: Message, state: FSMContext) -> None:
        if timezone_service is None:
            await message.answer("Керування часовим поясом ще не налаштовано.")
            return

        telegram_id = _telegram_id(message)
        text = getattr(message, "text", "") or ""
        parts = text.split(maxsplit=1)

        if len(parts) == 1 or text == TIMEZONE_BUTTON or text == "/timezone":
            current_timezone = timezone_service.get_user_timezone(telegram_id)
            await message.answer(
                f"Ваш поточний часовий пояс: {current_timezone}.",
                reply_markup=main_menu_keyboard() if _is_allowed(telegram_id) else start_keyboard(),
            )
            return

        requested_timezone = parts[1].strip()
        try:
            if onboarding_service is not None:
                user = onboarding_service.set_timezone(telegram_id, requested_timezone)
            else:
                user = timezone_service.set_user_timezone(telegram_id, requested_timezone)
        except ValueError:
            await message.answer(
                "Невідомий часовий пояс. Виберіть коректний IANA timezone, наприклад Europe/Kyiv."
            )
            return

        await state.clear()
        await message.answer(
            registration_completed_text(telegram_id, user.timezone)
            if not _is_allowed(telegram_id)
            else f"Часовий пояс оновлено: {user.timezone}.",
            reply_markup=main_menu_keyboard(),
        )

    async def _cancel_current_action(message: Message, state: FSMContext) -> None:
        telegram_id = _telegram_id(message)
        state_data = await state.get_data()
        cancelled = False

        if event_confirmation is not None:
            cancelled = event_confirmation.cancel_pending(telegram_id)

        if await state.get_state() is not None:
            cancelled = True
            await state.clear()

        if cancelled:
            await message.answer("Поточну дію скасовано.", reply_markup=main_menu_keyboard())
        else:
            await message.answer("Наразі немає активної дії.", reply_markup=main_menu_keyboard())

    async def _confirm_legacy_pending(message: Message) -> None:
        if event_confirmation is None:
            await message.answer("Наразі немає чого підтверджувати.")
            return

        telegram_id = _telegram_id(message)
        if event_confirmation.has_pending_delete(telegram_id):
            event = event_confirmation.confirm_pending_delete(telegram_id)
            if event is None:
                await message.answer("Наразі немає чого підтверджувати.")
                return
            await message.answer(
                "Подію видалено.\n\n"
                f"Назва: {event.title}\n"
                f"Дата і час: {event.event_at}\n"
                f"Часовий пояс: {event.timezone}",
                reply_markup=main_menu_keyboard(),
            )
            return

        event = event_confirmation.confirm_pending(telegram_id)
        if event is None:
            await message.answer("Наразі немає чого підтверджувати.")
            return

        await message.answer(
            "Подію створено.\n\n"
            f"Назва: {event.title}\n"
            f"Дата і час: {event.event_at}\n"
            f"Часовий пояс: {event.timezone}",
            reply_markup=main_menu_keyboard(),
        )

    async def _handle_delete_command(message: Message) -> None:
        if event_service is None:
            await message.answer("Видалення подій ще не налаштовано.")
            return

        telegram_id = _telegram_id(message)
        text = getattr(message, "text", "") or ""
        parts = text.split(maxsplit=1)

        if len(parts) == 1 or text == DELETE_BUTTON:
            await _show_delete_menu(message)
            return

        try:
            event_id = int(parts[1].strip())
        except ValueError:
            await message.answer("Вкажіть коректний ID події, наприклад /delete 1.")
            return

        event = event_service.repository.get_event_for_user(telegram_id, event_id)
        if event is None:
            await message.answer("Подію не знайдено.")
            return

        await message.answer(
            "Ви дійсно хочете видалити подію?\n\n"
            f"Назва: {event.title}\n"
            f"Дата і час: {event.event_at}\n"
            f"Часовий пояс: {event.timezone}",
            reply_markup=delete_confirmation_keyboard(event.id),
        )

    async def _handle_add_state(message: Message, state: FSMContext) -> bool:
        current_state = await state.get_state()
        if current_state == EventCreationStates.waiting_title.state:
            title = getattr(message, "text", "").strip()
            if not title:
                await message.answer("Вкажіть назву події.")
                return True

            await state.update_data(event_title=title)
            await state.set_state(EventCreationStates.waiting_date)
            await message.answer(
                "Вкажіть дату події або оберіть швидкий варіант.",
                reply_markup=event_date_selection_keyboard(),
            )
            return True

        if current_state == EventCreationStates.waiting_date.state:
            raw_date = getattr(message, "text", "").strip()
            relative_draft = (
                parse_event_text(raw_date)
                if "через" in raw_date.lower()
                else None
            )
            if relative_draft is not None and relative_draft.event_datetime is not None:
                data = await state.get_data()
                title = data.get("event_title")
                if not title:
                    await state.clear()
                    await message.answer("Не вдалося зібрати дані події. Почніть ще раз.")
                    return True

                await _show_event_creation_preview(
                    message,
                    state,
                    title=title,
                    event_date=relative_draft.event_datetime.date(),
                    event_time=relative_draft.event_datetime.time(),
                )
                return True

            try:
                event_date = event_service.parse_date(raw_date) if event_service else date.today()
            except ValueError:
                await message.answer("Не вдалося прочитати дату. Спробуйте ще раз.")
                return True

            data = await state.get_data()
            title = data.get("event_title")
            event_time_raw = data.get("event_time")
            await state.update_data(event_date=event_date.isoformat())
            if title and event_time_raw:
                try:
                    selected_time = time.fromisoformat(event_time_raw)
                except ValueError:
                    selected_time = time(12, 0)
                await _show_event_creation_preview(
                    message,
                    state,
                    title=title,
                    event_date=event_date,
                    event_time=selected_time,
                )
            else:
                await state.set_state(EventCreationStates.waiting_time)
                await message.answer(
                    "Вкажіть час події або оберіть швидкий варіант.",
                    reply_markup=event_time_selection_keyboard(),
                )
            return True

        if current_state == EventCreationStates.waiting_time.state:
            raw_time = getattr(message, "text", "").strip()
            try:
                event_time = event_service.parse_time(raw_time) if event_service else time(0, 0)
            except ValueError:
                await message.answer("Не вдалося прочитати час. Спробуйте ще раз.")
                return True

            data = await state.get_data()
            title = data.get("event_title")
            event_date_raw = data.get("event_date")
            if not title or not event_date_raw:
                await state.clear()
                await message.answer("Не вдалося зібрати дані події. Почніть ще раз.")
                return True

            event_date = date.fromisoformat(event_date_raw)
            await _show_event_creation_preview(
                message,
                state,
                title=title,
                event_date=event_date,
                event_time=event_time,
            )
            return True

        return False

    async def _complete_event_creation(
        message: Message,
        state: FSMContext,
        telegram_id: int | None,
    ) -> None:
        if event_service is None:
            await message.answer("Створення подій ще не налаштовано.")
            return

        if telegram_id is None:
            await message.answer("Не вдалося визначити ваш Telegram ID.")
            return

        data = await state.get_data()
        title = data.get("event_title")
        event_date_raw = data.get("event_date")
        event_time_raw = data.get("event_time")

        if not title or not event_date_raw or not event_time_raw:
            await state.clear()
            await message.answer("Не вдалося завершити створення події.")
            return

        event = event_service.create_event(
            telegram_id,
            title=title,
            event_date=date.fromisoformat(event_date_raw),
            event_time=time.fromisoformat(event_time_raw),
        )
        if reminder_scheduler is not None:
            reminder_scheduler.schedule_event_reminders(event.id)
        await state.clear()
        await message.answer(
            event_service.build_created_text(event),
            reply_markup=main_menu_keyboard(),
        )

    async def _cancel_event_creation(message: Message, state: FSMContext) -> None:
        await state.clear()
        if event_confirmation is not None:
            event_confirmation.cancel_pending(_telegram_id(message))
        await message.answer("Створення події скасовано.", reply_markup=main_menu_keyboard())

    async def _remove_callback_message(callback: CallbackQuery) -> None:
        message = getattr(callback, "message", None)
        if message is None:
            return

        delete = getattr(message, "delete", None)
        if delete is not None:
            try:
                await delete()
                return
            except Exception:
                pass

        edit_reply_markup = getattr(message, "edit_reply_markup", None)
        if edit_reply_markup is not None:
            try:
                await edit_reply_markup(reply_markup=None)
            except Exception:
                pass

    @router.message()
    async def handle_message(message: Message, state: FSMContext) -> None:
        text = getattr(message, "text", "") or ""
        if not text.strip():
            return

        current_state = await state.get_state()

        if text == "/start":
            await _show_start_screen(message, state)
            return

        if text == START_BUTTON:
            if await _deny_if_needed(message):
                return
            await _run_onboarding(message, state)
            return

        if text in {"/help", HELP_BUTTON}:
            await _show_help(message)
            return

        if text in {"/whoami", WHOAMI_BUTTON}:
            await _show_whoami(message)
            return

        if text in {"/cancel", CANCEL_BUTTON}:
            await _cancel_current_action(message, state)
            return

        if text in {"/confirm", CONFIRM_BUTTON}:
            if await _handle_add_state(message, state):
                return
            await _confirm_legacy_pending(message)
            return

        if text in {ADD_BUTTON}:
            if await _deny_if_needed(message):
                return
            await _start_add_flow(message, state)
            return

        if text in {LIST_BUTTON, "/list"}:
            if await _deny_if_needed(message):
                return
            await _show_future_events(message)
            return

        if text in {DELETE_BUTTON} or text.startswith("/delete"):
            if await _deny_if_needed(message):
                return
            await _handle_delete_command(message)
            return

        if text.startswith("/timezone") or text == TIMEZONE_BUTTON:
            if await _deny_if_needed(message):
                return
            await _handle_timezone_command(message, state)
            return

        if await _handle_add_state(message, state):
            return

        if current_state is not None:
            if current_state == OnboardingStates.choosing_timezone.state:
                await message.answer(
                    "Оберіть часовий пояс кнопкою нижче.",
                    reply_markup=timezone_selection_keyboard(),
                )
                return

            if current_state == EventCreationStates.confirming.state:
                await message.answer(
                    "Використайте кнопки підтвердження або скасування під повідомленням.",
                    reply_markup=event_confirmation_keyboard(),
                )
                return

            return

        if not await _deny_if_needed(message):
            await _handle_natural_language_event(message, state)

    @router.callback_query()
    async def handle_callback(callback: CallbackQuery, state: FSMContext) -> None:
        data = getattr(callback, "data", "") or ""
        telegram_id = _telegram_id(callback)

        if data.startswith("timezone:") and await state.get_state() == OnboardingStates.choosing_timezone.state:
            timezone_name = data.removeprefix("timezone:")
            if onboarding_service is None:
                await callback.answer()
                return

            user = onboarding_service.set_timezone(telegram_id, timezone_name)
            await state.clear()
            await callback.message.answer(
                registration_completed_text(telegram_id, user.timezone),
                reply_markup=main_menu_keyboard(),
            )
            await callback.answer()
            return

        if data == EVENT_CREATE_CONFIRM_CALLBACK:
            await _remove_callback_message(callback)
            await _complete_event_creation(callback.message, state, telegram_id)
            await callback.answer()
            return

        if data == EVENT_CREATE_CANCEL_CALLBACK:
            await _remove_callback_message(callback)
            await _cancel_event_creation(callback.message, state)
            await callback.answer()
            return

        if data == EVENT_CREATE_EDIT_DATE_CALLBACK:
            if await state.get_state() != EventCreationStates.confirming.state:
                await callback.answer()
                return
            await state.set_state(EventCreationStates.waiting_date)
            await callback.message.answer(
                "Оберіть нову дату або введіть вручну.",
                reply_markup=event_date_selection_keyboard(),
            )
            await callback.answer()
            return

        if data == EVENT_CREATE_EDIT_TIME_CALLBACK:
            if await state.get_state() != EventCreationStates.confirming.state:
                await callback.answer()
                return
            await _show_time_slider(callback.message, state)
            await callback.answer()
            return

        if data.startswith(EVENT_CREATE_DATE_CALLBACK_PREFIX):
            if await state.get_state() not in {
                EventCreationStates.waiting_date.state,
                EventCreationStates.confirming.state,
            }:
                await callback.answer()
                return

            date_key = data.removeprefix(EVENT_CREATE_DATE_CALLBACK_PREFIX)
            today = date.today()
            date_offsets = {
                "today": 0,
                "tomorrow": 1,
                "after_tomorrow": 2,
            }
            if date_key not in date_offsets:
                await callback.answer("Некоректна дата.")
                return

            selected_date = today + timedelta(days=date_offsets[date_key])
            await state.update_data(event_date=selected_date.isoformat())
            state_data = await state.get_data()
            title = state_data.get("event_title")
            event_time_raw = state_data.get("event_time")
            if title and event_time_raw:
                try:
                    selected_time = time.fromisoformat(event_time_raw)
                except ValueError:
                    selected_time = time(12, 0)
                await _show_event_creation_preview(
                    callback.message,
                    state,
                    title=title,
                    event_date=selected_date,
                    event_time=selected_time,
                    telegram_id=telegram_id,
                )
            else:
                await state.set_state(EventCreationStates.waiting_time)
                await callback.message.answer(
                    "Оберіть час події або введіть вручну.",
                    reply_markup=event_time_selection_keyboard(),
                )
            await callback.answer()
            return

        if data.startswith(EVENT_CREATE_TIME_CALLBACK_PREFIX):
            if await state.get_state() != EventCreationStates.waiting_time.state:
                await callback.answer()
                return

            selected_time_raw = data.removeprefix(EVENT_CREATE_TIME_CALLBACK_PREFIX)
            state_data = await state.get_data()
            title = state_data.get("event_title")
            event_date_raw = state_data.get("event_date")
            if not title or not event_date_raw:
                await state.clear()
                await callback.message.answer("Не вдалося зібрати дані події. Почніть ще раз.")
                await callback.answer()
                return

            try:
                selected_time = time.fromisoformat(selected_time_raw)
                selected_date = date.fromisoformat(event_date_raw)
            except ValueError:
                await callback.answer("Некоректний час.")
                return

            await _show_event_creation_preview(
                callback.message,
                state,
                title=title,
                event_date=selected_date,
                event_time=selected_time,
                telegram_id=telegram_id,
            )
            await callback.answer()
            return

        if data.startswith(EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX):
            state_data = await state.get_data()
            try:
                part, delta_raw = data.removeprefix(
                    EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX
                ).split(":", 1)
                delta = int(delta_raw)
            except ValueError:
                await callback.answer("Некоректний час.")
                return

            hour = int(state_data.get("slider_hour", 12))
            minute = int(state_data.get("slider_minute", 0))
            if part == "hour":
                hour = (hour + delta) % 24
            elif part == "minute":
                minute = (minute + delta) % 60
            else:
                await callback.answer("Некоректний час.")
                return

            await state.update_data(slider_hour=hour, slider_minute=minute)
            await callback.message.edit_reply_markup(
                reply_markup=event_time_slider_keyboard(hour, minute),
            )
            await callback.answer()
            return

        if data == EVENT_CREATE_TIME_SLIDER_DONE_CALLBACK:
            state_data = await state.get_data()
            title = state_data.get("event_title")
            event_date_raw = state_data.get("event_date")
            hour = int(state_data.get("slider_hour", 12))
            minute = int(state_data.get("slider_minute", 0))
            if not title or not event_date_raw:
                await state.clear()
                await callback.message.answer("Не вдалося зібрати дані події. Почніть ще раз.")
                await callback.answer()
                return

            await _remove_callback_message(callback)
            await _show_event_creation_preview(
                callback.message,
                state,
                title=title,
                event_date=date.fromisoformat(event_date_raw),
                event_time=time(hour, minute),
                telegram_id=telegram_id,
            )
            await callback.answer()
            return

        if data.startswith(EVENT_CREATE_RELATIVE_CALLBACK_PREFIX):
            if await state.get_state() != EventCreationStates.waiting_date.state:
                await callback.answer()
                return

            state_data = await state.get_data()
            title = state_data.get("event_title")
            if not title:
                await state.clear()
                await callback.message.answer("Не вдалося зібрати дані події. Почніть ще раз.")
                await callback.answer()
                return

            try:
                minutes = int(data.removeprefix(EVENT_CREATE_RELATIVE_CALLBACK_PREFIX))
            except ValueError:
                await callback.answer("Некоректний час.")
                return

            selected_datetime = datetime.now().replace(microsecond=0) + timedelta(minutes=minutes)
            await _show_event_creation_preview(
                callback.message,
                state,
                title=title,
                event_date=selected_datetime.date(),
                event_time=selected_datetime.time(),
                telegram_id=telegram_id,
            )
            await callback.answer()
            return

        if data.startswith(EVENT_DELETE_CONFIRM_CALLBACK_PREFIX):
            if event_service is None:
                await callback.answer()
                return

            try:
                event_id = int(data.removeprefix(EVENT_DELETE_CONFIRM_CALLBACK_PREFIX))
            except ValueError:
                await callback.answer("Некоректний ID.")
                return

            deleted = event_service.delete_event(telegram_id, event_id)
            if deleted is None:
                await callback.message.answer("Подію не знайдено.")
                await callback.answer()
                return

            await _remove_callback_message(callback)
            await callback.message.answer(
                "✅ Подію видалено.\n\n"
                f"Подія: {deleted.title}\n"
                f"Дата і час: {deleted.event_at}\n"
                f"Часовий пояс: {deleted.timezone}",
                reply_markup=main_menu_keyboard(),
            )
            await callback.answer()
            return

        if data.startswith(EVENT_DELETE_CALLBACK_PREFIX):
            if event_service is None:
                await callback.answer()
                return

            try:
                event_id = int(data.removeprefix(EVENT_DELETE_CALLBACK_PREFIX))
            except ValueError:
                await callback.answer("Некоректний ID.")
                return

            event = event_service.repository.get_event_for_user(telegram_id, event_id)
            if event is None:
                await callback.message.answer("Подію не знайдено.")
                await callback.answer()
                return

            await callback.message.answer(
                "Ви дійсно хочете видалити подію?\n\n"
                f"Назва: {event.title}\n"
                f"Дата і час: {event.event_at}\n"
                f"Часовий пояс: {event.timezone}",
                reply_markup=delete_confirmation_keyboard(event.id),
            )
            await callback.answer()
            return

        if data == EVENT_DELETE_CANCEL_CALLBACK:
            await _remove_callback_message(callback)
            await callback.message.answer("Видалення скасовано.", reply_markup=main_menu_keyboard())
            await callback.answer()
            return

        await callback.answer()

    return router
