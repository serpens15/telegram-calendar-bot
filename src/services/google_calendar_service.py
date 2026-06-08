"""Google Calendar integration placeholder.

Real Google Calendar sync is outside the current text-first MVP because it needs
OAuth setup and separate privacy decisions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoogleCalendarService:
    enabled: bool = False

    def create_event(self, *args, **kwargs) -> None:
        if not self.enabled:
            return None
        raise NotImplementedError("Google Calendar integration is not configured yet.")
