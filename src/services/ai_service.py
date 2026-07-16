import logging
from openai import AsyncOpenAI, APIStatusError

from src.config import settings

# Используем логгер uvicorn для красивого вывода в консоль Docker
logger = logging.getLogger("uvicorn.error")


class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENAI_API_KEY,
            default_headers={
                "HTTP-Referer": "https://tunewise.ai",
                "X-Title": "TuneWise AI",
            }
        )

    def _get_mock_embedding(self, text: str) -> list[float]:
        """
        Умная локальная заглушка. Возвращает разные векторы размерности 1536
        в зависимости от ключевых слов в тексте.
        """
        text_lower = text.lower()
        vector = [0.0] * 1536

        if any(w in text_lower for w in ["груст", "дожд", "window", "rain", "acoustic", "акустик", "гитар"]):
            vector[0] = 1.0  # Ось грусти
        elif any(w in text_lower for w in ["неон", "drive", "поездк", "машин", "авто", "retro", "80"]):
            vector[1] = 1.0  # Ось поездки/ретро
        elif any(w in text_lower for w in ["спорт", "тренир", "techno", "агрессив", "adrenaline"]):
            vector[2] = 1.0  # Ось спорта/энергии
        else:
            vector[3] = 1.0  # Дефолтная ось

        return vector

    async def get_embedding(self, text: str) -> list[float]:
        """
        Получает эмбеддинг текста (размерность 1536) через OpenRouter.
        Если на балансе $0.00 (ошибка 402), автоматически переключается на заглушку.
        """
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "mock-key":
            return self._get_mock_embedding(text)

        try:
            response = await self.client.embeddings.create(
                model="openai/text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except APIStatusError as e:
            # Если OpenRouter вернул 402 (Insufficient credits / Нет средств)
            if e.status_code == 402:
                logger.warning(
                    "⚠️  [OpenRouter] Баланс $0.00 (ошибка 402). "
                    "Автоматически переключаемся на умную локальную заглушку для эмбеддингов!"
                )
                return self._get_mock_embedding(text)

            logger.error(f"Ошибка APIStatusError при получении эмбеддинга: {e}")
            raise e
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении эмбеддинга: {e}")
            raise e

    async def generate_summary(self, playlist_title: str, tracks_info: str) -> str:
        """
        Генерирует обзор плейлиста, используя ПОЛНОСТЬЮ БЕСПЛАТНУЮ модель на OpenRouter.
        """
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "mock-key":
            return "Это тестовый обзор плейлиста (Mock Mode)."

        prompt = (
            f"Создай креативный и вдохновляющий обзор для музыкального плейлиста '{playlist_title}'.\n"
            f"Вот список треков и их атмосфера:\n{tracks_info}\n"
            f"Объедини их общей концепцией, напиши кратко (3-4 предложения), стильно и на русском языке."
        )

        try:
            response = await self.client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {"role": "system", "content": "Ты музыкальный критик. Пишешь краткие, сочные и стильные обзоры."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка генерации саммари через OpenRouter: {e}")
            raise e


ai_service = AIService()