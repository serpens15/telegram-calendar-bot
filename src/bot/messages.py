"""Static bot responses."""

from __future__ import annotations


def start_text() -> str:
    return (
        "Telegram Calendar Bot is running.\n\n"
        "Send a reminder idea as text, then use /confirm or /cancel."
    )


def help_text() -> str:
    return (
        "Available commands:\n"
        "/start - show the bot intro\n"
        "/help - show this help message\n"
        "/timezone - show or change your timezone\n"
        "/confirm - save the pending event draft\n"
        "/cancel - discard the pending event draft"
    )
