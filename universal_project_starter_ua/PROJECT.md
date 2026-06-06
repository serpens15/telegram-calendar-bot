# PROJECT

Це головний файл проєкту. Він пояснює, що ми будуємо, для кого, навіщо і коли можна вважати першу версію завершеною.

## 1. Project Name

Telegram Calendar

## 2. Project Summary

Telegram Calendar — це Telegram-бот для швидкого створення подій у календарі через звичайне повідомлення в чаті.

Користувач пише боту подію, дату і час, наприклад: `Зустріч завтра о 15:00`, а бот розпізнає інформацію, уточнює деталі за потреби, додає подію в календар і може нагадати про неї.

Перша версія створюється для особистого використання автора проєкту та тестування кількома користувачами.

## 3. Problem

Яку проблему вирішує проєкт?

```text
Користувачу незручно кожного разу вручну відкривати календар, створювати подію, вводити назву, дату, час і нагадування.

Проєкт вирішує проблему швидкого запису подій через Telegram: достатньо написати повідомлення боту, а він допоможе перетворити його на подію в календарі.

Основна ідея: зробити процес додавання події максимально простим, швидким і зрозумілим.
```

## 4. Target User

Хто буде користуватися продуктом?

```text
На першому етапі цільовий користувач — автор проєкту.

Додатково бот може використовуватися кількома тестовими користувачами, щоб перевірити логіку, зручність, помилки та реальні сценарії використання.

Потенційні користувачі в майбутньому:
- люди, які часто користуються Telegram;
- люди, які хочуть швидко записувати події;
- студенти, фрилансери, підприємці;
- користувачі, яким потрібні прості нагадування;
- люди, які не хочуть вручну відкривати Google Calendar або інший календар.
```

## 5. Value

Яку цінність отримує користувач?

```text
Користувач отримує простий спосіб швидко створювати події в календарі прямо з Telegram.

Основна цінність:
- економія часу;
- менше ручних дій;
- зручний формат: написав повідомлення — отримав подію в календарі;
- можливість не забувати важливі справи;
- простий інтерфейс без зайвих додатків;
- поступова автоматизація особистого планування.
```

## 6. MVP Scope

Мінімальна версія, яка вже дає користь.

```text
- Telegram-бот запускається і відповідає на базові команди.
- Користувач може написати текст події, дату і час.
- Бот може уточнити відсутні дані: дату, час або назву події.
- Бот зберігає подію в базі даних.
- Бот показує список найближчих подій.
- Бот може видалити або скасувати подію.
- Бот надсилає нагадування перед подією.
- Є базова інтеграція з календарем або підготовлена архітектура для Google Calendar.
- Є інструкція запуску проєкту локально.
```

## 7. Out of Scope

Що точно не входить у першу версію?

```text
- Масова публічна версія для великої кількості користувачів.
- Платна підписка або монетизація.
- Складна AI-обробка природної мови на першому етапі.
- Повноцінна CRM або таск-менеджер.
- Командні календарі для компаній.
- Складна веб-адмінка.
- Мобільний застосунок.
- Підтримка багатьох календарних сервісів одночасно.
- Складна система ролей і прав доступу.
- Деплой на платний сервер, якщо можна обійтися безкоштовними або локальними варіантами.
```

## 8. Success Criteria

Проєкт або етап вважається завершеним, коли:

- [ ] Core features працюють.
- [ ] Бот запускається локально без помилок.
- [ ] Користувач може створити подію через Telegram.
- [ ] Подія зберігається в базі даних.
- [ ] Користувач може переглянути список подій.
- [ ] Користувач може видалити подію.
- [ ] Працює базове нагадування про подію.
- [ ] Є базова документація.
- [ ] Є інструкція запуску.
- [ ] Є тестові сценарії.
- [ ] Немає Critical/High bugs.
- [ ] Секрети не зберігаються в коді.
- [ ] Архітектура пояснена.

## 9. Constraints

Обмеження проєкту:

```text
- Budget: мінімальний або безкоштовний бюджет. Проєкт створюється для навчання та з натхненням.
- Deadline: дедлайну немає.
- Preferred technologies:
  - Python;
  - aiogram для Telegram-бота;
  - SQLite для першої локальної бази даних;
  - APScheduler або інший простий планувальник для нагадувань;
  - python-dotenv для змінних середовища;
  - Google Calendar API на наступному етапі інтеграції;
  - Docker опціонально після стабільної локальної версії.
- Forbidden technologies:
  - платні сервіси без необхідності;
  - складні enterprise-рішення для першої версії;
  - зберігання токенів і секретів прямо в коді.
- Hosting limits:
  - спочатку локальний запуск на компʼютері;
  - потім можливий безкоштовний або бюджетний хостинг;
  - Docker додати пізніше для зручного запуску.
- Privacy requirements:
  - Telegram Bot Token зберігати тільки в .env;
  - Google API credentials не комітити в GitHub;
  - особисті події користувачів не показувати іншим користувачам;
  - не зберігати зайві персональні дані;
  - база даних має бути в .gitignore, якщо містить реальні події.
```

## 10. Current Status

```text
Status: Planning
Last updated: 2026-06-06
Current phase: заповнення PROJECT.md та формування першого технічного бачення
Next decision needed: підтвердити стек технологій і перейти до створення структури проєкту
```

## 11. Recommended Architecture

```text
Telegram User
    ↓
Telegram Bot
    ↓
Python application with aiogram
    ↓
Event parsing and validation layer
    ↓
SQLite database
    ↓
Reminder scheduler
    ↓
Telegram notification

Future integration:
Python application
    ↓
Google Calendar API
    ↓
Google Calendar event
```

## 12. Recommended First Tech Stack

```text
Language: Python
Telegram framework: aiogram
Database for MVP: SQLite
Config: python-dotenv
Reminders: APScheduler
Calendar integration: Google Calendar API, after local MVP
Hosting: local computer first, then free or low-cost hosting
Version control: Git + GitHub
Environment: VS Code + terminal
```

## 13. First Development Milestones

```text
Milestone 1: Project setup
- створити структуру папок;
- налаштувати Git;
- створити .env;
- підключити Telegram Bot Token;
- запустити бота локально.

Milestone 2: Basic bot commands
- /start;
- /help;
- /add;
- /list;
- /delete.

Milestone 3: Local event storage
- створити SQLite базу;
- зберігати події;
- показувати події користувача;
- видаляти події.

Milestone 4: Reminder system
- додати планувальник;
- перевіряти майбутні події;
- надсилати нагадування в Telegram.

Milestone 5: Calendar integration
- підключити Google Calendar API;
- створювати події в Google Calendar;
- обробляти помилки авторизації.

Milestone 6: Testing and cleanup
- перевірити основні сценарії;
- прибрати секрети з коду;
- оновити README.md;
- підготувати проєкт до деплою.
```

## 14. Notes for AI Assistant

```text
AI Assistant must not make big architectural decisions without asking the user first.

If several technical paths are possible, AI Assistant should explain options in simple words and ask which direction to choose.

If the task is large, AI Assistant should split it into small branches or milestones and ask which branch to work on next.

AI Assistant should explain every command and every file change because the user is learning.

AI Assistant should prefer simple, free and beginner-friendly solutions before suggesting complex production-level tools.
```
