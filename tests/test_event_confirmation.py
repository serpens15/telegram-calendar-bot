from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository
from parsing.models import ParsedEventDraft
from services.event_confirmation import EventConfirmationService
from services.timezone_service import TimezoneService


class EventConfirmationServiceTest(unittest.TestCase):
    def _complete_draft(self) -> ParsedEventDraft:
        return ParsedEventDraft(
            source_text="завтра о 15:00 зустріч",
            title="зустріч",
            event_date=date(2026, 6, 7),
            event_time=datetime(2026, 6, 7, 15, 0).time(),
            event_datetime=datetime(2026, 6, 7, 15, 0),
            status="complete",
        )

    def test_preview_marks_draft_pending(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = EventConfirmationService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                default_timezone="Europe/Kyiv",
            )

            draft = self._complete_draft()
            preview = service.preview_or_clarify(111, draft)

            self.assertIn("Preview:", preview)
            self.assertIn("Title: зустріч", preview)
            self.assertIn("Timezone: Europe/Kyiv", preview)
            self.assertIn("UTC:", preview)
            self.assertIs(service.get_pending(111), draft)

    def test_confirm_creates_event_and_clears_pending(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = EventConfirmationService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                default_timezone="Europe/Kyiv",
            )
            draft = self._complete_draft()
            service.set_pending(111, draft)

            event = service.confirm_pending(111)

            self.assertIsNotNone(event)
            self.assertEqual(event.title, "зустріч")
            self.assertEqual(event.event_at, "2026-06-07T15:00:00+03:00")
            self.assertEqual(event.event_at_utc, "2026-06-07T12:00:00+00:00")
            self.assertEqual(service.get_pending(111), None)
            self.assertEqual(repo.list_events_for_user(111)[0].id, event.id)

    def test_cancel_clears_pending_without_creating_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = EventConfirmationService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                default_timezone="Europe/Kyiv",
            )
            service.set_pending(111, self._complete_draft())

            cancelled = service.cancel_pending(111)

            self.assertTrue(cancelled)
            self.assertIsNone(service.get_pending(111))
            self.assertEqual(repo.list_events_for_user(111), [])


if __name__ == "__main__":
    unittest.main()
