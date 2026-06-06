"""FSM state groups for the bot."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_timezone = State()


class EventCreationStates(StatesGroup):
    waiting_title = State()
    waiting_date = State()
    waiting_time = State()
    confirming = State()

