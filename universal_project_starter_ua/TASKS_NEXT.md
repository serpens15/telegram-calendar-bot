# TASKS NEXT

## Current Sprint

```text
Goal: Покращити Telegram Calendar Bot під новий onboarding flow, головне меню на кнопках і покрокове створення подій.
Focus: стартова кнопка, автоматичне додавання в allow list, профіль користувача, FSM для подій, список і видалення.
Do not work on: Google Calendar, web-панель, повторювані події, монетизація.
```

## TASK-013: Onboarding and Auto-Allowlist

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

Status: Done

## TASK-014: Main Menu and Keyboard UX

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

Status: Done

## TASK-015: FSM Event Creation Flow

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

Status: Done

## TASK-016: Event Listing and Deletion Flow

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

Status: Done

## TASK-017: Timezone Resolution and Manual Selection

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

Status: Done
