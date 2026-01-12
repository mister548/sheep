"""Webhook для обработки платежей YooKassa."""
import logging

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import async_session_maker
from database.models import Payment as PaymentModel, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/yookassa", tags=["payments"])

# Глобальная переменная для бота (устанавливается из main.py)
_bot = None


def set_bot(bot_instance):
    """Установить bot instance."""
    global _bot
    _bot = bot_instance


@router.post("/webhook")
async def yookassa_webhook(request: Request):
    """Обработчик webhook от YooKassa."""
    global _bot

    try:
        data = await request.json()
        logger.info(f"YooKassa webhook received: {data}")

        event = data.get("event")
        if event != "payment.succeeded":
            logger.info(f"Ignoring event: {event}")
            return {"ok": True}

        payment_object = data.get("object", {})
        metadata = payment_object.get("metadata", {})
        user_id = int(metadata.get("user_id"))
        payment_id = payment_object.get("id")
        credits = int(metadata.get("credits", 0))

        if not user_id or not payment_id:
            logger.error(f"Missing user_id or payment_id in webhook: {data}")
            raise HTTPException(status_code=400, detail="Missing user_id or payment_id")

        async with async_session_maker() as db_session:
            # Проверяем, не обработан ли уже этот платеж
            result = await db_session.execute(
                select(PaymentModel).where(PaymentModel.payment_id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                if payment.status == "succeeded":
                    logger.info(f"Payment {payment_id} already processed")
                    return {"ok": True}
                payment.status = "succeeded"
            else:
                logger.error(f"Received unknown payment {payment_id} for user {user_id}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Payment {payment_id} does not exist in database"
                )

            # Начисляем кредиты пользователю
            user_result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if user:
                user.credits += credits
            else:
                # Создаем пользователя, если его нет (маловероятно, но на всякий случай)
                if _bot:
                    try:
                        tg_user = await _bot.get_chat(user_id)
                        user = User(
                            id=user_id,
                            username=tg_user.username,
                            first_name=tg_user.first_name,
                            credits=credits,
                        )
                        db_session.add(user)
                    except Exception as e:
                        logger.error(f"Не удалось получить информацию о пользователе: {e}")
                        user = User(id=user_id, credits=credits)
                        db_session.add(user)
                else:
                    user = User(id=user_id, credits=credits)
                    db_session.add(user)

            await db_session.commit()

            # Отправляем сообщение пользователю
            if _bot:
                try:
                    await _bot.send_message(
                        user_id,
                        f"✅ Оплата прошла! Вам начислено {credits} кредитов.\n\n"
                        f"💳 Текущий баланс: {user.credits} кредитов",
                    )
                    logger.info(f"Уведомление об оплате отправлено пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления об оплате: {e}", exc_info=True)
            else:
                logger.warning("Bot instance не установлен, уведомление не отправлено")

            return {
                "ok": True,
                "user_id": user_id,
                "credits": credits,
            }

    except Exception as e:
        logger.error(f"Ошибка в yookassa_webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
