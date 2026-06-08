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
Current task: TASK-018 natural language event creation with local-first parser and Gemini fallback виконано; далі local run verification з реальним `.env`.
Last updated: 2026-06-08
```

## What Has Been Done

```text
- Ініціалізовано Python-проєкт з aiogram, src-структурою, README, .env.example і pytest-тестами.
- Додано access control allow list для обмеження доступу до бота.
- Додано парсинг тексту подій.
- Додано confirmation flow для чернетки події перед збереженням.
- Додано groundwork для timezone service.
- Додано timezone-aware event storage.
- Додано onboarding зі стартовою кнопкою, автоматичним allow list і створенням профілю користувача.
- Додано головне меню на ReplyKeyboard і inline-кнопки для підтвердження/видалення.
- Додано FSM flow створення події: назва -> дата -> час -> підтвердження.
- Додано список майбутніх подій і видалення події після підтвердження.
- Додано локальний scheduler reminders через APScheduler: відновлення pending reminders при старті та планування reminders після створення нової події.
- Для кожної нової події створюються два нагадування: за 15 хвилин до події та рівно в час події.
- Наявні тести для access control, bot messages, onboarding, event confirmation, handlers, parsing, repository, reminder scheduler, settings і timezone service.
- Оновлено README і проєктні документи під реальний text-first MVP; voice/Whisper явно залишено в backlog / next stage.
- TASK-012 Testing and Documentation позначено як Done.
- Додано edge-case тести для Europe/Kyiv навколо старту й завершення DST у timezone conversion та створенні event reminders.
- Додано ParserService з local-first parsing і Gemini fallback тільки при incomplete/low-confidence result.
- Розширено локальний parser: confidence/source, "нагадати/нагадай" prefix cleanup, "N числа", приклади типу "Нагадати купити молоко сьогодні о 18:00".
- Оновлено confirmation UI: inline-кнопки Підтвердити, Змінити дату, Змінити час, Скасувати; для зміни часу додано компактний pseudo-slider.
- Після підтвердження або скасування create/delete операцій бот видаляє callback-повідомлення з inline-кнопками або прибирає клавіатуру fallback-ом, щоб користувач не дублював операції старими кнопками.
- Додано опційний GeminiService через `GEMINI_API_KEY`/`GEMINI_MODEL`; без ключа зовнішні запити не виконуються.
- Додано GoogleCalendarService stub і NotificationService wrapper як архітектурні точки розширення без реальної Google Calendar інтеграції.
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
  What changed: Додано/оновлено тести для поточних MVP-компонентів; додано timezone/DST edge-case тести для Europe/Kyiv; останній запуск `python -m unittest discover -s tests -q` пройшов.
  Why: Захистити поведінку onboarding, меню, FSM creation, list/delete, scheduler, storage, handlers, settings, timezone conversion і reminder UTC scheduling.

- File: src/bot/app.py, src/bot/handlers.py, src/bot/keyboards.py, src/bot/states.py, src/services/event_service.py, src/services/onboarding_service.py, src/scheduler/reminder_scheduler.py
  What changed: Додано onboarding, keyboard UX, FSM creation, list/delete і scheduler wiring; виправлено confirm callback user id; додано другий reminder на час події; оновлено natural-language confirmation flow і time pseudo-slider; після фінальних callback-операцій старі inline-повідомлення прибираються.
  Why: Завершити текстовий вертикальний сценарій до локальних reminders, зменшити кількість ручних дій користувача і не дозволяти дублювати операції старими кнопками.

