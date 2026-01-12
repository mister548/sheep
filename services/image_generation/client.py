"""Клиент для API генерации изображений."""
import logging
from io import BytesIO
from typing import Optional

import aiohttp
from aiohttp import FormData

from config.settings import settings

logger = logging.getLogger(__name__)


class ImageGenerationClient:
    """Клиент для работы с API генерации изображений."""

    def __init__(self):
        self.api_url = settings.GEN_API_URL
        self.api_key = settings.GEN_API_KEY
        self.callback_url = settings.CALLBACK_URL

    async def generate_image(
        self,
        image_bytes: bytes,
        prompt: str,
        model: str = "gpt-image-1",
        size: str = "1024x1024",
        quality: str = "low",
    ) -> Optional[dict]:
        """
        Отправить запрос на генерацию изображения.

        Args:
            image_bytes: Байты изображения
            prompt: Описание для генерации
            model: Модель генерации
            size: Размер изображения
            quality: Качество изображения

        Returns:
            Ответ API или None в случае ошибки
        """
        # Создаем FormData для multipart/form-data
        data = FormData()
        data.add_field("image[]", BytesIO(image_bytes), filename="input.png", content_type="image/png")
        data.add_field("prompt", prompt)
        data.add_field("model", model)
        data.add_field("quality", quality)
        data.add_field("size", size)
        data.add_field("n", "1")
        data.add_field("output_format", "png")
        data.add_field("background", "auto")
        data.add_field("moderation", "auto")
        data.add_field("callback_url", self.callback_url)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Генерация отправлена: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Ошибка API генерации: {response.status} - {error_text}"
                        )
                        return None
        except Exception as e:
            logger.error(f"Исключение при генерации изображения: {e}", exc_info=True)
            return None
