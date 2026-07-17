# src/tasks.py
import asyncio

from src.celery_app import celery
from src.database import SessionLocal  # Теперь этот импорт работает!
from src.models import Playlist
from src.services.ai_service import ai_service


@celery.task(name="generate_playlist_ai_summary_task")
def generate_playlist_ai_summary_task(playlist_id: int):
    # Celery-воркер работает синхронно, поэтому мы запускаем асинхронный цикл событий (Event Loop)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_generate_summary(playlist_id))


async def async_generate_summary(playlist_id: int):
    # Открываем асинхронную сессию к БД вручную с помощью нашей фабрики
    async with SessionLocal() as db:
        # Находим нужный плейлист
        playlist = await db.get(Playlist, playlist_id)
        if not playlist:
            print(f"Плейлист {playlist_id} не найден.")
            return

        # Подгружаем связанные треки плейлиста
        await db.refresh(playlist, ["tracks"])

        if not playlist.tracks:
            print(f"В плейлисте {playlist_id} нет треков для анализа.")
            return

        # Формируем описание треков для ИИ
        tracks_info = "\n".join(
            [f"- {t.artist} — {t.title} ({t.description})" for t in playlist.tracks]
        )

        try:
            # Запрашиваем генерацию у OpenRouter
            summary = await ai_service.generate_summary(playlist.title, tracks_info)

            # Сохраняем результат
            playlist.ai_summary = summary
            await db.commit()
            print(f"AI-обзор успешно сгенерирован для плейлиста ID {playlist_id}!")
        except Exception as e:
            await db.rollback()
            print(f"Ошибка при генерации обзора в Celery: {e}")
