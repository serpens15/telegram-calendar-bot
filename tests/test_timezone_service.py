from __future__ import annotations

import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository
from services.timezone_service import TimezoneService


class TimezoneServiceTest(unittest.TestCase):
    def test_set_user_timezone_persists_value(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repository.initialize()
            service = TimezoneService(repository=repository, default_timezone="Europe/Kyiv")

            user = service.set_user_timezone(123, "Europe/Berlin")
            stored = repository.get_user_by_telegram_id(123)

        self.assertEqual(user.timezone, "Europe/Berlin")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.timezone, "Europe/Berlin")

    def test_get_user_timezone_returns_default_for_new_user(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repository.initialize()
            service = TimezoneService(repository=repository, default_timezone="Europe/Kyiv")

            timezone = service.get_user_timezone(456)

        self.assertEqual(timezone, "Europe/Kyiv")

    def test_validate_timezone_rejects_invalid_name(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repository.initialize()
            service = TimezoneService(repository=repository, default_timezone="Europe/Kyiv")

            with self.assertRaises(ValueError):
                service.validate_timezone("Invalid/Zone")


if __name__ == "__main__":
    unittest.main()
