from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config.settings import load_settings


class BotSettingsTest(unittest.TestCase):
    def test_load_settings_reads_environment_values(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "APP_ENV": "production",
            "LOG_LEVEL": "debug",
            "DEFAULT_TIMEZONE": "Europe/Warsaw",
            "ALLOWED_TELEGRAM_IDS": "10, 20, x, 30",
        }

        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.telegram_bot_token, "test-token")
        self.assertEqual(settings.app_env, "production")
        self.assertEqual(settings.log_level, "debug")
        self.assertEqual(settings.default_timezone, "Europe/Warsaw")
        self.assertEqual(settings.allowed_telegram_ids, (10, 20, 30))

    def test_load_settings_uses_defaults_when_values_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "config.settings._load_dotenv_file"
        ):
            settings = load_settings()

        self.assertEqual(settings.telegram_bot_token, "")
        self.assertEqual(settings.app_env, "development")
        self.assertEqual(settings.log_level, "info")
        self.assertEqual(settings.default_timezone, "Europe/Kyiv")
        self.assertEqual(settings.allowed_telegram_ids, ())

    def test_load_settings_reads_local_env_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "TELEGRAM_BOT_TOKEN=file-token",
                        "APP_ENV=staging",
                        "LOG_LEVEL=warning",
                        "DEFAULT_TIMEZONE=Europe/Berlin",
                        "ALLOWED_TELEGRAM_IDS=100, 200, bad, 300",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True), patch(
                "config.settings.Path.cwd", return_value=Path(temp_dir)
            ):
                settings = load_settings()

        self.assertEqual(settings.telegram_bot_token, "file-token")
        self.assertEqual(settings.app_env, "staging")
        self.assertEqual(settings.log_level, "warning")
        self.assertEqual(settings.default_timezone, "Europe/Berlin")
        self.assertEqual(settings.allowed_telegram_ids, (100, 200, 300))


if __name__ == "__main__":
    unittest.main()
