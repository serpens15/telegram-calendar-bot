"""Backward-compatible settings import."""

from __future__ import annotations

from config.settings import BotSettings, load_settings

__all__ = ["BotSettings", "load_settings"]
