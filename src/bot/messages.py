"""Static bot responses."""

from __future__ import annotations


START_BUTTON = "Старт"
ADD_BUTTON = "Додати подію"
HELP_BUTTON = "Довідка"
WHOAMI_BUTTON = "Мій ID"
LIST_BUTTON = "Список подій"
DELETE_BUTTON = "Видалити подію"
TIMEZONE_BUTTON = "Часовий пояс"
CONFIRM_BUTTON = "Підтвердити"
CANCEL_BUTTON = "Скасувати"


def start_text() -> str:
    return (
        "Бот Telegram Calendar Bot запущено.\n\n"
        "Надішліть текст події, а кнопки нижче допоможуть швидко відкрити список, "
        "перевірити часовий пояс або підтвердити дію."
    )


def help_text() -> str:
    return (
        "Доступні дії:\n"
        f"{START_BUTTON} - повернутися на головний екран\n"
        f"{ADD_BUTTON} - почати додавання події\n"
        f"{HELP_BUTTON} - показати довідку\n"
        f"{WHOAMI_BUTTON} - показати ваш Telegram ID\n"
        f"{LIST_BUTTON} - показати найближчі події\n"
        f"{DELETE_BUTTON} - почати видалення події\n"
        f"{TIMEZONE_BUTTON} - показати або змінити часовий пояс\n"
        f"{CONFIRM_BUTTON} - зберегти або підтвердити дію\n"
        f"{CANCEL_BUTTON} - скасувати поточну чернетку"
    )


def main_menu_keyboard():
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=START_BUTTON),
                KeyboardButton(text=ADD_BUTTON),
                KeyboardButton(text=LIST_BUTTON),
            ],
            [
                KeyboardButton(text=WHOAMI_BUTTON),
                KeyboardButton(text=DELETE_BUTTON),
                KeyboardButton(text=TIMEZONE_BUTTON),
            ],
            [
                KeyboardButton(text=HELP_BUTTON),
                KeyboardButton(text=CONFIRM_BUTTON),
                KeyboardButton(text=CANCEL_BUTTON),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
