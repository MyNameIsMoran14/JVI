# med-helper

Семейный медицинский помощник: бот и Mini App для отслеживания анализов и лечения одного пациента.

## Локальный запуск (этап 1)

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate       # Windows
pip install -e ".[dev]"

cp ../.env.example ../.env   # заполнить TELEGRAM_BOT_TOKEN и ALLOWED_TELEGRAM_IDS
```

Тесты (используют временную SQLite, Postgres не нужен):

```bash
pytest
```

Полный стек в Docker (Postgres, Redis, API, бот):

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Миграции применяются автоматически при старте `api` (`alembic upgrade head`). Чтобы применить их вручную:

```bash
cd backend
alembic upgrade head
```

Загрузить справочник показателей (`seeds/analytes.yaml`) в базу:

```bash
python -m app.extraction.seed
```

Бот без Docker (long polling, для разработки на ноутбуке):

```bash
cd backend
python -m app.bot.main
```
