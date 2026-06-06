from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository
from services.onboarding_service import OnboardingService
from services.timezone_service import TimezoneService


class OnboardingServiceTest(unittest.TestCase):
    def test_start_auto_adds_user_and_detects_timezone(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = OnboardingService(
                repository=repo,
                timezone_service=TimezoneService(repository=repo, default_timezone="Europe/Kyiv"),
                default_timezone="Europe/Kyiv",
            )

            result = service.start(
                SimpleNamespace(
                    id=111,
                    username="alice",
                    first_name="Alice",
                    last_name="Smith",
                    language_code="uk",
                )
            )

            self.assertTrue(repo.is_user_allowed(111))
            self.assertFalse(result.needs_timezone_selection)
            self.assertEqual(result.timezone, "Europe/Kyiv")
            self.assertEqual(repo.get_user_by_telegram_id(111).timezone, "Europe/Kyiv")

    def test_start_requests_manual_timezone_when_auto_detection_is_unavailable(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = OnboardingService(
                repository=repo,
                timezone_service=TimezoneService(repository=repo, default_timezone="Europe/Kyiv"),
                default_timezone="Europe/Kyiv",
            )

            result = service.start(
                SimpleNamespace(
                    id=222,
                    username="bob",
                    first_name="Bob",
                    last_name="Brown",
                    language_code="zz",
                )
            )

            self.assertTrue(repo.is_user_allowed(222))
            self.assertTrue(result.needs_timezone_selection)
            self.assertEqual(result.timezone, "Europe/Kyiv")
            self.assertEqual(repo.get_user_by_telegram_id(222).timezone, "Europe/Kyiv")

    def test_set_timezone_updates_existing_user(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = OnboardingService(
                repository=repo,
                timezone_service=TimezoneService(repository=repo, default_timezone="Europe/Kyiv"),
                default_timezone="Europe/Kyiv",
            )
            repo.allow_user(333)
            repo.upsert_user_profile(333, username="carol", timezone_name="Europe/Kyiv")

            user = service.set_timezone(333, "Europe/Berlin")

            self.assertEqual(user.timezone, "Europe/Berlin")
            self.assertEqual(repo.get_user_by_telegram_id(333).timezone, "Europe/Berlin")


if __name__ == "__main__":
    unittest.main()
