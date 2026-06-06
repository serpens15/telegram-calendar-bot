from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from db.models import EventRecord


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bot.messages import START_BUTTON
from bot.handlers import build_router


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


class _FakeAccessControl:
    def __init__(self, allowed_ids: set[int] | None = None):
        self.allowed_ids = allowed_ids or set()

    def is_allowed(self, telegram_id):
        return telegram_id in self.allowed_ids


class _FakeEventConfirmation:
    def __init__(self):
        self.preview_calls: list[tuple[int, object]] = []
        self.confirm_calls: list[int] = []
        self.cancel_calls: list[int] = []
        self.delete_request_calls: list[tuple[int, int]] = []
        self.delete_confirm_calls: list[int] = []
        self.pending_events: set[int] = set()
        self.pending_deletes: dict[int, int] = {}
        self.next_confirm_event = EventRecord(
            id=1,
            user_id=111,
            title="Team sync",
            event_at="2026-06-07T15:00:00+03:00",
            event_at_utc="2026-06-07T12:00:00+00:00",
            timezone="Europe/Kyiv",
            source_text="завтра о 15:00 зустріч",
            created_at="2026-06-06 10:00:00",
            updated_at="2026-06-06 10:00:00",
        )
        self.events_list_text = (
            "Найближчі події:\n1. Team sync | 2026-06-07T15:00:00+03:00 | Europe/Kyiv"
        )
        self.delete_preview_text = (
            "Видалити цю подію?\n\n"
            "ID: 1\n"
            "Назва: Team sync\n"
            "Коли: 2026-06-07T15:00:00+03:00\n"
            "Часовий пояс: Europe/Kyiv\n\n"
            "Надішліть /confirm, щоб видалити, або /cancel, щоб скасувати."
        )
        self.preview_text = "preview text"
        self.cancel_result = True

    def preview_or_clarify(self, telegram_id, draft):
        self.preview_calls.append((telegram_id, draft))
        self.pending_events.add(telegram_id)
        return self.preview_text

    def confirm_pending(self, telegram_id):
        self.confirm_calls.append(telegram_id)
        self.pending_events.discard(telegram_id)
        return self.next_confirm_event

    def cancel_pending(self, telegram_id):
        self.cancel_calls.append(telegram_id)
        self.pending_events.discard(telegram_id)
        self.pending_deletes.pop(telegram_id, None)
        return self.cancel_result

    def has_pending_event(self, telegram_id):
        return telegram_id in self.pending_events

    def has_pending_delete(self, telegram_id):
        return telegram_id in self.pending_deletes

    def build_events_list_text(self, telegram_id):
        return self.events_list_text

    def request_delete(self, telegram_id, event_id):
        self.delete_request_calls.append((telegram_id, event_id))
        self.pending_deletes[telegram_id] = event_id
        if event_id != self.next_confirm_event.id:
            return None
        return self.delete_preview_text

    def confirm_pending_delete(self, telegram_id):
        self.delete_confirm_calls.append(telegram_id)
        self.pending_deletes.pop(telegram_id, None)
        return self.next_confirm_event


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
        return types.SimpleNamespace(timezone=timezone)


def _install_fake_aiogram() -> dict[str, types.ModuleType]:
    aiogram = types.ModuleType("aiogram")
    aiogram.Router = _FakeRouter

    filters = types.ModuleType("aiogram.filters")

    class Command:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    filters.Command = Command

    types_module = types.ModuleType("aiogram.types")

    class Message:
        pass

    class KeyboardButton:
        def __init__(self, text):
            self.text = text

    class ReplyKeyboardMarkup:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    types_module.Message = Message
    types_module.KeyboardButton = KeyboardButton
    types_module.ReplyKeyboardMarkup = ReplyKeyboardMarkup

    return {
        "aiogram": aiogram,
        "aiogram.filters": filters,
        "aiogram.types": types_module,
    }


