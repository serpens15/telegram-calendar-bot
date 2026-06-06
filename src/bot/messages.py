"""Static bot messages and button labels."""

from __future__ import annotations


START_BUTTON = "Старт"
ADD_BUTTON = "➕ Додати подію"
LIST_BUTTON = "Список подій"
DELETE_BUTTON = "Видалити подію"
HELP_BUTTON = "Довідка"
WHOAMI_BUTTON = "Мій ID"
TIMEZONE_BUTTON = "Часовий пояс"
CONFIRM_BUTTON = "Підтвердити"
CANCEL_BUTTON = "Скасувати"


def start_text() -> str:
    return (
        "Ласкаво просимо до Telegram Calendar Bot.\n\n"
        "Натисніть кнопку Старт, щоб зареєструватися та відкрити головне меню."
    )


def registration_completed_text(telegram_id: int, timezone: str) -> str:
    return (
        "✅ Реєстрація завершена\n\n"
        f"Ваш ID: {telegram_id}\n\n"
        f"Часовий пояс: {timezone}"
    )


def timezone_selection_text() -> str:
    return (
        "Не вдалося автоматично визначити ваш часовий пояс.\n\n"
        "Оберіть його вручну зі списку нижче."
    )


def help_text() -> str:
    return (
        "Доступні команди:\n"
        "/start - показати стартовий екран\n"
        "/help - показати довідку\n"
        "/whoami - показати ваш Telegram ID\n"
        "/timezone - переглянути або змінити часовий пояс\n"
        "/list - показати майбутні події\n"
        "/delete - почати видалення події\n"
        "/cancel - скасувати поточну дію\n\n"
        "Основне меню після реєстрації:\n"
        f"{ADD_BUTTON}\n"
        f"{LIST_BUTTON}\n"
        f"{DELETE_BUTTON}"
    )

