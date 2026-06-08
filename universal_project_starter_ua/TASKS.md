# TASKS

Цей файл містить маленькі задачі для реалізації.

Правило: одна задача = одна відповідальність.

## Task Template

```text
Task ID:
Task Name:

Goal:

Files:

Dependencies:

Acceptance Criteria:
- [ ] ...
- [ ] ...
- [ ] ...

Risks:

Test Scenarios:
- Positive:
- Negative:
- Edge:

Status:
```

## Current Sprint / Current Phase

```text
Goal: Підняти MVP Telegram Calendar Bot локально і реалізувати перший вертикальний сценарій.
Focus: bootstrap, текстова подія, збереження в SQLite, базові reminders.
Do not work on: Google Calendar, веб-панель, повторювані події, монетизація.
```

## Tasks

### TASK-001: Project Bootstrap

Goal:

```text
Створити базову структуру Python-проєкту для Telegram Calendar Bot.
```

Files:

```text
pyproject.toml або requirements.txt
src/
README.md
.env.example
.gitignore
```

Dependencies:

```text
None
```

Acceptance Criteria:

- [ ] Є базова структура проєкту.
- [ ] Є приклад `.env.example`.
- [ ] `.env` не потрапляє в git.
- [ ] Зрозуміло, як запускати локально.

Risks:

```text
Неправильно обрана структура може ускладнити подальше розширення.
```

Test Scenarios:

- Positive: структура створена, конфігурація читається.
- Negative: відсутній `.env` дає зрозумілу помилку.
- Edge: повторний локальний запуск не ламає проєкт.

Status: Done

### TASK-013: Onboarding and Auto-Allowlist

Goal:

```text
Зробити стартовий onboarding з кнопкою Старт, автоматичним додаванням у allow list і створенням профілю користувача.
```

Files:

```text
src/bot/app.py
src/bot/handlers.py
src/security/access_control.py
src/db/repository.py
src/db/models.py
src/config/settings.py
src/services/onboarding_service.py
tests/test_handlers.py
tests/test_access_control.py
tests/test_repository.py
tests/test_onboarding_service.py
```

Dependencies:

```text
TASK-005
TASK-011
```

Acceptance Criteria:

- [ ] /start і кнопка Старт запускають onboarding навіть для нового користувача.
- [ ] Telegram ID додається в allow list автоматично при першому вході.
- [ ] Для користувача створюється профіль у БД.

Risks:

```text
Автоматичне додавання в allow list може розширити доступ ширше, ніж очікувалось.
```

Test Scenarios:

- Positive: новий користувач проходить реєстрацію.
- Negative: некоректний update не ламає onboarding.
- Edge: повторний старт не дублює allow list запис.

Status: Done

### TASK-014: Main Menu and Keyboard UX

Goal:

```text
Побудувати головне меню на ReplyKeyboard з великими кнопками для базових сценаріїв.
```

Files:

```text
src/bot/messages.py
src/bot/keyboards.py
src/bot/handlers.py
tests/test_bot_messages.py
tests/test_handlers.py
```

Dependencies:

```text
TASK-013
```

Acceptance Criteria:

- [ ] Після реєстрації показується головне меню.
- [ ] У меню є кнопки Додати подію, Список подій, Видалити подію.
- [ ] Підтвердження та видалення використовують InlineKeyboard.

Risks:

```text
Невдалий UX клавіатури може ускладнити навігацію в боті.
```

Test Scenarios:

- Positive: меню відображається коректно.
- Negative: невідомий текст не ламає flow.
- Edge: кнопка Старт завжди повертає до головного екрану.

Status: Done

### TASK-015: FSM Event Creation Flow

Goal:

```text
Реалізувати покрокове додавання події через FSM: назва, дата, час, підтвердження.
```

Files:

```text
src/bot/states.py
src/bot/handlers.py
src/services/event_service.py
src/services/event_confirmation.py
tests/test_handlers.py
tests/test_event_confirmation.py
```

Dependencies:

```text
TASK-014
TASK-006
TASK-011
```

Acceptance Criteria:

- [ ] Користувач послідовно вводить назву, дату і час.
- [ ] Після введення даних показується preview з кнопками підтвердження і скасування.
- [ ] Після підтвердження подія створюється і зберігається.

Risks:

```text
FSM може конфліктувати з іншими діалогами, якщо стани не очищати коректно.
```

Test Scenarios:

- Positive: подія створюється через покроковий flow.
- Negative: неправильна дата або час відхиляються.
- Edge: cancel скидає незавершену чернетку.

Status: Done

### TASK-016: Event Listing and Deletion Flow

Goal:

```text
Показувати майбутні події користувача та видаляти їх тільки після підтвердження.
```

Files:

