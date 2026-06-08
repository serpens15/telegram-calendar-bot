from __future__ import annotations

import sys
from datetime import date, datetime
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

    def test_parse_relative_minutes_without_space(self) -> None:
        draft = parse_event_text(
            "через 15хв дзвінок",
            reference_datetime=datetime(2026, 6, 8, 10, 30),
        )

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "дзвінок")
        self.assertEqual(draft.event_date, date(2026, 6, 8))
        self.assertEqual(draft.event_time.isoformat(), "10:45:00")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T10:45:00")

    def test_parse_relative_hour_word(self) -> None:
        draft = parse_event_text(
            "через годину зустріч",
            reference_datetime=datetime(2026, 6, 8, 10, 30),
        )

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "зустріч")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T11:30:00")

    def test_parse_relative_minutes_with_title_before_duration(self) -> None:
        draft = parse_event_text(
            "перевірити через 2 хв",
            reference_datetime=datetime(2026, 6, 8, 10, 30),
        )

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "перевірити")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T10:32:00")

    def test_parse_relative_hours_and_minutes(self) -> None:
        draft = parse_event_text(
            "через 1 год 30 хв кава",
            reference_datetime=datetime(2026, 6, 8, 10, 30),
        )

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "кава")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T12:00:00")

    def test_parse_relative_half_hour(self) -> None:
        draft = parse_event_text(
            "через пів години розминка",
            reference_datetime=datetime(2026, 6, 8, 10, 30),
        )

        self.assertEqual(draft.status, "complete")
        self.assertEqual(draft.title, "розминка")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T11:00:00")

    def test_relative_duration_without_title_requests_clarification(self) -> None:
        draft = parse_event_text(
            "через 15 хв",
            reference_datetime=datetime(2026, 6, 8, 10, 30),
        )

        self.assertEqual(draft.status, "needs_clarification")
        self.assertEqual(draft.missing_fields, ("title",))
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T10:45:00")

    def test_empty_text_is_invalid(self) -> None:
        draft = parse_event_text("   ", reference_date=date(2026, 6, 6))

        self.assertEqual(draft.status, "invalid")
        self.assertEqual(draft.errors, ("empty_text",))
        self.assertIsNone(draft.title)


if __name__ == "__main__":
    unittest.main()
