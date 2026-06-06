from __future__ import annotations

import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.repository import SQLiteRepository
from security.access_control import AccessControlService


class AccessControlTest(unittest.TestCase):
    def test_empty_allow_list_blocks_everyone(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            access_control = AccessControlService(allowed_telegram_ids=(), repository=repo)

            self.assertFalse(access_control.is_allowed(123))
            self.assertFalse(access_control.is_allowed(None))

    def test_config_allow_list_grants_access_and_syncs_to_db(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            access_control = AccessControlService(
                allowed_telegram_ids=(111, 222),
                repository=repo,
            )

            access_control.sync_allow_list()

            self.assertTrue(access_control.is_allowed(111))
            self.assertTrue(access_control.is_allowed(222))
            self.assertFalse(access_control.is_allowed(333))
            self.assertTrue(repo.is_user_allowed(111))
            self.assertTrue(repo.is_user_allowed(222))

    def test_database_allow_list_is_respected(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo = SQLiteRepository(Path(temp_dir) / "calendar.sqlite3")
            repo.initialize()
            repo.allow_user(444)
            access_control = AccessControlService(allowed_telegram_ids=(), repository=repo)

            self.assertTrue(access_control.is_allowed(444))


if __name__ == "__main__":
    unittest.main()
