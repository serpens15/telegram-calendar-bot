from __future__ import annotations

import asyncio
from dataclasses import dataclass
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from db.models import EventRecord
from db.repository import SQLiteRepository
from services.event_service import EventService
from services.timezone_service import TimezoneService


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bot.keyboards import (
    EVENT_CREATE_CONFIRM_CALLBACK,
    EVENT_DELETE_CONFIRM_CALLBACK_PREFIX,
    START_BUTTON,
)
from bot.handlers import build_router
from bot.messages import ADD_BUTTON, DELETE_BUTTON, LIST_BUTTON
from bot.states import EventCreationStates, OnboardingStates


class _FakeHandler:
    def __init__(self, callback):
        self.callback = callback


class _FakeObserver:
    def __init__(self):
        self.handlers = []

    def __call__(self, *filters):
        def decorator(callback):
            self.handlers.append(_FakeHandler(callback))
            return callback

        return decorator


class _FakeRouter:
    def __init__(self):
        self.message = _FakeObserver()
        self.callback_query = _FakeObserver()


class _FakeAccessControl:
    def __init__(self, allowed_ids: set[int] | None = None):
        self.allowed_ids = allowed_ids or set()

    def is_allowed(self, telegram_id):
        return telegram_id in self.allowed_ids


class _FakeState:
    def __init__(self, initial_state: str | None = None):
        self.state = initial_state
        self.data: dict[str, object] = {}
        self.set_state_calls: list[object] = []
        self.cleared = False

    async def set_state(self, state):
        self.set_state_calls.append(state)
        self.state = getattr(state, "state", state)

    async def get_state(self):
        return self.state

    async def clear(self):
        self.cleared = True
        self.state = None
        self.data.clear()

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)


@dataclass
class _OnboardingResult:
    user: SimpleNamespace
    timezone: str
    needs_timezone_selection: bool
    is_new_user: bool


class _FakeOnboardingService:
    def __init__(self, result: _OnboardingResult):
        self.result = result
        self.start_calls: list[object] = []
        self.set_timezone_calls: list[tuple[int, str]] = []

    def start(self, telegram_user):
        self.start_calls.append(telegram_user)
        return self.result

    def set_timezone(self, telegram_id, timezone):
        self.set_timezone_calls.append((telegram_id, timezone))
        return SimpleNamespace(telegram_id=telegram_id, timezone=timezone)


class _FakeEventService:
    def __init__(self):
        self.future_text = "Майбутні події"
        self.created_events: list[tuple[int, str, str, str]] = []
        self.deleted_events: list[tuple[int, int]] = []
        self.events_for_delete = [
            EventRecord(
                id=1,
                user_id=111,
                title="Зустріч",
                event_at="2026-06-15T18:00:00+03:00",
                event_at_utc="2026-06-15T15:00:00+00:00",
                timezone="Europe/Kyiv",
                source_text=None,
                created_at="2026-06-01 10:00:00",
                updated_at="2026-06-01 10:00:00",
            )
        ]
        self.repository = SimpleNamespace(
            get_event_for_user=self._get_event_for_user,
        )

    def _get_event_for_user(self, telegram_id, event_id):
        for event in self.events_for_delete:
            if event.id == event_id:
                return event
        return None

    def parse_date(self, raw_value):
        return __import__("datetime").date(2026, 6, 15)

    def parse_time(self, raw_value):
        return __import__("datetime").time(18, 0)

    def build_preview_text(self, *, title, event_date, event_time, timezone):
        return (
            f"Подія:\n{title}\n\n"
            f"Дата: {event_date.strftime('%d.%m.%Y')}\n"
            f"Час: {event_time.strftime('%H:%M')}\n"
            f"Часовий пояс: {timezone}\n\n"
            "Створити подію?"
        )

    def build_created_text(self, event):
        return f"✅ Подію створено.\n\nПодія: {event.title}"

    def build_future_events_text(self, telegram_id):
        return self.future_text

    def get_events_for_deletion(self, telegram_id):
        return list(self.events_for_delete)

    def format_event_local_text(self, event_at):
        return "15.06.2026 18:00"

    def create_event(self, telegram_id, *, title, event_date, event_time):
        self.created_events.append((telegram_id, title, event_date.isoformat(), event_time.isoformat()))
        return EventRecord(
            id=99,
            user_id=telegram_id,
            title=title,
            event_at="2026-06-15T18:00:00+03:00",
            event_at_utc="2026-06-15T15:00:00+00:00",
            timezone="Europe/Kyiv",
            source_text=None,
            created_at="2026-06-01 10:00:00",
            updated_at="2026-06-01 10:00:00",
        )

    def delete_event(self, telegram_id, event_id):
        self.deleted_events.append((telegram_id, event_id))
        if event_id != 1:
            return None
        return self.events_for_delete[0]


