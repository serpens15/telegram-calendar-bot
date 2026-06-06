from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch


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
            router = build_router()

        handler_names = [handler.callback.__name__ for handler in router.message.handlers]

        self.assertEqual(handler_names, ["handle_start", "handle_help"])

    def test_start_handler_answers_with_start_text(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router()
            start_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_start"
            )
            message = AsyncMock()

            with patch("bot.handlers.start_text", return_value="start response"):
                asyncio.run(start_handler(message))

        message.answer.assert_awaited_once_with("start response")

    def test_help_handler_answers_with_help_text(self) -> None:
        with patch.dict(sys.modules, _install_fake_aiogram(), clear=False):
            router = build_router()
            help_handler = next(
                handler.callback
                for handler in router.message.handlers
                if handler.callback.__name__ == "handle_help"
            )
            message = AsyncMock()

            with patch("bot.handlers.help_text", return_value="help response"):
                asyncio.run(help_handler(message))

        message.answer.assert_awaited_once_with("help response")


if __name__ == "__main__":
    unittest.main()