- File: src/parsing/*, src/services/ai/*
  What changed: Додано ParserService local-first orchestration, confidence/source у ParsedEventDraft, Gemini fallback adapter і розширення локального parser.
  Why: Користувач має створювати подію одним повідомленням; Gemini має викликатися тільки якщо локальний parser не впорався.

- File: README.md, universal_project_starter_ua/PROJECT.md, universal_project_starter_ua/REQUIREMENTS.md, universal_project_starter_ua/ARCHITECTURE.md, universal_project_starter_ua/TASKS.md, universal_project_starter_ua/SESSION_STATE.md
  What changed: Документацію вирівняно з фактичною text-first MVP реалізацією; voice/Whisper позначено як backlog / next stage; TASK-012 позначено Done.
  Why: Прибрати розбіжності між планом, документацією і кодом.
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
- Scheduler Layer: локальні reminders через APScheduler.

Поточний напрям: стабілізувати текстовий MVP, перевірити локальний запуск бота і після підтвердження перейти до voice/Whisper або cleanup/documentation.
```

## Current MVP Scope

```text
- Telegram bot через aiogram.
- Команди /start, /help, /timezone, /confirm, /cancel, /list, /delete.
- Onboarding зі стартовою кнопкою, автоматичним allow list і профілем користувача.
- Головне меню з кнопками Додати подію, Список подій, Видалити подію.
- Прийом текстових повідомлень з описом події.
- Парсинг дати, часу й назви події.
- Confirmation preview перед збереженням.
- SQLite persistence.
- Timezone-aware event storage.
- Список майбутніх подій.
- Видалення подій після підтвердження.
- Локальні reminders через APScheduler: за 15 хвилин до події та в час події.
- Access control allow list.
- Базові тести.
```

## Backlog Summary

```text
- Голосові повідомлення і Whisper transcription.
- Покращений вибір дати/часу через Telegram Web App з календарем і time picker; inline pseudo-slider для часу вже додано.
- Google Calendar integration.
- Повторювані події.
- Premium/free limits і монетизація.
- Production deployment.
```

## Open Questions

```text
- Який наступний MVP-крок підтвердити: voice/Whisper transcription чи cleanup/documentation/local run verification?
- Чи потрібна команда /add, якщо бот уже приймає звичайний текст?
- Чи потрібно додати явну команду /add поряд із кнопкою Додати подію?
- Чи потрібно після підтвердження події показувати коротший/інший summary для користувача?
- Чи варто замінити прості кнопки вибору дати/часу на псевдо-бігунок inline-кнопками або окремий Telegram Web App date/time picker?
```

## Known Risks

```text
- Risk: Timezone edge cases можуть ламати нагадування при DST або некоректному IANA timezone.
  Impact: Нагадування може прийти не в той час.
  Next action: Частково закрито тестами для Europe/Kyiv DST start/end; за потреби додати покриття для інших timezone або неоднозначних локальних годин.

- Risk: Scheduler реалізований, але не перевірений на реальному Telegram bot runtime у цій сесії.
  Impact: Unit-тести проходять, але інтеграційні проблеми запуску/доставки можуть проявитися лише локально з реальним токеном.
  Next action: Виконати local run verification з валідним `.env` і тестовою подією.

- Risk: Voice/Whisper може ускладнити MVP.
  Impact: Витрати, latency і залежність від зовнішнього API або локальної моделі.
  Next action: Тримати voice у backlog до завершення текстового сценарію.

- Risk: Gemini fallback може повертати некоректний JSON або бути недоступним.
  Impact: Неоднозначні повідомлення можуть не розпізнатися через AI fallback.
  Next action: Local parser залишається основним шляхом; Gemini відповідь валідовується, а без `GEMINI_API_KEY` fallback вимкнений.
```

## Tests / Validation

```text
Last tests run: 2026-06-08, `python -m unittest discover -s tests -q`.
Result: 69 tests, OK.
Known test gaps:
- `pytest` не встановлений у поточному Python, тому перевірка виконувалась через unittest.
- Timezone/DST edge-case тести додано для Europe/Kyiv start/end; не покрито всі підтримувані timezone і неоднозначні локальні години під час fall-back.
- Natural-language parser/fallback тести додано для local-first behavior, Gemini fallback routing, "нагадати" prefix і "N числа".
- Потрібна інтеграційна перевірка доставки reminders у реальному Telegram runtime. `python src\main.py` поза sandbox не впав одразу і працював до timeout, що схоже на нормальний long-running polling процес; доставку тестового reminder ще потрібно перевірити вручну з ботом.
```

## Next Recommended Step

```text
Перед кодом підтвердити наступну гілку реалізації:
1. Local run verification з реальним `.env` і тестовою подією.
2. Перевірити Gemini fallback з реальним `GEMINI_API_KEY` на неоднозначному тексті.
3. Voice/Whisper transcription.

Рекомендація: спочатку local run verification, потім voice/Whisper.
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

