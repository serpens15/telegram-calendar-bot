"""Keyboard builders for the Telegram bot UI."""

from __future__ import annotations

from dataclasses import dataclass

from .messages import (
    ADD_BUTTON,
    CANCEL_BUTTON,
    DELETE_BUTTON,
    LIST_BUTTON,
    START_BUTTON,
)


TIMEZONE_CALLBACK_PREFIX = "timezone:"
EVENT_DELETE_CALLBACK_PREFIX = "event:delete:"
EVENT_DELETE_CONFIRM_CALLBACK_PREFIX = "event:delete:confirm:"
EVENT_CREATE_CONFIRM_CALLBACK = "event:create:confirm"
EVENT_CREATE_CANCEL_CALLBACK = "event:create:cancel"
EVENT_CREATE_EDIT_DATE_CALLBACK = "event:create:edit_date"
EVENT_CREATE_EDIT_TIME_CALLBACK = "event:create:edit_time"
EVENT_CREATE_DATE_CALLBACK_PREFIX = "event:create:date:"
EVENT_CREATE_TIME_CALLBACK_PREFIX = "event:create:time:"
EVENT_CREATE_RELATIVE_CALLBACK_PREFIX = "event:create:relative:"
EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX = "event:create:time_slider:"
EVENT_CREATE_TIME_SLIDER_DONE_CALLBACK = "event:create:time_slider:done"
EVENT_DELETE_CANCEL_CALLBACK = "event:delete:cancel"

SUPPORTED_TIMEZONES: tuple[str, ...] = (
    "Europe/Kyiv",
    "Europe/Warsaw",
    "Europe/Berlin",
    "Europe/London",
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
)


@dataclass(frozen=True, slots=True)
class DeleteEventKeyboardItem:
    event_id: int
    title: str
    event_at: str


def _keyboard_button(text: str):
    from aiogram.types import KeyboardButton

    return KeyboardButton(text=text)


def _inline_button(text: str, callback_data: str):
    from aiogram.types import InlineKeyboardButton

    return InlineKeyboardButton(text=text, callback_data=callback_data)


def start_keyboard():
    from aiogram.types import ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        keyboard=[[_keyboard_button(START_BUTTON)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def main_menu_keyboard():
    from aiogram.types import ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        keyboard=[
            [_keyboard_button(ADD_BUTTON)],
            [_keyboard_button(LIST_BUTTON)],
            [_keyboard_button(DELETE_BUTTON)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def event_confirmation_keyboard():
    from aiogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _inline_button("✅ Підтвердити", EVENT_CREATE_CONFIRM_CALLBACK),
            ],
            [
                _inline_button("✏️ Змінити дату", EVENT_CREATE_EDIT_DATE_CALLBACK),
                _inline_button("✏️ Змінити час", EVENT_CREATE_EDIT_TIME_CALLBACK),
            ],
            [
                _inline_button("❌ Скасувати", EVENT_CREATE_CANCEL_CALLBACK),
            ]
        ]
    )


def event_date_selection_keyboard():
    from aiogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _inline_button("Сьогодні", f"{EVENT_CREATE_DATE_CALLBACK_PREFIX}today"),
                _inline_button("Завтра", f"{EVENT_CREATE_DATE_CALLBACK_PREFIX}tomorrow"),
            ],
            [
                _inline_button(
                    "Післязавтра",
                    f"{EVENT_CREATE_DATE_CALLBACK_PREFIX}after_tomorrow",
                ),
            ],
            [
                _inline_button("+15 хв", f"{EVENT_CREATE_RELATIVE_CALLBACK_PREFIX}15"),
                _inline_button("+30 хв", f"{EVENT_CREATE_RELATIVE_CALLBACK_PREFIX}30"),
            ],
            [
                _inline_button("+1 год", f"{EVENT_CREATE_RELATIVE_CALLBACK_PREFIX}60"),
                _inline_button("+2 год", f"{EVENT_CREATE_RELATIVE_CALLBACK_PREFIX}120"),
            ],
        ]
    )


