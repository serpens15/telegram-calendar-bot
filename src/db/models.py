"""Dataclasses for SQLite-backed records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    timezone: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class AllowedUserRecord:
    id: int
    telegram_id: int
    created_at: str


@dataclass(frozen=True, slots=True)
class EventRecord:
    id: int
    user_id: int
    title: str
    event_at: str
    timezone: str
    source_text: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ReminderRecord:
    id: int
    event_id: int
    reminder_at: str
    status: str
    sent_at: str | None
    created_at: str
    updated_at: str
