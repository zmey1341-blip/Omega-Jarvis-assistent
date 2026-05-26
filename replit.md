# Jarvis-Omega

Автономная AI-система с Telegram-ботом, каскадным роутингом провайдеров и веб-панелью управления (TMA).

## Run & Operate

- `cd jarvis-omega && pip install -r requirements.txt` — установить зависимости
- `cd jarvis-omega && python main.py` — запустить бота + TMA-сервер
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)
- **Python bot**: aiogram 3, FastAPI, httpx, python-dotenv

## Where things live

- `jarvis-omega/core/brain.py` — системные метрики, SharedState
- `jarvis-omega/core/fail_safe_routing.py` — каскадный роутер провайдеров AI
- `jarvis-omega/modules/admin_dashboard.py` — Telegram-бот (aiogram 3)
- `jarvis-omega/modules/tma_server.py` — FastAPI сервер для TMA
- `jarvis-omega/static/dashboard.html` — Telegram Mini App (Chart.js + TG Web App SDK)
- `jarvis-omega/main.py` — точка входа, asyncio.gather всех сервисов
- `jarvis-omega/.env.template` — шаблон переменных окружения

## Architecture decisions

- FailSafeRouter использует каскад: Gemini → OpenAI → Zhipu → OpenRouter → Ollama
- Exponential Backoff + Jitter (15–45 сек) при HTTP 429, логирование переключений
- brain — синглтон с asyncio.Lock для потокобезопасных метрик
- FastAPI и aiogram запускаются через asyncio.gather в одном event loop
- TMA-дашборд опрашивает /api/metrics каждые 10 секунд, рисует Chart.js графики

## Product

- Telegram-бот для администратора с командами `/status`, `/pause`, `/resume`
- Веб-панель (TMA) с графиками прибыли, статусом провайдеров и управлением воркерами
- Умный роутинг AI-запросов через 5 провайдеров с автоматическим failover

## User preferences

- Строго модульная структура Python-проекта
- Все секреты через .env (python-dotenv)

## Gotchas

- Скопируй `.env.template` в `.env` и заполни перед запуском
- `TELEGRAM_ADMIN_ID` — числовой Telegram ID администратора (не username)
- Ollama должна быть запущена локально на порту 11434 (или задай OLLAMA_BASE_URL)

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
