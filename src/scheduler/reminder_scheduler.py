"""Reminder scheduling and delivery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
import inspect
import logging
from typing import Any, Callable

from aiogram import Bot

from db.models import ReminderRecord
from db.repository import SQLiteRepository
from services.timezone_service import TimezoneService


logger = logging.getLogger(__name__)


try:  # pragma: no cover - exercised implicitly when APScheduler is installed.
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.date import DateTrigger
except ModuleNotFoundError:  # pragma: no cover - fallback for stripped environments.

    class DateTrigger:  # type: ignore[override]
        def __init__(self, *, run_date: datetime) -> None:
            self.run_date = run_date


    class AsyncIOScheduler:  # type: ignore[override]
        def __init__(self, timezone: Any = dt_timezone.utc) -> None:
            self.timezone = timezone
            self._jobs: dict[str, asyncio.Task[Any]] = {}
            self._pending_jobs: dict[str, dict[str, Any]] = {}
            self._running = False

        @property
        def running(self) -> bool:
            return self._running

        def add_job(
            self,
            func: Callable[..., Any],
            trigger: DateTrigger,
            *,
            args: list[Any] | tuple[Any, ...] | None = None,
            id: str | None = None,
            replace_existing: bool = False,
            misfire_grace_time: int | None = None,
        ) -> None:
            job_id = id or f"job-{len(self._pending_jobs) + len(self._jobs) + 1}"
            if not replace_existing and (job_id in self._jobs or job_id in self._pending_jobs):
                raise ValueError(f"Job {job_id!r} already exists")

            job = {
                "func": func,
                "trigger": trigger,
                "args": tuple(args or ()),
                "id": job_id,
                "misfire_grace_time": misfire_grace_time,
            }

            if self._running:
                self._schedule_job(job)
            else:
                self._pending_jobs[job_id] = job

        def _schedule_job(self, job: dict[str, Any]) -> None:
            run_date = job["trigger"].run_date
            delay = max(0.0, (run_date - datetime.now(dt_timezone.utc)).total_seconds())
            self._jobs[job["id"]] = asyncio.create_task(self._run_job(job, delay))

        async def _run_job(self, job: dict[str, Any], delay: float) -> None:
            try:
                if delay > 0:
                    await asyncio.sleep(delay)
                result = job["func"](*job["args"])
                if inspect.isawaitable(result):
                    await result
            finally:
                self._jobs.pop(job["id"], None)

        def start(self) -> None:
            if self._running:
                return
            self._running = True
            pending_jobs = list(self._pending_jobs.values())
            self._pending_jobs.clear()
            for job in pending_jobs:
                self._schedule_job(job)

        def shutdown(self, wait: bool = False) -> None:
            self._running = False
            for task in list(self._jobs.values()):
                task.cancel()
            self._jobs.clear()
            self._pending_jobs.clear()


@dataclass(slots=True)
class ReminderSchedulerService:
    repository: SQLiteRepository
    timezone_service: TimezoneService
    bot: Bot
    default_reminder_minutes: int = 15
    scheduler: AsyncIOScheduler | None = None
    _started: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler(timezone=dt_timezone.utc)

    def start(self) -> None:
        self.sync_pending_reminders()
        self.scheduler.start()
        self._started = True

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        self._started = False

    def sync_pending_reminders(self) -> None:
        for reminder in self.repository.list_pending_reminders():
            self.schedule_reminder(reminder)

    def schedule_event_reminders(self, event_id: int) -> None:
        for reminder in self.repository.list_reminders_for_event(event_id):
            if reminder.status == "pending":
                self.schedule_reminder(reminder)

    def schedule_reminder(self, reminder: ReminderRecord) -> None:
        if reminder.status != "pending":
            return

        run_date = self._parse_utc_datetime(reminder.reminder_at_utc)
        scheduled_run_date = max(run_date, datetime.now(dt_timezone.utc))
        self.scheduler.add_job(
            self._deliver_reminder,
            DateTrigger(run_date=scheduled_run_date),
            args=[reminder.id],
            id=f"reminder-{reminder.id}",
            replace_existing=True,
            misfire_grace_time=3600,
        )

    async def _deliver_reminder(self, reminder_id: int) -> None:
        context = self.repository.get_reminder_context(reminder_id)
        if context is None or context.reminder.status != "pending":
            return

        message = f"{self._format_event_time(context.event.event_at)} {context.event.title}"

        try:
            await self.bot.send_message(chat_id=context.telegram_id, text=message)
        except Exception:
            logger.exception("Failed to deliver reminder %s", reminder_id)
            return

        self.repository.mark_reminder_sent(
            reminder_id,
            sent_at=datetime.now(dt_timezone.utc).isoformat(),
        )
        if self._is_event_time_reminder(context.reminder.reminder_at_utc, context.event.event_at_utc):
            self.repository.delete_event(context.event.id)

    def _parse_utc_datetime(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt_timezone.utc)
        return parsed.astimezone(dt_timezone.utc)

    def _is_event_time_reminder(self, reminder_at_utc: str, event_at_utc: str) -> bool:
        return self._parse_utc_datetime(reminder_at_utc) >= self._parse_utc_datetime(event_at_utc)

    def _format_event_time(self, event_at: str) -> str:
        try:
            return datetime.fromisoformat(event_at).strftime("%H:%M")
        except ValueError:
            return event_at
