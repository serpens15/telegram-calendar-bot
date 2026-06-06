"""Security-related bot responses."""

from __future__ import annotations


def access_denied_text() -> str:
    return (
        "Access denied.\n\n"
        "Your Telegram account is not in the allow list for this bot."
    )
