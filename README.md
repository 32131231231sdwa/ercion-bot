# Эрцион III Season — Telegram Bot

Бот для ролевой игры в мире Эрцион.

## Запуск

```bash
cd artifacts/ercion-bot
cp .env.example .env
# Заполни .env своими данными
python bot.py
```

## Обязательные переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | ID администраторов через запятую |
| `CHANNEL_USERNAME` | Username канала (без @) |

## Опциональные

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | PostgreSQL URL (по умолчанию SQLite) |
| `OPENAI_API_KEY` | Для боевого ИИ |
| `ADMIN_NOTIFY_USERNAME` | Username для уведомлений |

## Railway

Добавь переменные в разделе Variables и задеплой.