```text
src/bot/handlers.py
src/services/event_confirmation.py
src/db/repository.py
tests/test_handlers.py
tests/test_event_confirmation.py
tests/test_repository.py
```

Dependencies:

```text
TASK-004
TASK-014
TASK-015
```

Acceptance Criteria:

- [ ] /list показує всі майбутні події.
- [ ] /delete або кнопка Видалити подію показує список доступних подій.
- [ ] Видалення відбувається лише після підтвердження.

Risks:

```text
Великі списки подій можуть потребувати додаткової пагінації у майбутньому.
```

Test Scenarios:

- Positive: список і видалення працюють для існуючих подій.
- Negative: неіснуюча подія не видаляється.
- Edge: порожній список показує дружнє повідомлення.

Status: Done

### TASK-017: Timezone Resolution and Manual Selection

Goal:

```text
Зберігати timezone окремо для кожного користувача і дозволяти ручний вибір, якщо авто-детекція недоступна.
```

Files:

```text
src/services/timezone_service.py
src/bot/handlers.py
src/db/repository.py
src/db/schema.py
tests/test_timezone_service.py
tests/test_handlers.py
```

Dependencies:

```text
TASK-011
TASK-013
```

Acceptance Criteria:

- [ ] Для користувача зберігається окремий timezone.
- [ ] Якщо авто-визначення недоступне, бот пропонує ручний вибір.
- [ ] Події та нагадування використовують timezone користувача.

Risks:

```text
Неправильно вибраний timezone вплине на час подій і reminder-ів.
```

Test Scenarios:

- Positive: timezone визначається або задається вручну.
- Negative: невідомий timezone відхиляється.
- Edge: повторна реєстрація не губить існуючий timezone.

Status: Done

### TASK-002: Bot Skeleton

Goal:

```text
Підняти мінімальний aiogram-бот з командами /start і /help.
```

Files:

```text
src/bot/*
src/main.py
```

Dependencies:

```text
TASK-001
```

Acceptance Criteria:

- [ ] Бот стартує локально.
- [ ] /start відповідає коротким описом.
- [ ] /help показує доступні команди.

Risks:

```text
Невірна обробка update може зламати базовий чат-флоу.
```

Test Scenarios:

- Positive: /start і /help працюють.
- Negative: невідома команда не падає.
- Edge: порожнє повідомлення обробляється без помилки.

Status: Done

### TASK-003: Configuration and Settings

Goal:

```text
Додати конфігурацію через environment variables і завантаження налаштувань.
```

Files:

```text
src/config/*
```

Dependencies:

```text
TASK-001
```

Acceptance Criteria:

- [ ] Токен бота читається з `.env`.
- [ ] Часовий пояс за замовчуванням задається через конфіг.
- [ ] Налаштування не хардкодяться в коді.

Risks:

```text
Некоректна конфігурація може зупинити запуск бота.
```

Test Scenarios:

- Positive: валідний `.env` запускає проєкт.
- Negative: відсутній токен дає чітку помилку.
- Edge: додаткові змінні не ламають старт.

Status: Done

### TASK-004: SQLite Schema and Repository Layer

Goal:

```text
Створити таблиці для users, events, reminders і allowed users.
```

Files:

```text
src/db/*
```

Dependencies:

```text
TASK-001
TASK-003
```

Acceptance Criteria:

- [ ] Структура БД описана.
- [ ] Є сховище для timezone користувача.
- [ ] Є сховище для подій і нагадувань.

Risks:

```text
Схема без timezone або reminder fields ускладнить майбутню логіку.
```

Test Scenarios:

- Positive: запис і читання події працюють.
- Negative: некоректні дані відхиляються.
- Edge: порожня база відкривається без помилки.

Status: Done

### TASK-005: Access Control for MVP

Goal:

```text
Обмежити доступ до бота списком дозволених Telegram ID.
```

Files:

```text
src/security/*
```

Dependencies:

```text
TASK-002
TASK-004
```

Acceptance Criteria:

- [ ] Дозволений користувач проходить перевірку.
- [ ] Недозволений користувач отримує відмову.
- [ ] Адмін-ID можна зберігати в конфігурації або БД.

Risks:

```text
Помилка в ACL може відкрити бот для небажаних користувачів.
```

Test Scenarios:

- Positive: allow-listed user користується ботом.
- Negative: сторонній користувач не має доступу.
- Edge: порожній список доступу блокує всі запити передбачувано.

Status: Done

### TASK-006: Text Event Parsing

Goal:

```text
Реалізувати парсинг текстових подій у простій природній мові.
```

Files:

```text
src/parsing/*
```

Dependencies:

```text
TASK-002
TASK-003
TASK-004
```

Acceptance Criteria:

