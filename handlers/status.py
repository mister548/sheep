"""Обработчики команды /status."""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.base import async_session_maker
from database.models import User

logger = logging.getLogger(__name__)

router = Router(name="status")


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Показать статус пользователя."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return

        status_text = f"""
📊 Твой статус:

💳 Кредиты: {user.credits}

{'✅ Активна' if user.credits > 0 else '⚠️ Нет кредитов'}
"""
        await message.answer(status_text)