def event_time_selection_keyboard():
    from aiogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _inline_button("09:00", f"{EVENT_CREATE_TIME_CALLBACK_PREFIX}09:00"),
                _inline_button("12:00", f"{EVENT_CREATE_TIME_CALLBACK_PREFIX}12:00"),
                _inline_button("15:00", f"{EVENT_CREATE_TIME_CALLBACK_PREFIX}15:00"),
            ],
            [
                _inline_button("18:00", f"{EVENT_CREATE_TIME_CALLBACK_PREFIX}18:00"),
                _inline_button("21:00", f"{EVENT_CREATE_TIME_CALLBACK_PREFIX}21:00"),
            ],
        ]
    )


def event_time_slider_keyboard(selected_hour: int, selected_minute: int):
    from aiogram.types import InlineKeyboardMarkup

    hour = selected_hour % 24
    minute = selected_minute % 60
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_inline_button("Година:", "event:create:noop")],
            [
                _inline_button(
                    "◀️",
                    f"{EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX}hour:-1",
                ),
                _inline_button(f"{hour:02d}", "event:create:noop"),
                _inline_button(
                    "▶️",
                    f"{EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX}hour:1",
                ),
            ],
            [_inline_button("Хвилини:", "event:create:noop")],
            [
                _inline_button(
                    "◀️",
                    f"{EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX}minute:-5",
                ),
                _inline_button(f"{minute:02d}", "event:create:noop"),
                _inline_button(
                    "▶️",
                    f"{EVENT_CREATE_TIME_SLIDER_CALLBACK_PREFIX}minute:5",
                ),
            ],
            [_inline_button("Готово", EVENT_CREATE_TIME_SLIDER_DONE_CALLBACK)],
        ]
    )


def delete_confirmation_keyboard(event_id: int):
    from aiogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _inline_button(
                    "✅ Так",
                    f"{EVENT_DELETE_CONFIRM_CALLBACK_PREFIX}{event_id}",
                ),
                _inline_button(
                    "❌ Ні",
                    f"{EVENT_DELETE_CANCEL_CALLBACK}",
                ),
            ]
        ]
    )


def timezone_selection_keyboard():
    from aiogram.types import InlineKeyboardMarkup

    rows = [
        [
            _inline_button("Europe/Kyiv", f"{TIMEZONE_CALLBACK_PREFIX}Europe/Kyiv"),
            _inline_button("Europe/Warsaw", f"{TIMEZONE_CALLBACK_PREFIX}Europe/Warsaw"),
        ],
        [
            _inline_button("Europe/Berlin", f"{TIMEZONE_CALLBACK_PREFIX}Europe/Berlin"),
            _inline_button("Europe/London", f"{TIMEZONE_CALLBACK_PREFIX}Europe/London"),
        ],
        [
            _inline_button("UTC", f"{TIMEZONE_CALLBACK_PREFIX}UTC"),
            _inline_button(
                "America/New_York",
                f"{TIMEZONE_CALLBACK_PREFIX}America/New_York",
            ),
        ],
        [
            _inline_button(
                "America/Chicago",
                f"{TIMEZONE_CALLBACK_PREFIX}America/Chicago",
            ),
            _inline_button(
                "America/Denver",
                f"{TIMEZONE_CALLBACK_PREFIX}America/Denver",
            ),
        ],
        [
            _inline_button(
                "America/Los_Angeles",
                f"{TIMEZONE_CALLBACK_PREFIX}America/Los_Angeles",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_events_keyboard(items: list[DeleteEventKeyboardItem]):
    from aiogram.types import InlineKeyboardMarkup

    inline_rows = []
    for item in items:
        inline_rows.append(
            [
                _inline_button(
                    f"Видалити: {item.title}",
                    f"{EVENT_DELETE_CALLBACK_PREFIX}{item.event_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=inline_rows)
