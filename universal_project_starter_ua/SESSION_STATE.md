# SESSION_STATE

Цей файл допомагає AI-асистенту не забувати, що було зроблено в попередніх сеансах.

AI має читати цей файл на початку кожного нового сеансу і пропонувати оновлення наприкінці кожної суттєвої задачі.

## Language Rule

```text
AI має відповідати українською мовою за замовчуванням.
Технічні терміни, назви файлів, команд, бібліотек, API та помилок можна залишати англійською.
Якщо користувач прямо попросив іншу мову, можна тимчасово перейти на неї.
```

## Current Project State

```text
Project name: Telegram Calendar Bot
Current phase: MVP implementation
Current goal: Побудувати Telegram-бота для створення подій і локальних нагадувань з текстових повідомлень.
Current task: Продовжити після timezone-aware event storage, не змінюючи напрям без підтвердження користувача.
Last updated: 2026-06-06
```

## What Has Been Done

```text
- Ініціалізовано Python-проєкт з aiogram, src-структурою, README, .env.example і pytest-тестами.
- Додано access control allow list для обмеження доступу до бота.
- Додано парсинг тексту подій.
- Додано confirmation flow для чернетки події перед збереженням.
- Додано groundwork для timezone service.
- Додано timezone-aware event storage.
- Наявні тести для access control, bot messages, event confirmation, handlers, parsing, repository, settings і timezone service.
```

## Important Decisions

```text
- Decision: MVP будується як Python Telegram bot на aiogram.
  Date:
  Reason: Найпростіший шлях для Telegram-first інтерфейсу.
  Related file: ARCHITECTURE.md

- Decision: SQLite використовується як MVP storage.
  Date:
  Reason: Простий локальний persistence без зайвої інфраструктури.
  Related file: ARCHITECTURE.md

- Decision: Google Calendar не входить у MVP.
  Date:
  Reason: Не ускладнювати першу робочу версію OAuth/API інтеграцією.
  Related file: PROJECT.md, BACKLOG.md
```

## Files Changed Recently

```text
- File: src/services/timezone_service.py
  What changed: Додано groundwork для роботи з часовими поясами.
  Why: Події й нагадування мають коректно працювати для користувацького timezone.

- File: src/db/*
  What changed: Додано timezone-aware event storage.
  Why: Потрібно зберігати локальний час, UTC час і timezone для подій.

- File: tests/*
  What changed: Додано/оновлено тести для поточних MVP-компонентів.
  Why: Захистити поведінку парсингу, storage, handlers, settings і timezone logic.
```

## Current Architecture / Direction

```text
MVP - один Python-сервіс Telegram-бота.

Основні шари:
- Telegram Bot Layer: aiogram handlers/messages/settings.
- Security Layer: allow list для доступу.
- Parsing Layer: розбір текстових подій.
- Service Layer: confirmation flow, timezone service.
- Storage Layer: SQLite repository/schema/models.
- Future Scheduler Layer: локальні reminders через APScheduler.

Поточний напрям: завершити вертикальний сценарій текстова подія -> confirmation -> SQLite storage -> список/видалення -> reminders.
```

## Current MVP Scope

```text
- Telegram bot через aiogram.
- Команди /start, /help, /timezone, /confirm, /cancel.
- Прийом текстових повідомлень з описом події.
- Парсинг дати, часу й назви події.
- Confirmation preview перед збереженням.
- SQLite persistence.
- Timezone-aware event storage.
- Access control allow list.
- Базові тести.
```

## Backlog Summary

```text
- Голосові повідомлення і Whisper transcription.
- Список майбутніх подій.
- Видалення подій.
- Scheduler/reminders.
- Google Calendar integration.
- Повторювані події.
- Premium/free limits і монетизація.
- Production deployment.
```

## Open Questions

```text
- Який наступний MVP-крок підтвердити: list/delete events чи scheduler reminders?
- Чи потрібна команда /add, якщо бот уже приймає звичайний текст?
- Який формат UX для списку і видалення подій: команди з id чи inline buttons?
- Коли додавати voice/Whisper: до reminders чи після стабілізації текстового сценарію?
```

## Known Risks

```text
- Risk: Timezone edge cases можуть ламати нагадування при DST або некоректному IANA timezone.
  Impact: Нагадування може прийти не в той час.
  Next action: Додати edge-case тести для timezone conversion.

- Risk: Scheduler ще не реалізований.
  Impact: Події можуть зберігатися, але не нагадувати користувачу.
  Next action: Спланувати окрему TASK для APScheduler і recovery after restart.

- Risk: Voice/Whisper може ускладнити MVP.
  Impact: Витрати, latency і залежність від зовнішнього API або локальної моделі.
  Next action: Тримати voice у backlog до завершення текстового сценарію.
```

## Tests / Validation

```text
Last tests run: Unknown in current session.
Result: Not verified in current session.
Known test gaps:
- Scheduler/reminders tests ще неактуальні, бо функція не реалізована.
- Потрібні edge-case тести для timezone і DST.
- Потрібні тести для list/delete events після реалізації.
```

## Next Recommended Step

```text
Перед кодом підтвердити наступну гілку реалізації:
1. List/delete events.
2. Scheduler/reminders.
3. Voice/Whisper transcription.

Рекомендація: спочатку list/delete events, потім scheduler/reminders, voice/Whisper залишити після стабілізації текстового MVP.
```

## End-of-Session Update Checklist

Наприкінці сеансу AI має запропонувати оновити:

- [ ] Current Project State
- [ ] What Has Been Done
- [ ] Important Decisions
- [ ] Files Changed Recently
- [ ] Current MVP Scope
- [ ] Backlog Summary
- [ ] Open Questions
- [ ] Known Risks
- [ ] Tests / Validation
- [ ] Next Recommended Step

