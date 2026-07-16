from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from src.config import settings

# 1. Создаем асинхронный движок для работы с PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Поменяйте на True, если хотите видеть все SQL-запросы в консоли
)

# 2. Создаем асинхронную фабрику сессий (SessionLocal)
# Именно ее мы будем использовать в фоновых задачах Celery
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 3. Базовый класс для всех моделей базы данных
class Base(DeclarativeBase):
    pass

# 4. Зависимость (Dependency) для FastAPI эндпоинтов
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 5. Функция автоматической инициализации базы данных при старте
async def init_db():
    async with engine.begin() as conn:
        # Обязательно включаем расширение pgvector в PostgreSQL
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
