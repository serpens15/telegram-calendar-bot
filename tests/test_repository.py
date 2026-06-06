from __future__ import annotations

import sqlite3
import sys
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

    def test_user_timezone_and_allow_list_persist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            allowed = repo.allow_user(111)
            user = repo.get_or_create_user(111, username="alice", timezone="Europe/Warsaw")
            updated = repo.update_user_timezone(111, "Europe/Kyiv")

            self.assertEqual(allowed.telegram_id, 111)
            self.assertTrue(repo.is_user_allowed(111))
            self.assertEqual(user.telegram_id, 111)
            self.assertEqual(user.timezone, "Europe/Warsaw")
            self.assertEqual(updated.timezone, "Europe/Kyiv")

    def test_events_and_reminders_are_stored(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()

            event = repo.create_event(
                222,
                title="Team sync",
                event_at="2026-06-06T10:00:00+03:00",
                event_at_utc="2026-06-06T07:00:00+00:00",
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
            user_events = repo.list_events_for_user(222)
            event_reminders = repo.list_reminders_for_event(event.id)

            self.assertEqual(event.title, "Team sync")
            self.assertEqual(stored_event.event_at, "2026-06-06T10:00:00+03:00")
            self.assertEqual(stored_event.event_at_utc, "2026-06-06T07:00:00+00:00")
            self.assertEqual(stored_event.timezone, "Europe/Kyiv")
            self.assertEqual(stored_event.source_text, "tomorrow at 10:00")
            self.assertEqual(stored_reminder.reminder_at, "2026-06-06T09:45:00+03:00")
            self.assertEqual(stored_reminder.reminder_at_utc, "2026-06-06T06:45:00+00:00")
            self.assertEqual(len(user_events), 1)
            self.assertEqual(user_events[0].id, event.id)
            self.assertEqual(len(event_reminders), 1)
            self.assertEqual(event_reminders[0].id, reminder.id)

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


if __name__ == "__main__":
    unittest.main()
