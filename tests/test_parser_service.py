from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsing.models import ParsedEventDraft
from parsing.parser_service import ParserService


class _FakeAIParser:
    def __init__(self, draft: ParsedEventDraft | None):
        self.draft = draft
        self.calls: list[str] = []

    def parse_event_text(self, text: str, *, reference_date=None):
        self.calls.append(text)
        return self.draft


class ParserServiceTest(unittest.TestCase):
    def test_local_parser_prevents_ai_call_when_confident(self) -> None:
        ai = _FakeAIParser(None)
        service = ParserService(ai_parser=ai, confidence_threshold=0.85)

        draft = service.parse(
            "Завтра о 15:00 зустріч з Андрієм",
            reference_date=date(2026, 6, 8),
        )

        self.assertEqual(draft.parser_source, "local")
        self.assertEqual(draft.status, "complete")
        self.assertEqual(ai.calls, [])

    def test_ai_fallback_used_when_local_parser_is_incomplete(self) -> None:
        ai_draft = ParsedEventDraft(
            source_text="зустріч після обіду",
            title="зустріч",
            event_date=date(2026, 6, 8),
            event_time=datetime(2026, 6, 8, 15, 0).time(),
            event_datetime=datetime(2026, 6, 8, 15, 0),
            status="complete",
            confidence=0.95,
            parser_source="gemini",
        )
        ai = _FakeAIParser(ai_draft)
        service = ParserService(ai_parser=ai, confidence_threshold=0.85)

        draft = service.parse("зустріч після обіду", reference_date=date(2026, 6, 8))

        self.assertEqual(draft.parser_source, "gemini")
        self.assertEqual(draft.event_datetime.isoformat(), "2026-06-08T15:00:00")
        self.assertEqual(ai.calls, ["зустріч після обіду"])

    def test_low_confidence_ai_result_keeps_local_draft(self) -> None:
        ai_draft = ParsedEventDraft(
            source_text="зустріч після обіду",
            title="зустріч",
            event_date=date(2026, 6, 8),
            event_time=datetime(2026, 6, 8, 15, 0).time(),
            event_datetime=datetime(2026, 6, 8, 15, 0),
            status="complete",
            confidence=0.4,
            parser_source="gemini",
        )
        service = ParserService(ai_parser=_FakeAIParser(ai_draft), confidence_threshold=0.85)

        draft = service.parse("зустріч після обіду", reference_date=date(2026, 6, 8))

        self.assertEqual(draft.parser_source, "local")
        self.assertEqual(draft.status, "needs_clarification")


if __name__ == "__main__":
    unittest.main()