class _FakeTimezoneService:
    def __init__(self, current_timezone: str = "Europe/Kyiv"):
        self.current_timezone = current_timezone
        self.set_calls: list[tuple[int, str]] = []

    def get_user_timezone(self, telegram_id):
        return self.current_timezone

    def set_user_timezone(self, telegram_id, timezone):
        self.set_calls.append((telegram_id, timezone))
        if timezone == "Invalid/Zone":
            raise ValueError("Unknown timezone")
        self.current_timezone = timezone
        return SimpleNamespace(timezone=timezone)


class _FakeReminderScheduler:
    def __init__(self):
        self.scheduled_event_ids: list[int] = []

    def schedule_event_reminders(self, event_id: int) -> None:
        self.scheduled_event_ids.append(event_id)


def _install_fake_aiogram() -> dict[str, ModuleType]:
    aiogram = ModuleType("aiogram")

    class Router:
        def __init__(self):
            self.message = _FakeObserver()
            self.callback_query = _FakeObserver()

    aiogram.Router = Router

    class Message:
        pass

    class CallbackQuery:
        pass

    class KeyboardButton:
        def __init__(self, text):
            self.text = text

    class InlineKeyboardButton:
        def __init__(self, text, callback_data):
            self.text = text
            self.callback_data = callback_data

    class ReplyKeyboardMarkup:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class InlineKeyboardMarkup:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    aiogram_types = ModuleType("aiogram.types")
    aiogram_types.Message = Message
    aiogram_types.CallbackQuery = CallbackQuery
    aiogram_types.KeyboardButton = KeyboardButton
    aiogram_types.InlineKeyboardButton = InlineKeyboardButton
    aiogram_types.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    aiogram_types.InlineKeyboardMarkup = InlineKeyboardMarkup

    aiogram_filters = ModuleType("aiogram.filters")
    aiogram_fsm = ModuleType("aiogram.fsm")
    aiogram_fsm_context = ModuleType("aiogram.fsm.context")
    aiogram_fsm_context.FSMContext = object

    aiogram.types = aiogram_types
    aiogram.filters = aiogram_filters
    aiogram.fsm = aiogram_fsm
    aiogram_fsm.context = aiogram_fsm_context

    return {
        "aiogram": aiogram,
        "aiogram.filters": aiogram_filters,
        "aiogram.types": aiogram_types,
        "aiogram.fsm": aiogram_fsm,
        "aiogram.fsm.context": aiogram_fsm_context,
    }


