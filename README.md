# Telegram Calendar Bot

Text-first MVP for a Telegram bot that creates calendar events and local reminders from Telegram messages.

## Current MVP

- Telegram bot on `aiogram`.
- Onboarding with the `Старт` button, auto allow-list registration and user profile creation.
- Main menu with `Додати подію`, `Список подій`, `Видалити подію`.
- Text event creation from natural language or step-by-step FSM flow.
- Confirmation preview before saving an event.
- SQLite storage for users, events, reminders and allowed users.
- Per-user timezone storage and `/timezone` command.
- Future event listing and confirmed deletion.
- Local reminders through APScheduler: 15 minutes before the event and at the event time.
- Unit tests for settings, access control, parsing, handlers, storage, timezone and scheduler logic.

Voice/Whisper, Google Calendar, recurring events, web admin and monetization are backlog items, not part of the current text-first MVP.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

Fill `.env`:

```text
TELEGRAM_BOT_TOKEN=<your bot token>
DEFAULT_TIMEZONE=Europe/Kyiv
DEFAULT_REMINDER_MINUTES=15
DATABASE_PATH=telegram_calendar.sqlite3
ALLOWED_TELEGRAM_IDS=
```

Run from the project root:

```powershell
python src\main.py
```

The app reads `.env` from the project root automatically. SQLite storage is created automatically at `DATABASE_PATH`.

## Bot Commands

```text
/start - show the start screen
/help - show help
/whoami - show your Telegram ID
/timezone - show or change your timezone
/list - show future events
/delete - start event deletion
/confirm - confirm a pending legacy draft
/cancel - cancel the current action
```

Event creation is available from the `Додати подію` menu button and from plain text messages that contain an event description.

## Validation

```powershell
python -m unittest discover -s tests -q
```

Current expected result: `44 tests`, `OK`.

## Project Structure

```text
src/
  bot/          Telegram handlers, keyboards, messages and FSM states
  config/       Environment settings loader
  db/           SQLite schema, models and repository
  parsing/      Text event parsing
  scheduler/    APScheduler reminder delivery
  security/     Access control
  services/     Business services
tests/          Unit tests
```