class BotHandlersTest(unittest.TestCase):
    def test_build_router_registers_start_and_help_handlers(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )

        handler_names = [handler.callback.__name__ for handler in router.message.handlers]

        self.assertEqual(
            handler_names,
            [
                "handle_start",
                "handle_help",
                "handle_whoami",
                "handle_list",
                "handle_confirm",
                "handle_cancel",
                "handle_timezone",
                "handle_delete",
                "handle_text",
            ],
        )

    def test_start_handler_answers_with_start_text(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )
            start_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_start"
            )
            message = AsyncMock()
            message.from_user.id = 111

            with patch("bot.handlers.start_text", return_value="start response"):
                asyncio.run(start_handler(message))

        message.answer.assert_awaited_once()
        self.assertEqual(message.answer.await_args.args[0], "start response")
        keyboard = message.answer.await_args.kwargs["reply_markup"].kwargs["keyboard"]
        self.assertEqual(keyboard[0][0].text, START_BUTTON)

    def test_help_handler_answers_with_help_text(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )
            help_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_help"
            )
            message = AsyncMock()
            message.from_user.id = 111

            with patch("bot.handlers.help_text", return_value="help response"):
                asyncio.run(help_handler(message))

        message.answer.assert_awaited_once_with("help response")

    def test_whoami_handler_shows_telegram_id(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )
            whoami_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_whoami"
            )
            message = AsyncMock()
            message.from_user.id = 111

            asyncio.run(whoami_handler(message))

        message.answer.assert_awaited_once_with("Ваш Telegram ID: 111.")

    def test_whoami_handler_works_for_unauthorized_user(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl(set()),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )
            whoami_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_whoami"
            )
            message = AsyncMock()
            message.from_user.id = 999

            asyncio.run(whoami_handler(message))

        message.answer.assert_awaited_once_with("Ваш Telegram ID: 999.")

    def test_start_button_returns_start_text(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )
            text_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_text"
            )
            message = AsyncMock()
            message.text = START_BUTTON
            message.from_user.id = 111

            asyncio.run(text_handler(message))

        message.answer.assert_awaited_once()
        self.assertIn("Бот Telegram Calendar Bot запущено.", message.answer.await_args.args[0])
        self.assertIn("reply_markup", message.answer.await_args.kwargs)

    def test_list_handler_shows_events(self) -> None:
        fake_confirmation = _FakeEventConfirmation()

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            list_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_list"
            )
            message = AsyncMock()
            message.from_user.id = 111

            asyncio.run(list_handler(message))

        message.answer.assert_awaited_once_with(fake_confirmation.events_list_text)

    def test_delete_handler_requests_confirmation(self) -> None:
        fake_confirmation = _FakeEventConfirmation()

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            delete_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_delete"
            )
            message = AsyncMock()
            message.text = "/delete 1"
            message.from_user.id = 111

            asyncio.run(delete_handler(message))

        message.answer.assert_awaited_once_with(fake_confirmation.delete_preview_text)
        self.assertEqual(fake_confirmation.delete_request_calls, [(111, 1)])

    def test_start_handler_denies_unauthorized_user(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl(set()),
                _FakeEventConfirmation(),
                _FakeTimezoneService(),
            )
            start_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_start"
            )
            message = AsyncMock()
            message.from_user.id = 999

            asyncio.run(start_handler(message))

        message.answer.assert_awaited_once()
        self.assertIn("Доступ заборонено.", message.answer.await_args.args[0])

    def test_text_handler_previews_event_draft(self) -> None:
        fake_confirmation = _FakeEventConfirmation()
        fake_confirmation.preview_text = "preview text"

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            text_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_text"
            )
            message = AsyncMock()
            message.text = "завтра о 15:00 зустріч"
            message.from_user.id = 111

            with patch("bot.handlers.parse_event_text") as parse_event_text:
                parse_event_text.return_value = object()
                asyncio.run(text_handler(message))

        message.answer.assert_awaited_once_with("preview text")
        self.assertEqual(fake_confirmation.preview_calls[0][0], 111)

    def test_confirm_handler_creates_event(self) -> None:
        fake_confirmation = _FakeEventConfirmation()

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            confirm_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_confirm"
            )
            message = AsyncMock()
            message.from_user.id = 111

            asyncio.run(confirm_handler(message))

        message.answer.assert_awaited_once()
        self.assertIn("Подію створено.", message.answer.await_args.args[0])
        self.assertEqual(fake_confirmation.confirm_calls, [111])

    def test_confirm_handler_deletes_event_when_delete_is_pending(self) -> None:
        fake_confirmation = _FakeEventConfirmation()
        fake_confirmation.pending_deletes[111] = 1

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            confirm_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_confirm"
            )
            message = AsyncMock()
            message.from_user.id = 111

            asyncio.run(confirm_handler(message))

        message.answer.assert_awaited_once()
        self.assertIn("Подію видалено.", message.answer.await_args.args[0])
        self.assertEqual(fake_confirmation.delete_confirm_calls, [111])

    def test_cancel_handler_discards_event(self) -> None:
        fake_confirmation = _FakeEventConfirmation()
        fake_confirmation.pending_events.add(111)

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            cancel_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_cancel"
            )
            message = AsyncMock()
            message.from_user.id = 111

            asyncio.run(cancel_handler(message))

        message.answer.assert_awaited_once_with("Чернетку події скасовано.")
        self.assertEqual(fake_confirmation.cancel_calls, [111])

    def test_cancel_handler_discards_delete_request(self) -> None:
        fake_confirmation = _FakeEventConfirmation()
        fake_confirmation.pending_deletes[111] = 1

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                fake_confirmation,
                _FakeTimezoneService(),
            )
            cancel_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_cancel"
            )
            message = AsyncMock()
            message.from_user.id = 111

            asyncio.run(cancel_handler(message))

        message.answer.assert_awaited_once_with("Запит на видалення скасовано.")
        self.assertEqual(fake_confirmation.cancel_calls, [111])

    def test_timezone_handler_shows_current_timezone(self) -> None:
        fake_timezone = _FakeTimezoneService("Europe/Warsaw")

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                fake_timezone,
            )
            timezone_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_timezone"
            )
            message = AsyncMock()
            message.text = "/timezone"
            message.from_user.id = 111

            asyncio.run(timezone_handler(message))

        message.answer.assert_awaited_once()
        self.assertIn("Europe/Warsaw", message.answer.await_args.args[0])

    def test_timezone_handler_updates_timezone(self) -> None:
        fake_timezone = _FakeTimezoneService("Europe/Kyiv")

        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router(
                _FakeAccessControl({111}),
                _FakeEventConfirmation(),
                fake_timezone,
            )
            timezone_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_timezone"
            )
            message = AsyncMock()
            message.text = "/timezone Europe/Berlin"
            message.from_user.id = 111

            asyncio.run(timezone_handler(message))

        message.answer.assert_awaited_once_with("Часовий пояс оновлено: Europe/Berlin.")
        self.assertEqual(fake_timezone.set_calls, [(111, "Europe/Berlin")])


if __name__ == "__main__":
    unittest.main()