class BotHandlersTest(unittest.TestCase):
    def test_build_router_registers_message_and_callback_handlers(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                None,
                _FakeTimezoneService(),
                _FakeOnboardingService(
                    _OnboardingResult(
                        user=SimpleNamespace(telegram_id=111),
                        timezone="Europe/Kyiv",
                        needs_timezone_selection=False,
                        is_new_user=True,
                    )
                ),
                _FakeEventService(),
            )

        self.assertEqual([handler.callback.__name__ for handler in router.message.handlers], ["handle_message"])
        self.assertEqual([handler.callback.__name__ for handler in router.callback_query.handlers], ["handle_callback"])

    def test_start_command_shows_start_screen(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(_FakeAccessControl({111}), None, _FakeTimezoneService(), None, _FakeEventService())
            handler = router.message.handlers[0].callback
            message = AsyncMock()
            message.text = "/start"
            message.from_user.id = 111
            state = _FakeState()

            asyncio.run(handler(message, state))

        message.answer.assert_awaited_once()
        keyboard = message.answer.await_args.kwargs["reply_markup"].kwargs["keyboard"]
        self.assertEqual(keyboard[0][0].text, START_BUTTON)

    def test_start_button_runs_onboarding_and_shows_main_menu(self) -> None:
        onboarding_service = _FakeOnboardingService(
            _OnboardingResult(
                user=SimpleNamespace(telegram_id=111),
                timezone="Europe/Kyiv",
                needs_timezone_selection=False,
                is_new_user=True,
            )
        )

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(_FakeAccessControl({111}), None, _FakeTimezoneService(), onboarding_service, _FakeEventService())
            handler = router.message.handlers[0].callback
            message = AsyncMock()
            message.text = START_BUTTON
            message.from_user.id = 111
            state = _FakeState()

            asyncio.run(handler(message, state))

        message.answer.assert_awaited_once()
        self.assertIn("Реєстрація завершена", message.answer.await_args.args[0])
        keyboard = message.answer.await_args.kwargs["reply_markup"].kwargs["keyboard"]
        self.assertEqual([row[0].text for row in keyboard], [ADD_BUTTON, LIST_BUTTON, DELETE_BUTTON])

    def test_start_button_prompts_timezone_selection_when_needed(self) -> None:
        onboarding_service = _FakeOnboardingService(
            _OnboardingResult(
                user=SimpleNamespace(telegram_id=111),
                timezone="Europe/Kyiv",
                needs_timezone_selection=True,
                is_new_user=True,
            )
        )

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(_FakeAccessControl({111}), None, _FakeTimezoneService(), onboarding_service, _FakeEventService())
            handler = router.message.handlers[0].callback
            message = AsyncMock()
            message.text = START_BUTTON
            message.from_user.id = 111
            state = _FakeState()

            asyncio.run(handler(message, state))

        self.assertEqual(state.state, OnboardingStates.choosing_timezone.state)
        keyboard = message.answer.await_args.kwargs["reply_markup"].kwargs["inline_keyboard"]
        self.assertTrue(any(button.callback_data == "timezone:Europe/Kyiv" for row in keyboard for button in row))

    def test_add_flow_creates_event_after_confirmation(self) -> None:
        event_service = _FakeEventService()
        reminder_scheduler = _FakeReminderScheduler()
        state = _FakeState()

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                None,
                _FakeTimezoneService(),
                None,
                event_service,
                reminder_scheduler,
            )
            handler = router.message.handlers[0].callback
            callback_handler = router.callback_query.handlers[0].callback

            message = AsyncMock()
            message.from_user.id = 111
            message.text = ADD_BUTTON
            asyncio.run(handler(message, state))

            self.assertEqual(state.state, EventCreationStates.waiting_title.state)

            message.text = "Зустріч"
            asyncio.run(handler(message, state))
            self.assertEqual(state.state, EventCreationStates.waiting_date.state)

            message.text = "15.06.2026"
            asyncio.run(handler(message, state))
            self.assertEqual(state.state, EventCreationStates.waiting_time.state)

            message.text = "18:00"
            asyncio.run(handler(message, state))
            self.assertEqual(state.state, EventCreationStates.confirming.state)
            self.assertIn("Створити подію?", message.answer.await_args.args[0])

            callback = AsyncMock()
            callback.data = EVENT_CREATE_CONFIRM_CALLBACK
            callback.message = AsyncMock()
            callback.message.from_user.id = 999
            callback.from_user.id = 111
            asyncio.run(callback_handler(callback, state))

        self.assertEqual(event_service.created_events[0][0], 111)
        self.assertEqual(event_service.created_events[0][1], "Зустріч")
        self.assertEqual(reminder_scheduler.scheduled_event_ids, [99])
        self.assertTrue(state.cleared)
        self.assertIn("Подію створено", callback.message.answer.await_args.args[0])

    def test_list_and_delete_flow_uses_inline_confirmation(self) -> None:
        event_service = _FakeEventService()
        state = _FakeState()

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(_FakeAccessControl({111}), None, _FakeTimezoneService(), None, event_service)
            handler = router.message.handlers[0].callback
            callback_handler = router.callback_query.handlers[0].callback

            message = AsyncMock()
            message.from_user.id = 111
            message.text = LIST_BUTTON
            asyncio.run(handler(message, state))

            message.text = DELETE_BUTTON
            asyncio.run(handler(message, state))
            self.assertIn("Оберіть подію для видалення", message.answer.await_args.args[0])

            callback = AsyncMock()
            callback.data = "event:delete:1"
            callback.message = message
            callback.from_user.id = 111
            asyncio.run(callback_handler(callback, state))
            self.assertIn("Ви дійсно хочете видалити подію?", message.answer.await_args.args[0])

            callback.data = f"{EVENT_DELETE_CONFIRM_CALLBACK_PREFIX}1"
            asyncio.run(callback_handler(callback, state))

        self.assertEqual(event_service.deleted_events, [(111, 1)])
        self.assertIn("Подію видалено", message.answer.await_args.args[0])

    def test_timezone_callback_completes_onboarding(self) -> None:
        onboarding_service = _FakeOnboardingService(
            _OnboardingResult(
                user=SimpleNamespace(telegram_id=111),
                timezone="Europe/Kyiv",
                needs_timezone_selection=True,
                is_new_user=True,
            )
        )
        event_service = _FakeEventService()
        state = _FakeState(OnboardingStates.choosing_timezone.state)

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(_FakeAccessControl({111}), None, _FakeTimezoneService(), onboarding_service, event_service)
            callback_handler = router.callback_query.handlers[0].callback

            callback = AsyncMock()
            callback.data = "timezone:Europe/Berlin"
            callback.message = AsyncMock()
            callback.message.from_user.id = 111
            callback.from_user.id = 111

            asyncio.run(callback_handler(callback, state))

        self.assertEqual(onboarding_service.set_timezone_calls, [(111, "Europe/Berlin")])
        self.assertTrue(state.cleared)
        callback.message.answer.assert_awaited_once()

    def test_whoami_works_without_access_list(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(_FakeAccessControl(set()), None, _FakeTimezoneService(), None, _FakeEventService())
            handler = router.message.handlers[0].callback
            message = AsyncMock()
            message.from_user.id = 999
            message.text = "/whoami"
            state = _FakeState()

            asyncio.run(handler(message, state))

        message.answer.assert_awaited_once_with("Ваш Telegram ID: 999")


    def test_delete_buttons_reflect_database_events(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            timezone_service = TimezoneService(
                repository=repo,
                default_timezone="Europe/Kyiv",
            )
            event_service = EventService(
                repository=repo,
                timezone_service=timezone_service,
            )

            first_event = repo.create_event(
                111,
                title="Сонячна зустріч",
                event_at="2026-07-01T10:00:00+03:00",
                event_at_utc="2026-07-01T07:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            second_event = repo.create_event(
                111,
                title="Планування",
                event_at="2026-07-02T11:30:00+03:00",
                event_at_utc="2026-07-02T08:30:00+00:00",
                timezone="Europe/Kyiv",
            )

            with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
                router = build_router(
                    _FakeAccessControl({111}),
                    None,
                    timezone_service,
                    None,
                    event_service,
                )
                handler = router.message.handlers[0].callback

                message = AsyncMock()
                message.from_user.id = 111
                message.text = DELETE_BUTTON
                state = _FakeState()

                asyncio.run(handler(message, state))

            reply_markup = message.answer.await_args.kwargs["reply_markup"]
            keyboard = reply_markup.kwargs["inline_keyboard"]
            self.assertEqual(len(keyboard), 2)
            self.assertEqual(keyboard[0][0].text, f"Видалити: {first_event.title}")
            self.assertEqual(keyboard[0][0].callback_data, f"event:delete:{first_event.id}")
            self.assertEqual(keyboard[1][0].text, f"Видалити: {second_event.title}")
            self.assertEqual(keyboard[1][0].callback_data, f"event:delete:{second_event.id}")

    def test_list_and_delete_buttons_stay_in_sync_after_db_changes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            timezone_service = TimezoneService(
                repository=repo,
                default_timezone="Europe/Kyiv",
            )
            event_service = EventService(
                repository=repo,
                timezone_service=timezone_service,
            )

            first_event = repo.create_event(
                111,
                title="Зустріч з колегами",
                event_at="2026-07-01T10:00:00+03:00",
                event_at_utc="2026-07-01T07:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            second_event = repo.create_event(
                111,
                title="Візов",
                event_at="2026-07-02T11:30:00+03:00",
                event_at_utc="2026-07-02T08:30:00+00:00",
                timezone="Europe/Kyiv",
            )

            with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
                router = build_router(
                    _FakeAccessControl({111}),
                    None,
                    timezone_service,
                    None,
                    event_service,
                )
                handler = router.message.handlers[0].callback
                callback_handler = router.callback_query.handlers[0].callback
                state = _FakeState()

                list_message = AsyncMock()
                list_message.from_user.id = 111
                list_message.text = LIST_BUTTON
                asyncio.run(handler(list_message, state))
                self.assertIn(first_event.title, list_message.answer.await_args.args[0])
                self.assertIn(second_event.title, list_message.answer.await_args.args[0])

                delete_message = AsyncMock()
                delete_message.from_user.id = 111
                delete_message.text = DELETE_BUTTON
                asyncio.run(handler(delete_message, state))

                callback = AsyncMock()
                callback.data = f"event:delete:{first_event.id}"
                callback.message = delete_message
                callback.from_user.id = 111
                asyncio.run(callback_handler(callback, state))

                callback.data = f"{EVENT_DELETE_CONFIRM_CALLBACK_PREFIX}{first_event.id}"
                asyncio.run(callback_handler(callback, state))

                refreshed_list_message = AsyncMock()
                refreshed_list_message.from_user.id = 111
                refreshed_list_message.text = LIST_BUTTON
                asyncio.run(handler(refreshed_list_message, state))

            refreshed_text = refreshed_list_message.answer.await_args.args[0]
            self.assertNotIn(first_event.title, refreshed_text)
            self.assertIn(second_event.title, refreshed_text)
            self.assertEqual(repo.list_events_for_user(111), [second_event])


if __name__ == "__main__":
    unittest.main()
