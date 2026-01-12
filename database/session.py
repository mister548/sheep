"""Сессии базы данных для dependency injection."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from database.base import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


