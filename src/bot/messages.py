"""Static bot responses."""

from __future__ import annotations


def start_text() -> str:
    return (
        "Telegram Calendar Bot is running.\n\n"
        "Send a reminder idea as text and the next step will be added later."
    )


def help_text() -> str:
    return (
        "Available commands:\n"
        "/start - show the bot intro\n"
        "/help - show this help message"
    )

