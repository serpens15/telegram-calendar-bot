from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bot.messages import ADD_BUTTON, DELETE_BUTTON, LIST_BUTTON, help_text, start_text


class BotMessagesTest(unittest.TestCase):
    def test_start_text_mentions_start_button(self) -> None:
        text = start_text()

        self.assertIn("Ласкаво просимо", text)
        self.assertIn("Старт", text)

    def test_help_text_lists_main_menu_and_commands(self) -> None:
        text = help_text()

        self.assertIn(ADD_BUTTON, text)
        self.assertIn(LIST_BUTTON, text)
        self.assertIn(DELETE_BUTTON, text)
        self.assertIn("/start", text)
        self.assertIn("/help", text)
        self.assertIn("/whoami", text)
        self.assertIn("/timezone", text)
        self.assertIn("/cancel", text)


if __name__ == "__main__":
    unittest.main()
