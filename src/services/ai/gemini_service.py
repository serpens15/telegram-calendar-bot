"""Gemini fallback parser for event text."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import json
import urllib.error
import urllib.request

from parsing.models import ParsedEventDraft


@dataclass(frozen=True, slots=True)
class GeminiService:
    api_key: str
    model: str = "gemini-2.5-flash"
    timeout_seconds: int = 10

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def parse_event_text(
        self,
        text: str,
        *,
        reference_date: date | None = None,
    ) -> ParsedEventDraft | None:
        if not self.is_configured:
            return None

        reference = reference_date or date.today()
        prompt = _build_prompt(text=text, reference_date=reference)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0,
            },
        }
        response_payload = self._post_generate_content(payload)
        raw_text = _extract_candidate_text(response_payload)
        if raw_text is None:
            return None

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return None

        return _draft_from_payload(source_text=text, payload=data)

    def _post_generate_content(self, payload: dict) -> dict | None:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None


def _build_prompt(*, text: str, reference_date: date) -> str:
    return (
        "Ти парсер подій для Telegram Calendar Bot. "
        "Поверни тільки валідний JSON без markdown. "
        "Не додавай пояснень. "
        "Витягни title, date, time і confidence з українського тексту. "
        "date має бути у форматі YYYY-MM-DD, time у форматі HH:MM. "
        "Якщо поле не визначене, поверни null. "
        "confidence має бути числом від 0 до 1. "
        f"Поточна дата: {reference_date.isoformat()}.\n"
        'Схема: {"title": string|null, "date": string|null, '
        '"time": string|null, "confidence": number}\n'
        f"Текст: {text}"
    )


def _extract_candidate_text(payload: dict | None) -> str | None:
    if not payload:
        return None

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None

    content = candidates[0].get("content")
    if not isinstance(content, dict):
        return None

    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return None

    text = parts[0].get("text")
    return text if isinstance(text, str) else None


def _draft_from_payload(*, source_text: str, payload: dict) -> ParsedEventDraft | None:
    title = payload.get("title")
    date_raw = payload.get("date")
    time_raw = payload.get("time")
    confidence_raw = payload.get("confidence", 0)

    event_date = _parse_date(date_raw)
    event_time = _parse_time(time_raw)
    confidence = _parse_confidence(confidence_raw)

    missing_fields: list[str] = []
    if not isinstance(title, str) or not title.strip():
        title = None
        missing_fields.append("title")
    if event_date is None:
        missing_fields.append("date")
    if event_time is None:
        missing_fields.append("time")

    event_datetime = (
        datetime.combine(event_date, event_time)
        if event_date is not None and event_time is not None
        else None
    )

    return ParsedEventDraft(
        source_text=source_text,
        title=title.strip() if isinstance(title, str) else None,
        event_date=event_date,
        event_time=event_time,
        event_datetime=event_datetime,
        status="complete" if not missing_fields else "needs_clarification",
        missing_fields=tuple(missing_fields),
        confidence=confidence,
        parser_source="gemini",
    )


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_time(value: object) -> time | None:
    if not isinstance(value, str):
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def _parse_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, confidence))
