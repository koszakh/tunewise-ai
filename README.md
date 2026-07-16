# TuneWise AI 🎵

Асинхронное backend-приложение для управления музыкальной медиатекой.

Проект демонстрирует интеграцию современного веб-фреймворка, векторной базы данных для ИИ-поиска, фонового воркера для выполнения ресурсоемких задач, авторизации пользователей и интеграции с внешними API языковых моделей.

---

# 🚀 Основной функционал

### REST API
Полностью асинхронный API на **FastAPI** с валидацией данных через **Pydantic v2**.

### 🔐 JWT-аутентификация и безопасность
- регистрация и авторизация пользователей;
- безопасное хэширование паролей с использованием **bcrypt**;
- аутентификация по **JWT (HS256)**;
- защита эндпоинтов через асинхронные зависимости (**Dependencies**).

### 🧠 Семантический ИИ-поиск (pgvector)
Поиск треков выполняется **по смыслу**, а не по ключевым словам.

Например:

> *"грустная акустика для дождливой осени"*

### ⚙️ Фоновые задачи (Celery + RabbitMQ + Redis)
При создании нового плейлиста анализ треков и генерация креативного описания выполняются в фоне с помощью **Celery**, что сохраняет высокую отзывчивость основного API.

### 🤖 Интеграция с ИИ (OpenRouter API)
Генерация саммари плейлистов с использованием бесплатных LLM-моделей через единый интерфейс **OpenRouter**.

### 🛡️ Отказоустойчивость (Fallback Mode)
Если недоступны платные эмбеддинги OpenRouter, приложение автоматически переключается на локальный детерминированный алгоритм генерации векторов без остановки работы системы.

### ✅ Автоматическое тестирование
Изолированная тестовая среда на основе:

- pytest
- pytest-asyncio
- HTTPX
- отдельной тестовой базы данных
- eager mode для Celery

---

# 🛠 Стек технологий

| Категория | Технологии |
|-----------|------------|
| Язык | Python 3.11+ |
| Web Framework | FastAPI (Async/Await) |
| ORM | SQLAlchemy 2.0 + Alembic |
| База данных | PostgreSQL 16 + pgvector |
| Очередь задач | Celery + RabbitMQ |
| Backend результатов | Redis |
| Валидация | Pydantic v2 |
| Аутентификация | PyJWT + Passlib (bcrypt) |
| Тестирование | Pytest + pytest-asyncio + HTTPX |
| Контейнеризация | Docker + Docker Compose |

---

# 📁 Структура проекта

```text
tunewise-ai/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── src/
│   ├── services/
│   ├── celery_app.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   └── tasks.py
│
├── tests/
│   ├── conftest.py
│   └── test_auth.py
│
├── .env.example
├── alembic.ini
├── compose.local.yml
├── Dockerfile
├── generate_key.py
├── pytest.ini
└── requirements.txt
```

### Назначение директорий

| Путь | Описание |
|------|----------|
| `alembic/` | Миграции базы данных |
| `alembic/versions/` | Файлы миграций |
| `src/services/` | Работа с OpenRouter API и локальными сервисами |
| `src/celery_app.py` | Инициализация Celery |
| `src/config.py` | Конфигурация приложения |
| `src/database.py` | Настройка асинхронной БД |
| `src/dependencies.py` | Зависимости FastAPI |
| `src/main.py` | Точка входа приложения |
| `src/models.py` | SQLAlchemy-модели |
| `src/schemas.py` | Pydantic-схемы |
| `src/security.py` | JWT и хэширование паролей |
| `src/tasks.py` | Фоновые задачи Celery |
| `tests/` | Автоматические тесты |

---

# 🚀 Быстрый запуск

## 1. Подготовка окружения

Создайте файл `.env` и автоматически сгенерируйте безопасный `SECRET_KEY`.

Если установлен Python локально:

```bash
python generate_key.py
```

Или внутри Docker:

```bash
docker compose -f compose.local.yml run --rm api python generate_key.py
```

Скрипт:

- создаст `.env` из `.env.example`, если его еще нет;
- сгенерирует безопасный 64-символьный шестнадцатеричный ключ.

---

## 2. Сборка и запуск контейнеров

```bash
docker compose -f compose.local.yml up -d --build
```

---

## 3. Применение миграций

```bash
docker compose -f compose.local.yml run --rm api alembic upgrade head
```

После запуска приложение будет доступно по адресам:

- Swagger UI — http://localhost:8000/docs
- ReDoc — http://localhost:8000/redoc

---

# 🔑 Аутентификация

Приложение использует **OAuth2 Bearer Token**.

## Регистрация

```
POST /register
```

Принимает:

- username
- email
- password

Пароль автоматически хэшируется перед сохранением в БД.

---

## Авторизация

```
POST /login
```

Принимает стандартную форму OAuth2, проверяет пароль и возвращает JWT-токен.

---

## Защита эндпоинтов

Для ограничения доступа используется зависимость `get_current_user`.

```python
from fastapi import Depends

from src.dependencies import get_current_user
from src.models import User

@app.post("/playlists")
async def create_playlist(
    playlist_data: PlaylistCreate,
    current_user: User = Depends(get_current_user)
):
    return {
        "message": f"Плейлист создан пользователем {current_user.username}"
    }
```

---

# 🗃️ Работа с миграциями (Alembic)

## Создание новой миграции

```bash
docker compose -f compose.local.yml run --rm api \
    alembic revision --autogenerate -m "Add new field to model"
```

---

## Применение миграций

```bash
docker compose -f compose.local.yml run --rm api alembic upgrade head
```

---

## Откат на одну миграцию

```bash
docker compose -f compose.local.yml run --rm api alembic downgrade -1
```

---

# 🧪 Запуск тестов

Тестирование полностью изолировано от основной базы данных и использует отдельную БД `test_db`.

## Создание тестовой базы (один раз)

```bash
docker compose -f compose.local.yml exec db \
    psql -U postgres -c "CREATE DATABASE test_db;"
```

---

## Запуск тестов

```bash
docker compose -f compose.local.yml run --rm api pytest -v
```

Во время тестирования Celery автоматически переводится в режим

```python
task_always_eager = True
```

что позволяет выполнять фоновые задачи синхронно без обращения к RabbitMQ.