from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository


class SQLiteRepositoryTest(unittest.TestCase):
    def test_initialize_creates_expected_tables_and_timezone_column(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            connection = sqlite3.connect(repo.db_path)
            try:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                user_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(users)").fetchall()
                }
            finally:
                connection.close()

            self.assertTrue({"users", "allowed_users", "events", "reminders"}.issubset(table_names))
            self.assertIn("timezone", user_columns)

    def test_user_timezone_allow_list_and_profile_upsert_persist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            allowed = repo.allow_user(111)
            created = repo.upsert_user_profile(
                111,
                username="alice",
                first_name="Alice",
                last_name="Smith",
                timezone_name="Europe/Warsaw",
            )
            updated = repo.upsert_user_profile(
                111,
                username="alice2",
                first_name="Alicia",
                timezone_name="Europe/Kyiv",
            )
            timezone_user = repo.update_user_timezone(111, "Europe/Berlin")

            self.assertEqual(allowed.telegram_id, 111)
            self.assertTrue(repo.is_user_allowed(111))
            self.assertEqual(created.telegram_id, 111)
            self.assertEqual(updated.username, "alice2")
            self.assertEqual(updated.first_name, "Alicia")
            self.assertEqual(updated.last_name, "Smith")
            self.assertEqual(updated.timezone, "Europe/Kyiv")
            self.assertEqual(timezone_user.timezone, "Europe/Berlin")

    def test_events_and_reminders_are_stored(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            event, reminder_from_event = repo.create_event_with_reminder(
                222,
                title="Team sync",
                event_at="2026-06-06T10:00:00+03:00",
                event_at_utc="2026-06-06T07:00:00+00:00",
                reminder_at="2026-06-06T09:45:00+03:00",
                reminder_at_utc="2026-06-06T06:45:00+00:00",
                timezone="Europe/Kyiv",
                source_text="tomorrow at 10:00",
            )
            reminder = repo.create_reminder(
                event.id,
                reminder_at="2026-06-06T09:45:00+03:00",
                reminder_at_utc="2026-06-06T06:45:00+00:00",
            )

            stored_event = repo.get_event_by_id(event.id)
            stored_reminder = repo.get_reminder_by_id(reminder.id)
            reminder_context = repo.get_reminder_context(reminder_from_event.id)
            user_events = repo.list_events_for_user(222)
            event_reminders = repo.list_reminders_for_event(event.id)

            self.assertEqual(event.title, "Team sync")
            self.assertEqual(stored_event.event_at, "2026-06-06T10:00:00+03:00")
            self.assertEqual(stored_event.event_at_utc, "2026-06-06T07:00:00+00:00")
            self.assertEqual(stored_event.timezone, "Europe/Kyiv")
            self.assertEqual(stored_event.source_text, "tomorrow at 10:00")
            self.assertEqual(reminder_from_event.reminder_at, "2026-06-06T09:45:00+03:00")
            self.assertEqual(reminder_from_event.reminder_at_utc, "2026-06-06T06:45:00+00:00")
            self.assertIsNotNone(reminder_context)
            self.assertEqual(reminder_context.telegram_id, 222)
            self.assertEqual(reminder_context.event.id, event.id)
            self.assertEqual(stored_reminder.reminder_at, "2026-06-06T09:45:00+03:00")
            self.assertEqual(stored_reminder.reminder_at_utc, "2026-06-06T06:45:00+00:00")
            self.assertEqual(len(user_events), 1)
            self.assertEqual(user_events[0].id, event.id)
            self.assertEqual(len(event_reminders), 2)
            self.assertEqual({item.id for item in event_reminders}, {reminder_from_event.id, reminder.id})
            self.assertEqual(len(repo.list_pending_reminders()), 2)

    def test_list_future_events_for_user_filters_past_events(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            now = datetime.now(timezone.utc).replace(microsecond=0)
            past_iso = now.replace(year=now.year - 1).isoformat()
            future_iso = now.replace(year=now.year + 1).isoformat()

            past_event = repo.create_event(
                444,
                title="Past",
                event_at=past_iso,
                event_at_utc=past_iso,
                timezone="UTC",
            )
            future_event = repo.create_event(
                444,
                title="Future",
                event_at=future_iso,
                event_at_utc=future_iso,
                timezone="UTC",
            )

            future_events = repo.list_future_events_for_user(444)
            future_ids = [event.id for event in future_events]

            self.assertNotIn(past_event.id, future_ids)
            self.assertIn(future_event.id, future_ids)
            self.assertIsNone(repo.get_event_by_id(past_event.id))

    def test_delete_event_for_user_removes_matching_event_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            first_event = repo.create_event(
                222,
                title="Team sync",
                event_at="2026-06-06T10:00:00+03:00",
                event_at_utc="2026-06-06T07:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            second_event = repo.create_event(
                333,
                title="Other sync",
                event_at="2026-06-06T11:00:00+03:00",
                event_at_utc="2026-06-06T08:00:00+00:00",
                timezone="Europe/Kyiv",
            )

            deleted = repo.delete_event_for_user(222, first_event.id)
            missing = repo.delete_event_for_user(222, second_event.id)

            self.assertIsNotNone(deleted)
            self.assertEqual(deleted.id, first_event.id)
            self.assertIsNone(missing)
            self.assertEqual(repo.list_events_for_user(222), [])
            self.assertEqual(repo.list_events_for_user(333)[0].id, second_event.id)

    def test_cleanup_completed_events_removes_only_events_without_pending_reminders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            completed_event = repo.create_event(
                222,
                title="Completed",
                event_at="2025-06-06T10:00:00+03:00",
                event_at_utc="2025-06-06T07:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            repo.create_reminder(
                completed_event.id,
                reminder_at="2025-06-06T10:00:00+03:00",
                reminder_at_utc="2025-06-06T07:00:00+00:00",
                status="sent",
                sent_at="2025-06-06T07:00:01+00:00",
            )
            pending_event = repo.create_event(
                222,
                title="Pending delivery",
                event_at="2025-06-07T10:00:00+03:00",
                event_at_utc="2025-06-07T07:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            repo.create_reminder(
                pending_event.id,
                reminder_at="2025-06-07T10:00:00+03:00",
                reminder_at_utc="2025-06-07T07:00:00+00:00",
            )

            removed_count = repo.cleanup_completed_events("2026-06-08T00:00:00+00:00")

            self.assertEqual(removed_count, 1)
            self.assertIsNone(repo.get_event_by_id(completed_event.id))
            self.assertIsNotNone(repo.get_event_by_id(pending_event.id))
            self.assertEqual(len(repo.list_reminders_for_event(completed_event.id)), 0)


if __name__ == "__main__":
    unittest.main()
