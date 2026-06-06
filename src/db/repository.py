"""SQLite repository for users, events, reminders, and allow-list data."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from .models import (
    AllowedUserRecord,
    EventRecord,
    ReminderDispatchContext,
    ReminderRecord,
    UserRecord,
)
from .schema import SCHEMA_SQL


def _row_to_dataclass(record_type, row):
    return record_type(**dict(row)) if row is not None else None


class SQLiteRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON;")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            self._apply_migrations(connection)

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        self._add_column_if_missing(connection, "events", "event_at_utc", "TEXT")
        self._add_column_if_missing(connection, "reminders", "reminder_at_utc", "TEXT")

    def _add_column_if_missing(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        existing_columns = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")
        }
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

    def get_user_by_telegram_id(self, telegram_id: int) -> UserRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return _row_to_dataclass(UserRecord, row)

    def get_or_create_user(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        timezone: str = "Europe/Kyiv",
    ) -> UserRecord:
        existing_user = self.get_user_by_telegram_id(telegram_id)
        if existing_user is not None:
            return existing_user

        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (telegram_id, username, first_name, last_name, timezone)
                VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_id, username, first_name, last_name, timezone),
            )
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return _row_to_dataclass(UserRecord, row)

    def update_user_timezone(self, telegram_id: int, timezone: str) -> UserRecord:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET timezone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
                """,
                (timezone, telegram_id),
            )
            row = connection.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return _row_to_dataclass(UserRecord, row)

    def allow_user(self, telegram_id: int) -> AllowedUserRecord:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO allowed_users (telegram_id) VALUES (?)",
                (telegram_id,),
            )
            row = connection.execute(
                "SELECT * FROM allowed_users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return _row_to_dataclass(AllowedUserRecord, row)

    def is_user_allowed(self, telegram_id: int) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM allowed_users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return row is not None

    def create_event(
        self,
        telegram_id: int,
        *,
        title: str,
        event_at: str,
        event_at_utc: str,
        timezone: str | None = None,
        source_text: str | None = None,
    ) -> EventRecord:
        user = self.get_or_create_user(telegram_id, timezone=timezone or "Europe/Kyiv")
        event_timezone = timezone or user.timezone

        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    user_id, title, event_at, event_at_utc, timezone, source_text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user.id, title, event_at, event_at_utc, event_timezone, source_text),
            )
            row = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return _row_to_dataclass(EventRecord, row)

    def create_event_with_reminder(
        self,
        telegram_id: int,
        *,
        title: str,
        event_at: str,
        event_at_utc: str,
        reminder_at: str,
        reminder_at_utc: str,
        timezone: str | None = None,
        source_text: str | None = None,
    ) -> tuple[EventRecord, ReminderRecord]:
        user = self.get_or_create_user(telegram_id, timezone=timezone or "Europe/Kyiv")
        event_timezone = timezone or user.timezone

        with self.connect() as connection:
            event_cursor = connection.execute(
                """
                INSERT INTO events (
                    user_id, title, event_at, event_at_utc, timezone, source_text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user.id, title, event_at, event_at_utc, event_timezone, source_text),
            )
            event_row = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_cursor.lastrowid,),
            ).fetchone()

            reminder_cursor = connection.execute(
                """
                INSERT INTO reminders (
                    event_id, reminder_at, reminder_at_utc, status, sent_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_cursor.lastrowid, reminder_at, reminder_at_utc, "pending", None),
            )
            reminder_row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_cursor.lastrowid,),
            ).fetchone()

        return _row_to_dataclass(EventRecord, event_row), _row_to_dataclass(
            ReminderRecord,
            reminder_row,
        )

    def create_reminder(
        self,
        event_id: int,
        *,
        reminder_at: str,
        reminder_at_utc: str,
        status: str = "pending",
        sent_at: str | None = None,
    ) -> ReminderRecord:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders (
                    event_id, reminder_at, reminder_at_utc, status, sent_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, reminder_at, reminder_at_utc, status, sent_at),
            )
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return _row_to_dataclass(ReminderRecord, row)

    def get_event_by_id(self, event_id: int) -> EventRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return _row_to_dataclass(EventRecord, row)

    def get_event_for_user(
        self,
        telegram_id: int,
        event_id: int,
    ) -> EventRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT events.*
                FROM events
                JOIN users ON users.id = events.user_id
                WHERE users.telegram_id = ? AND events.id = ?
                """,
                (telegram_id, event_id),
            ).fetchone()
        return _row_to_dataclass(EventRecord, row)

    def delete_event_for_user(
        self,
        telegram_id: int,
        event_id: int,
    ) -> EventRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT events.*
                FROM events
                JOIN users ON users.id = events.user_id
                WHERE users.telegram_id = ? AND events.id = ?
                """,
                (telegram_id, event_id),
            ).fetchone()
            if row is None:
                return None

            connection.execute(
                "DELETE FROM events WHERE id = ?",
                (event_id,),
            )
        return _row_to_dataclass(EventRecord, row)

    def get_reminder_by_id(self, reminder_id: int) -> ReminderRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()
        return _row_to_dataclass(ReminderRecord, row)

    def get_reminder_context(
        self,
        reminder_id: int,
    ) -> ReminderDispatchContext | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    reminders.id AS reminder_id,
                    reminders.event_id AS reminder_event_id,
                    reminders.reminder_at AS reminder_reminder_at,
                    reminders.reminder_at_utc AS reminder_reminder_at_utc,
                    reminders.status AS reminder_status,
                    reminders.sent_at AS reminder_sent_at,
                    reminders.created_at AS reminder_created_at,
                    reminders.updated_at AS reminder_updated_at,
                    events.id AS event_id,
                    events.user_id AS event_user_id,
                    events.title AS event_title,
                    events.event_at AS event_event_at,
                    events.event_at_utc AS event_event_at_utc,
                    events.timezone AS event_timezone,
                    events.source_text AS event_source_text,
                    events.created_at AS event_created_at,
                    events.updated_at AS event_updated_at,
                    users.telegram_id AS user_telegram_id,
                    users.timezone AS user_timezone
                FROM reminders
                JOIN events ON events.id = reminders.event_id
                JOIN users ON users.id = events.user_id
                WHERE reminders.id = ?
                """,
                (reminder_id,),
            ).fetchone()

        if row is None:
            return None

        reminder = ReminderRecord(
            id=row["reminder_id"],
            event_id=row["reminder_event_id"],
            reminder_at=row["reminder_reminder_at"],
            reminder_at_utc=row["reminder_reminder_at_utc"],
            status=row["reminder_status"],
            sent_at=row["reminder_sent_at"],
            created_at=row["reminder_created_at"],
            updated_at=row["reminder_updated_at"],
        )
        event = EventRecord(
            id=row["event_id"],
            user_id=row["event_user_id"],
            title=row["event_title"],
            event_at=row["event_event_at"],
            event_at_utc=row["event_event_at_utc"],
            timezone=row["event_timezone"],
            source_text=row["event_source_text"],
            created_at=row["event_created_at"],
            updated_at=row["event_updated_at"],
        )
        return ReminderDispatchContext(
            reminder=reminder,
            event=event,
            telegram_id=row["user_telegram_id"],
            timezone=row["user_timezone"],
        )

    def list_pending_reminders(self) -> list[ReminderRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM reminders
                WHERE status = 'pending'
                ORDER BY reminder_at_utc ASC, id ASC
                """
            ).fetchall()
        return [_row_to_dataclass(ReminderRecord, row) for row in rows]

    def mark_reminder_sent(self, reminder_id: int, sent_at: str) -> ReminderRecord | None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE reminders
                SET status = 'sent',
                    sent_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (sent_at, reminder_id),
            )
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()
        return _row_to_dataclass(ReminderRecord, row)

    def list_events_for_user(self, telegram_id: int) -> list[EventRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT events.*
                FROM events
                JOIN users ON users.id = events.user_id
                WHERE users.telegram_id = ?
                ORDER BY events.event_at ASC, events.id ASC
                """,
                (telegram_id,),
            ).fetchall()
        return [
            _row_to_dataclass(EventRecord, row)
            for row in rows
        ]

    def list_reminders_for_event(self, event_id: int) -> list[ReminderRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM reminders
                WHERE event_id = ?
                ORDER BY reminder_at ASC, id ASC
                """,
                (event_id,),
            ).fetchall()
        return [
            _row_to_dataclass(ReminderRecord, row)
            for row in rows
        ]
