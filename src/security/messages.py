"""Security-related bot responses."""

from __future__ import annotations


def access_denied_text() -> str:
    return (
        "Доступ заборонено.\n\n"
        "Ваш Telegram-акаунт не входить до списку дозволених для цього бота."
    )