- [ ] Підтримується формат на кшталт "завтра о 15:00 зустріч".
- [ ] Виділяються назва, дата і час.
- [ ] Невпевнені випадки йдуть у flow уточнення.

Risks:

```text
Надто агресивний парсинг може неправильно інтерпретувати подію.
```

Test Scenarios:

- Positive: типові формати розпізнаються.
- Negative: некоректна дата не проходить.
- Edge: текст без часу викликає уточнення.

Status: Done

### TASK-007: Event Confirmation Flow

Goal:

```text
Показати користувачу підсумок події і зберігати її тільки після підтвердження.
```

Files:

```text
src/bot/handlers/*
src/services/*
```

Dependencies:

```text
TASK-006
TASK-004
```

Acceptance Criteria:

- [ ] Є preview події.
- [ ] Підтвердження створює подію.
- [ ] Скасування не зберігає дані.

Risks:

```text
Погано організований state machine може ламати сценарій.
```

Test Scenarios:

- Positive: confirm зберігає подію.
- Negative: cancel очищає сценарій.
- Edge: повторне підтвердження не створює дубль.

Status: Done

### TASK-008: Voice Transcription Flow

Goal:

```text
Приймати voice message і перетворювати його в текст через Whisper.
```

Files:

```text
src/voice/*
src/services/*
```

Dependencies:

```text
TASK-002
TASK-006
```

Acceptance Criteria:

- [ ] Бот приймає voice message.
- [ ] Аудіо транскрибується в текст.
- [ ] Транскрибований текст проходить той самий сценарій, що й текст.

Risks:

```text
Помилки Whisper або завантаження файлу можуть зламати сценарій.
```

Test Scenarios:

- Positive: voice успішно розпізнається.
- Negative: пошкоджений audio дає чітку помилку.
- Edge: дуже коротке voice повідомлення обробляється без падіння.

Status: Not started

### TASK-009: Reminder Scheduler

Goal:

```text
Додати локальні нагадування через APScheduler.
```

Files:

```text
src/scheduler/*
src/services/*
```

Dependencies:

```text
TASK-004
TASK-007
```

Acceptance Criteria:

- [ ] Нагадування за 15 хвилин до події планується при створенні події.
- [ ] Нагадування в час події планується при створенні події.
- [ ] Бот надсилає нагадування у потрібний час.
- [ ] Після рестарту активні нагадування відновлюються з БД.

Risks:

```text
Задачі можуть загубитися при рестарті без механізму відновлення.
```

Test Scenarios:

- Positive: reminder відправляється вчасно.
- Negative: недоступний Telegram API логуватиметься.
- Edge: перезапуск не втрачає заплановані події.

Status: Done

### TASK-010: List and Delete Commands

Goal:

```text
Реалізувати /list і /delete для керування подіями.
```

Files:

```text
src/bot/handlers/*
src/services/*
```

Dependencies:

```text
TASK-004
TASK-007
```

Acceptance Criteria:

- [ ] /list показує найближчі події.
- [ ] /delete запускає видалення.
- [ ] Подія видаляється тільки після підтвердження.

Risks:

```text
Невдалий UX списку може ускладнити вибір події.
```

Test Scenarios:

- Positive: список повертається коректно.
- Negative: відсутні події обробляються без помилки.
- Edge: багато подій не ламають форматування.

Status: Done

### TASK-011: Timezone Handling

Goal:

```text
Додати збереження і зміну timezone користувача.
```

Files:

```text
src/bot/handlers/*
src/db/*
src/services/*
```

Dependencies:

```text
TASK-004
TASK-002
```

Acceptance Criteria:

- [ ] Часовий пояс зберігається для кожного користувача.
- [ ] /timezone змінює значення.
- [ ] Події та reminders працюють у правильному timezone.

Risks:

```text
Помилки timezone можуть зсунути нагадування на годину і більше.
```

Test Scenarios:

- Positive: timezone змінюється коректно.
- Negative: невідомий timezone відхиляється.
- Edge: DST переходи не ламають збереження часу.

Status: Done

### TASK-012: Testing and Documentation

Goal:

```text
Перевірити базові сценарії та оновити документацію під MVP.
```

Files:

```text
tests/*
README.md
PROJECT.md
REQUIREMENTS.md
ARCHITECTURE.md
TASKS.md
```

Dependencies:

```text
TASK-002 through TASK-011
```

Acceptance Criteria:

- [x] Є позитивні, негативні та edge-case тести.
- [x] Документація відповідає реальній реалізації.
- [x] Немає розбіжностей між планом і кодом для поточного text-first MVP.

Risks:

```text
Без тестів і документації MVP швидко деградує.
```

Test Scenarios:

- Positive: основний flow проходить.
- Negative: неправильний input не ламає бот.
- Edge: відновлення після рестарту перевірене.

Status: Done
