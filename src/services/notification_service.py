"""Notification orchestration for event reminders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NotificationService:
    reminder_scheduler: object | None = None

    def schedule_event_notifications(self, event_id: int) -> None:
        if self.reminder_scheduler is None:
            return

        schedule = getattr(self.reminder_scheduler, "schedule_event_reminders", None)
        if schedule is not None:
            schedule(event_id)
