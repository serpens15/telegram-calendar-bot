"""Access control for the MVP allow-list."""

from __future__ import annotations

from dataclasses import dataclass

from db.repository import SQLiteRepository


@dataclass(frozen=True, slots=True)
class AccessControlService:
    allowed_telegram_ids: tuple[int, ...]
    repository: SQLiteRepository

    def sync_allow_list(self) -> None:
        for telegram_id in self.allowed_telegram_ids:
            self.repository.allow_user(telegram_id)

    def is_allowed(self, telegram_id: int | None) -> bool:
        if telegram_id is None:
            return False

        if telegram_id in self.allowed_telegram_ids:
            return True

        return self.repository.is_user_allowed(telegram_id)
