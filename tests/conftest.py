import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.database import Base, get_db
from src.main import app

# 1. Используем отдельную тестовую базу данных
# Заменяем имя базы в конце URL на "test_db"
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/tunewise", "/test_db")

# Создаем тестовый асинхронный движок
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Создает кастомный event loop для всего цикла тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    """Перед началом тестов создает все таблицы, а после тестов — удаляет"""
    async with test_engine.begin() as conn:
        # Убедимся, что расширение pgvector включено в тестовой БД
        from sqlalchemy import text

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # Создаем таблицы
        await conn.run_sync(Base.metadata.create_all)

    yield  # Здесь выполняются сами тесты

    async with test_engine.begin() as conn:
        # Очищаем базу после всех тестов
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Фикстура для работы с БД в тестах. Каждому тесту — чистая транзакция."""
    async with TestingSessionLocal() as session:
        yield session
        # Откатываем изменения, чтобы тесты не влияли друг на друга
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный клиент для отправки запросов к FastAPI"""

    # Переопределяем зависимость get_db в FastAPI на нашу тестовую сессию
    async def _override_get_db():
        try:
            yield db_session
        finally:
            await db_session.close()

    app.dependency_overrides[get_db] = _override_get_db

    # Используем ASGITransport для вызова эндпоинтов напрямую в коде без реальных сетевых запросов
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Сбрасываем переопределение зависимостей после теста
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def disable_celery_queues():
    """Заставляет Celery выполнять все задачи синхронно во время тестов"""
    from src.celery_app import celery

    celery.conf.update(task_always_eager=True)
