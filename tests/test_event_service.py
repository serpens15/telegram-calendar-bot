from __future__ import annotations

import sys
from datetime import date, time
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository
from services.event_service import EventService
from services.timezone_service import TimezoneService


class EventServiceTest(unittest.TestCase):
    def test_create_event_adds_default_and_event_time_reminders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            timezone_service = TimezoneService(
                repository=repo,
                default_timezone="Europe/Kyiv",
            )
            service = EventService(
                repository=repo,
                timezone_service=timezone_service,
                default_reminder_minutes=15,
            )

            event = service.create_event(
                111,
                title="Зустріч",
                event_date=date(2026, 6, 15),
                event_time=time(18, 0),
            )
            reminders = repo.list_reminders_for_event(event.id)

        self.assertEqual(len(reminders), 2)
        self.assertEqual(
            [reminder.reminder_at for reminder in reminders],
            [
                "2026-06-15T17:45:00+03:00",
                "2026-06-15T18:00:00+03:00",
            ],
        )

    def test_get_events_for_deletion_returns_only_future_events(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            timezone_service = TimezoneService(
                repository=repo,
                default_timezone="Europe/Kyiv",
            )
            service = EventService(
                repository=repo,
                timezone_service=timezone_service,
            )

            past_event = repo.create_event(
                111,
                title="Минуле",
                event_at="2025-06-15T18:00:00+03:00",
                event_at_utc="2025-06-15T15:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            future_event = repo.create_event(
                111,
                title="Майбутнє",
                event_at="2027-06-15T18:00:00+03:00",
                event_at_utc="2027-06-15T15:00:00+00:00",
                timezone="Europe/Kyiv",
            )

            deletion_events = service.get_events_for_deletion(111)

            self.assertEqual([event.id for event in deletion_events], [future_event.id])
            self.assertIsNone(repo.get_event_by_id(past_event.id))


if __name__ == "__main__":
    unittest.main()
