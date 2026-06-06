from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsing import parse_event_text


class ParsingTest(unittest.TestCase):
    def test_parse_relative_date_and_time(self) -> None:
        draft = parse_event_text("завтра о 15:00 зустріч", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "зустріч")
        self.assertEqual(draft.event_date, date(2026, 6, 7))
        self.assertEqual(draft.event_time.isoformat(), "15:00:00")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-07T15:00:00")
        self.assertEqual(draft.missing_fields, ())

    def test_parse_absolute_numeric_date(self) -> None:
        draft = parse_event_text("25.06.2026 09:30 дзвінок", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "дзвінок")
        self.assertEqual(draft.event_date, date(2026, 6, 25))
        self.assertEqual(draft.event_time.isoformat(), "09:30:00")

    def test_parse_month_name_date(self) -> None:
        draft = parse_event_text("1 липня 18:00 сімейна вечеря", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "сімейна вечеря")
        self.assertEqual(draft.event_date, date(2026, 7, 1))
        self.assertEqual(draft.event_time.isoformat(), "18:00:00")

    def test_missing_date_requests_clarification(self) -> None:
        draft = parse_event_text("о 15:00 зустріч", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "needs_clarification")
        self.assertEqual(draft.missing_fields, ("date",))
        self.assertEqual(draft.title, "зустріч")
        self.assertIsNone(draft.event_date)

    def test_missing_time_requests_clarification(self) -> None:
        draft = parse_event_text("завтра зустріч", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "needs_clarification")
        self.assertEqual(draft.missing_fields, ("time",))
        self.assertEqual(draft.event_date, date(2026, 6, 7))
        self.assertEqual(draft.title, "зустріч")

    def test_empty_text_is_invalid(self) -> None:
        draft = parse_event_text("   ", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "invalid")
        self.assertEqual(draft.errors, ("empty_text",))
        self.assertIsNone(draft.title)


if __name__ == "__main__":
    unittest.main()
