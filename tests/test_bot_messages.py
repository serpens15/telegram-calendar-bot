from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bot.messages import help_text, start_text


class BotMessagesTest(unittest.TestCase):
    def test_start_text_mentions_bot_is_running(self) -> None:
        text = start_text()

        self.assertIn("Telegram Calendar Bot is running.", text)

    def test_help_text_lists_commands(self) -> None:
        text = help_text()

        self.assertIn("/start", text)
        self.assertIn("/help", text)
        self.assertIn("/confirm", text)
        self.assertIn("/cancel", text)


if __name__ == "__main__":
    unittest.main()
