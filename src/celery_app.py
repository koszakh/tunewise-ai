from celery import Celery
from src.config import settings

# Инициализируем Celery
celery = Celery(
    "tunewise_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Автоматически ищем задачи (tasks) в модулях нашего проекта
celery.autodiscover_tasks(["src"])

# Базовые настройки для стабильной работы
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
)