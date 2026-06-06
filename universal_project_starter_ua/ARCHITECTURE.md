# ARCHITECTURE

Цей файл описує технічну структуру проєкту.

## 1. Architecture Summary

MVP побудований як один Python-сервіс Telegram-бота з окремими шарами для обробки повідомлень, транскрибації голосу, парсингу дати й часу, збереження даних та планування нагадувань.

Основна ідея: handler лише приймає подію з Telegram, далі бізнес-логіка працює через сервіси, а зберігання і нагадування винесені в окремі модулі.

## 2. Components

```text
- Telegram Bot Layer:
  Responsibility: прийом команд, тексту, voice message, callback data, відправка відповідей користувачу.

- Parsing Layer:
  Responsibility: розпізнавання природної мови, виділення назви події, дати, часу і timezone.

- Voice Transcription Layer:
  Responsibility: завантаження аудіо з Telegram і перетворення voice message у текст через Whisper.

- Application Service Layer:
  Responsibility: orchestration сценаріїв створення, підтвердження, списку і видалення подій.

- Storage Layer:
  Responsibility: робота з SQLite, users, events, reminders, allowed users.

- Scheduler Layer:
  Responsibility: планування та відправка локальних нагадувань через APScheduler.
```

## 3. Data Flow

```text
User action
-> Telegram update
-> Access check
-> Message type detection
-> Text parser або Whisper transcription
-> Date/time extraction and validation
-> Confirmation preview
-> User confirmation
-> SQLite persistence
-> Scheduler registration
-> Telegram reminder message
```

## 4. Storage

```text
Database: SQLite

Main entities:
- User
- Event
- Reminder
- AllowedUser

Important fields:
- User: id, telegram_id, timezone, default_reminder_minutes, created_at
- Event: id, user_id, title, description, event_datetime_utc, event_datetime_local, timezone, status, source_text, created_at, updated_at
- Reminder: id, event_id, reminder_datetime_utc, status, sent_at, created_at
- AllowedUser: id, telegram_id, is_admin, created_at
```

### Storage Notes

- `event_datetime_utc` використовується для точного запуску нагадувань.
- `timezone` зберігається в IANA форматі, наприклад `Europe/Kyiv`.
- `source_text` корисний для дебагу парсингу, але без збереження зайвих секретних даних.
- База SQLite підходить для MVP і локального запуску.

## 5. External Services

```text
- Telegram Bot API:
  Purpose: прийом повідомлень і відправка відповідей.
  Cost: безкоштовно для MVP.
  Risks: rate limits, тимчасова недоступність.
  Alternative: немає для основного сценарію.

- Whisper:
  Purpose: speech-to-text для голосових повідомлень.
  Cost: або локальна модель, або платний API залежно від фінальної реалізації.
  Risks: точність розпізнавання, затримки, вартість.
  Alternative: локальний faster-whisper.

- APScheduler:
  Purpose: локальне планування нагадувань.
  Cost: безкоштовно.
  Risks: втрата задач при неправильному відновленні після рестарту.
  Alternative: окремий job queue або cron-based worker на наступному етапі.
```

## 6. Technology Stack Options

Перед остаточним вибором стеку AI вже погодив з користувачем основний напрям. Нижче наведені два робочі варіанти, але для MVP обрано найпростіший.

| Option | Simplicity | Speed | Scalability | Cost | Risks | MVP Fit |
|---|---|---|---|---|---|---|
| Python + aiogram + SQLite + APScheduler + Whisper | High | High | Medium | Low | Потрібно акуратно відновлювати нагадування після рестарту | Best |
| Python + aiogram + PostgreSQL + Celery + Whisper | Medium | Medium | High | Medium | Більше інфраструктури, складніше для MVP | Good, but heavy |

## 7. Chosen Stack

```text
Frontend:
  Telegram chat interface

Backend:
  Python 3.12+, aiogram

Database:
  SQLite for MVP

Infrastructure:
  Local run first, later simple VPS or free hosting

Testing:
  pytest

Other:
  Whisper for voice transcription
  APScheduler for reminders
  python-dotenv or pydantic-settings for configuration
```

## 8. Architecture Risks

```text
- Risk: Невірне розпізнавання природної мови.
  Impact: подія може бути створена з неправильними датою або часом.
  Mitigation: показувати preview і вимагати підтвердження.

- Risk: Помилки транскрибації голосу.
  Impact: голосові події можуть бути зрозумілі неправильно.
  Mitigation: використовувати Whisper, зберігати текст для preview, просити підтвердження.

- Risk: Втрата нагадувань після рестарту бота.
  Impact: користувач не отримає reminder.
  Mitigation: зберігати події в SQLite і відновлювати active reminders при старті.

- Risk: Помилки timezone/DST.
  Impact: нагадування приходять не в той час.
  Mitigation: зберігати IANA timezone і працювати через UTC для розкладу.

- Risk: Надмірне ускладнення MVP.
  Impact: повільний старт і складна підтримка.
  Mitigation: Google Calendar, повторювані події і веб-панель залишити на пізніше.
```

## 9. Future Architecture Notes

```text
- Google Calendar integration як окремий модуль.
- Додаткова синхронізація подій між локальною базою і зовнішнім календарем.
- Повторювані події.
- Багатокористувацька модель з ширшими правами доступу.
- Web admin interface.
- Черга задач замість простого scheduler, якщо навантаження виросте.
```
