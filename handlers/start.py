"""Обработчики команды /start."""
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from config.settings import settings
from database.base import async_session_maker
from database.models import User

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    async with async_session_maker() as session:
        # Проверяем, существует ли пользователь
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            # Создаем нового пользователя с 10 стартовыми кредитами
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                credits=settings.START_CREDITS,
            )
            session.add(user)
            await session.commit()
            logger.info(f"Создан новый пользователь {user_id} с {settings.START_CREDITS} кредитами")
        else:
            # Обновляем информацию о пользователе, если изменилась
            user.username = username
            user.first_name = first_name
            await session.commit()

    welcome_text = f"""
👋 Привет, {first_name or 'друг'}!

🎨 Я бот для генерации изображений с помощью AI.

💳 У тебя сейчас: {user.credits} кредитов

📋 Доступные команды:
/photo - Сгенерировать изображение (стоимость: {settings.GENERATION_COST} кредита)
/buy_subscription - Купить кредиты
/status - Проверить баланс и статус

🚀 Начни с команды /photo для генерации изображения!
"""
    await message.answer(welcome_text)


