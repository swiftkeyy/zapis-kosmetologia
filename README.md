# Telegram-бот для записи к мастеру по косметологии и массажу

Готовый бот на **Python + aiogram 3 + SQLite**.

## Возможности

- запись клиента через inline-кнопки;
- календарь с датами на ближайший месяц;
- выбор категории услуги, конкретной услуги и времени;
- хранение записей в SQLite;
- запрет на несколько активных записей у одного пользователя;
- автоматическое освобождение слота после отмены;
- обязательная проверка подписки на канал;
- кнопки **Прайсы** и **Портфолио**;
- админ-панель:
  - добавить рабочий день;
  - добавить слоты;
  - удалить слот;
  - добавить услугу;
  - удалить услугу из активного прайса;
  - посмотреть расписание на дату;
  - закрыть день полностью;
  - отменить запись клиента;
- уведомления админу и в канал;
- автонапоминание за 24 часа через APScheduler;
- восстановление напоминаний после перезапуска бота.

## Установка

```bash
python -m venv venv
```

### Windows
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / macOS
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Настройка

1. Скопируйте `.env.example` в `.env`
2. Заполните значения:

```env
BOT_TOKEN=...
ADMIN_ID=...
CHANNEL_ID=...
CHANNEL_LINK=...
DATABASE_PATH=bot.db
TIMEZONE=Europe/Moscow
```

## Важно

Чтобы проверка подписки работала корректно:

- бот должен быть добавлен в канал;
- бот должен иметь права, позволяющие видеть участников канала;
- для уведомлений в канал бот должен иметь право отправлять сообщения.

## Запуск

```bash
python bot.py
```

## Структура проекта

```text
kosmetology_bot/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── database/
│   ├── __init__.py
│   └── db.py
├── handlers/
│   ├── __init__.py
│   ├── admin.py
│   ├── booking.py
│   └── start.py
├── keyboards/
│   ├── __init__.py
│   ├── callbacks.py
│   └── inline.py
├── services/
│   ├── __init__.py
│   ├── scheduler.py
│   └── subscription.py
├── states/
│   ├── __init__.py
│   ├── admin.py
│   └── booking.py
└── utils/
    ├── __init__.py
    ├── default_data.py
    ├── helpers.py
    └── messages.py
```
