from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bot.messages import (
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
    start_text,
)


class BotMessagesTest(unittest.TestCase):
    def test_start_text_mentions_bot_is_running(self) -> None:
        text = start_text()

        self.assertIn("Бот Telegram Calendar Bot запущено.", text)

    def test_help_text_lists_buttons(self) -> None:
        text = help_text()

        self.assertIn(START_BUTTON, text)
        self.assertIn(ADD_BUTTON, text)
        self.assertIn(HELP_BUTTON, text)
        self.assertIn(WHOAMI_BUTTON, text)
        self.assertIn(LIST_BUTTON, text)
        self.assertIn(DELETE_BUTTON, text)
        self.assertIn(TIMEZONE_BUTTON, text)
        self.assertIn(CONFIRM_BUTTON, text)
        self.assertIn(CANCEL_BUTTON, text)


if __name__ == "__main__":
    unittest.main()
