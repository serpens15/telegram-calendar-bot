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
        self.preview_text = "preview text"
        self.cancel_result = True

    def preview_or_clarify(self, telegram_id, draft):
        self.preview_calls.append((telegram_id, draft))
        return self.preview_text

    def confirm_pending(self, telegram_id):
        self.confirm_calls.append(telegram_id)
        return self.next_confirm_event

    def cancel_pending(self, telegram_id):
        self.cancel_calls.append(telegram_id)
        return self.cancel_result


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

    types_module.Message = Message

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
                "handle_confirm",
                "handle_cancel",
                "handle_timezone",
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

        message.answer.assert_awaited_once_with("start response")

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
        self.assertIn("Access denied.", message.answer.await_args.args[0])

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
        self.assertIn("Event created.", message.answer.await_args.args[0])
        self.assertEqual(fake_confirmation.confirm_calls, [111])

    def test_cancel_handler_discards_event(self) -> None:
        fake_confirmation = _FakeEventConfirmation()

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

        message.answer.assert_awaited_once_with("Event draft cancelled.")
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

        message.answer.assert_awaited_once_with("Timezone updated to Europe/Berlin.")
        self.assertEqual(fake_timezone.set_calls, [(111, "Europe/Berlin")])


if __name__ == "__main__":
    unittest.main()
