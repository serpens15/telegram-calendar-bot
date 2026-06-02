# SECURITY_PRIVACY

Цей файл описує безпеку, секрети й персональні дані.

## 1. Secrets

Секрети не можна зберігати в коді.

```text
- API keys:
- Tokens:
- Passwords:
- Database URLs:
```

Всі секрети мають бути в `.env` або в secret manager на production.

## 2. User Data

Які дані користувача зберігаються?

```text
- Data:
  Why needed:
  Storage:
  Retention:
```

## 3. What Not To Log

```text
- passwords;
- tokens;
- API keys;
- full personal data;
- payment data;
- private messages or sensitive content, якщо це не потрібно для debugging.
```

## 4. Access Control

```text
Who can access:
Admin actions:
User permissions:
```

## 5. Data Deletion

Як користувач може видалити свої дані?

```text
Method:
What gets deleted:
What remains in logs/backups:
```

## 6. Security Checklist

- [ ] `.env` не закомічений.
- [ ] Є `.env.example` без реальних секретів.
- [ ] Input валідовується.
- [ ] Помилки не показують секрети.
- [ ] Logs не містять sensitive data.
- [ ] Access control перевірено.

