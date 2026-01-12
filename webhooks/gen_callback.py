"""Webhook для обработки callback от API генерации."""
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import async_session_maker
from database.models import GenerationTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gen", tags=["generation"])

# Глобальная переменная для бота (устанавливается из main.py)
_bot = None


def set_bot(bot_instance):
    """Установить bot instance."""
    global _bot
    _bot = bot_instance


@router.post("/callback")
async def gen_callback(request: Request):
    """Обработчик callback от API генерации изображений."""
    global _bot

    try:
        payload = await request.json()
        logger.info(f"GEN CALLBACK\n{json.dumps(payload, ensure_ascii=False, indent=2)}")

        request_id = str(payload.get("request_id"))
        status = payload.get("status")

        if not request_id:
            raise HTTPException(status_code=400, detail="Missing request_id")

        async with async_session_maker() as session:
            
            result = await session.execute(
                select(GenerationTask).where(GenerationTask.request_id == request_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                logger.error(f"Unknown request_id={request_id}")
                return {"ok": False, "error": "Unknown request_id"}
            
            # Проверяем статус
            if task.status in ("success", "failed"):
                logger.info(f"Request {request_id} уже обработан, игнорируем")
                return {"ok": True}

            chat_id = task.chat_id

            if status == "success":
                # Извлекаем URL изображения
                image_url = None

                if payload.get("result"):
                    result_data = payload["result"]
                    if isinstance(result_data, list) and len(result_data) > 0:
                        image_url = result_data[0]
                    elif isinstance(result_data, str):
                        image_url = result_data
                elif payload.get("full_response"):
                    full_response = payload["full_response"]
                    if isinstance(full_response, list) and len(full_response) > 0:
                        image_url = full_response[0].get("url")

                if image_url:
                    # Обновляем задачу
                    task.status = status
                    task.result_url = image_url
                    await session.commit()

                    # Отправляем изображение пользователю через бота
                    if _bot:
                        try:
                            await _bot.send_photo(
                                chat_id=chat_id,
                                photo=image_url,
                                caption="✅ Ваше изображение готово!",
                            )
                            logger.info(f"Изображение отправлено пользователю {chat_id}")
                        except Exception as e:
                            logger.error(f"Ошибка при отправке изображения: {e}", exc_info=True)
                    else:
                        logger.warning("Bot instance не установлен, изображение не отправлено")

                    return {"ok": True, "request_id": request_id}
                else:
                    logger.error(f"Не удалось извлечь image_url из payload: {payload}")
                    task.status = "failed"
                    await session.commit()
                    return {"ok": False, "error": "Image URL not found"}

            elif status == "failed":
                # Статус не success
                task.status = status
                await session.commit()
                logger.warning(f"Генерация завершилась со статусом: {status}")
                return {"ok": False, "status": status}
            else:
                task.status = status
                await session.commit()
                logger.warning(f"Генерация не завершилась статус: {status}")
                return {"ok": False, "status": status}

    except Exception as e:
        logger.error(f"Ошибка в gen_callback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
