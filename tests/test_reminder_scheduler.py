from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import types
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository
from scheduler.reminder_scheduler import ReminderSchedulerService
from services.timezone_service import TimezoneService


class _FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, object]] = []
        self.started = False
        self.shutdown_called = False

    @property
    def running(self) -> bool:
        return self.started

    def add_job(self, func, trigger, *, args=None, id=None, replace_existing=False, misfire_grace_time=None):
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "args": tuple(args or ()),
                "id": id,
                "replace_existing": replace_existing,
                "misfire_grace_time": misfire_grace_time,
            }
        )

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = False) -> None:
        self.shutdown_called = True


class _FakeBot:
    def __init__(self, bot_id: int = 999) -> None:
        self.bot_id = bot_id
        self.messages: list[tuple[int, str]] = []
        self.get_me_calls = 0

    async def get_me(self):
        self.get_me_calls += 1
        return types.SimpleNamespace(id=self.bot_id)

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


class ReminderSchedulerServiceTest(unittest.TestCase):
    def test_start_schedules_pending_reminders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            event, reminder = repo.create_event_with_reminder(
                111,
                title="Planning",
                event_at="2026-06-07T15:00:00+03:00",
                event_at_utc="2026-06-07T12:00:00+00:00",
                reminder_at="2026-06-07T14:45:00+03:00",
                reminder_at_utc="2026-06-07T11:45:00+00:00",
                timezone="Europe/Kyiv",
            )
            scheduler = _FakeScheduler()
            service = ReminderSchedulerService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                bot=_FakeBot(),
                scheduler=scheduler,
            )

            service.start()

        self.assertTrue(scheduler.started)
        self.assertEqual(len(scheduler.jobs), 1)
        self.assertEqual(scheduler.jobs[0]["id"], f"reminder-{reminder.id}")
        self.assertEqual(event.id, reminder.event_id)

    def test_deliver_reminder_sends_message_and_marks_sent(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            event, reminder = repo.create_event_with_reminder(
                111,
                title="Planning",
                event_at="2026-06-07T15:00:00+03:00",
                event_at_utc="2026-06-07T12:00:00+00:00",
                reminder_at="2026-06-07T14:45:00+03:00",
                reminder_at_utc="2026-06-07T11:45:00+00:00",
                timezone="Europe/Kyiv",
            )
            bot = _FakeBot()
            service = ReminderSchedulerService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                bot=bot,
                scheduler=_FakeScheduler(),
            )

            asyncio.run(service._deliver_reminder(reminder.id))
            stored_reminder = repo.get_reminder_by_id(reminder.id)

        self.assertEqual(bot.messages, [(111, "15:00 Planning")])
        self.assertEqual(stored_reminder.status, "sent")
        self.assertIsNotNone(stored_reminder.sent_at)
        self.assertEqual(event.id, reminder.event_id)

    def test_deliver_event_time_reminder_deletes_completed_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            event, reminder = repo.create_event_with_reminder(
                111,
                title="Planning",
                event_at="2026-06-07T15:00:00+03:00",
                event_at_utc="2026-06-07T12:00:00+00:00",
                reminder_at="2026-06-07T15:00:00+03:00",
                reminder_at_utc="2026-06-07T12:00:00+00:00",
                timezone="Europe/Kyiv",
            )
            bot = _FakeBot()
            service = ReminderSchedulerService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                bot=bot,
                scheduler=_FakeScheduler(),
            )

            asyncio.run(service._deliver_reminder(reminder.id))

            self.assertEqual(bot.messages[0][0], 111)
            self.assertIsNone(repo.get_event_by_id(event.id))
            self.assertIsNone(repo.get_reminder_by_id(reminder.id))

    def test_deliver_reminder_deletes_event_when_recipient_is_bot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            event, reminder = repo.create_event_with_reminder(
                999,
                title="Invalid recipient",
                event_at="2026-06-07T15:00:00+03:00",
                event_at_utc="2026-06-07T12:00:00+00:00",
                reminder_at="2026-06-07T14:45:00+03:00",
                reminder_at_utc="2026-06-07T11:45:00+00:00",
                timezone="Europe/Kyiv",
            )
            bot = _FakeBot(bot_id=999)
            service = ReminderSchedulerService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                bot=bot,
                scheduler=_FakeScheduler(),
            )

            asyncio.run(service._deliver_reminder(reminder.id))

            self.assertEqual(bot.messages, [])
            self.assertEqual(bot.get_me_calls, 1)
            self.assertIsNone(repo.get_event_by_id(event.id))
            self.assertIsNone(repo.get_reminder_by_id(reminder.id))

    def test_deliver_reminder_skips_missing_rows(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            service = ReminderSchedulerService(
                repository=repo,
                timezone_service=TimezoneService(
                    repository=repo,
                    default_timezone="Europe/Kyiv",
                ),
                bot=_FakeBot(),
                scheduler=_FakeScheduler(),
            )

            asyncio.run(service._deliver_reminder(999))


if __name__ == "__main__":
    unittest.main()
