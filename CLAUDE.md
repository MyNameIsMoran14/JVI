# med-helper

Семейный медицинский помощник для одного пациента: у папы множественная миелома. Мама загружает его анализы, видит динамику показателей, историю визитов к гематологу и разговаривает с AI-помощником, который помнит всю историю болезни.

Полная спецификация: `docs/PROJECT_SPEC.md`. Прочитай её перед тем, как проектировать новый модуль.

## Принятые решения (не пересматривать без запроса)

- **Интерфейс:** Telegram-бот + Telegram Mini App. Отдельного сайта со своим логином нет; тот же фронт при желании открывается в браузере.
- **LLM:** модели OpenAI через российского посредника (ProxyAPI или AITUNNEL) с официальным `openai` SDK. Провайдер меняется через `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` в `.env`. Код провайдер-агностичный: весь доступ к LLM идёт через `app/llm/`.
- **Сервер:** один VPS. Timeweb Cloud (оплата в рублях), для OpenRouter — европейская локация (Амстердам/Франкфурт), тариф от 2 ГБ RAM. На первых этапах бот работает в режиме long polling локально.
- **Архитектура:** модульный монолит на FastAPI + воркер arq. Микросервисы не нужны.

## Стек

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, aiogram 3, arq + Redis, PostgreSQL 16 (+ pgvector в v2), pdfplumber, pdf2image, rapidfuzz.
- Frontend: React + TypeScript + Vite, Zustand, TanStack Query, React Router, Mantine или shadcn/ui, Recharts, `@telegram-apps/sdk` (или `window.Telegram.WebApp`), типы из OpenAPI через `openapi-typescript`.
- Infra: Docker Compose (caddy, api, worker, postgres, redis), Caddy (авто-HTTPS), GitHub Actions → GHCR → деплой по SSH.

## Структура репозитория

```
med-helper/
  backend/
    app/core/        config, db, security
    app/auth/        проверка Telegram initData → JWT, белый список telegram_id
    app/documents/   загрузка и хранение файлов
    app/extraction/  распознавание анализов, нормализация названий и единиц
    app/labs/        показатели, ряды для графиков, тренды
    app/visits/ app/treatment/ app/patient/
    app/assistant/   сборка контекста, промпт, красные флаги, сводки
    app/bot/         aiogram-хендлеры (вызывают те же сервисы, что и REST)
    app/llm/         единый адаптер LLM
    alembic/  tests/  seeds/analytes.yaml  prompts/assistant.md
  frontend/src/{pages,components,api,store}/
  deploy/ docker-compose.yml, Caddyfile, backup.sh
  docs/PROJECT_SPEC.md
```

## Правила, которые нельзя нарушать

1. **Цифры считает код, не LLM.** Тренды, проценты изменения и флаги считаются в Python; модель получает готовые строки («κ/λ: 12,4 → 8,1 (−35% за 2 мес.)»).
2. **Распознанные анализы не попадают в `lab_results` без подтверждения** пользователем (статус `needs_review` → `confirmed`).
3. **В LLM не отправляются ФИО и дата рождения.** В контексте чата пишется только «пациент, мужчина, N лет». Шапку бланка с ФИО обрезаем до отправки в vision-модель.
4. **Помощник не назначает и не меняет лечение.** При красных флагах первым идёт фиксированный текст из шаблона (не сгенерированный), затем ответ модели.
5. **Референсы берутся с бланка лаборатории**, в коде не захардкожены. Пороги красных флагов задаются в конфиге и согласуются с лечащим гематологом.
6. **Секреты** хранятся только в `.env` и GitHub Secrets. Репозиторий приватный. Postgres и Redis наружу не открыты.
7. **Доступ** есть только с telegram_id из белого списка; остальных бот игнорирует.

## Стиль кода

- Типизация везде (mypy/pyright strict для backend, `strict` в tsconfig).
- Сервисный слой отдельно от роутеров; бот и REST вызывают одни и те же сервисы.
- Тесты pytest для extraction, нормализации единиц, трендов и красных флагов обязательны. Фикстуры — обезличенные бланки.
- Интерфейс и все тексты для пользователя на русском, крупный шрифт, минимум полей ввода.

## Текущий этап

Смотри раздел «План работ» в `docs/PROJECT_SPEC.md`. Начинаем с этапа 1 (фундамент).
