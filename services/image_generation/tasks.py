"""Утилиты для работы с задачами генерации."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GenerationTask


async def create_generation_task(
    session: AsyncSession,
    user_id: int,
    chat_id: int,
    request_id: str,
    prompt: str,
    model: str = "gpt-image-1",
    size: str = "1024x1024",
) -> GenerationTask:
    """Создать задачу генерации."""
    task = GenerationTask(
        user_id=user_id,
        chat_id=chat_id,
        request_id=request_id,
        prompt=prompt,
        model=model,
        size=size,
        status="pending",
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task_by_request_id(
    session: AsyncSession, request_id: str
) -> Optional[GenerationTask]:
    """Получить задачу по request_id."""
    result = await session.execute(
        select(GenerationTask).where(GenerationTask.request_id == request_id)
    )
    return result.scalar_one_or_none()


async def update_task_status(
    session: AsyncSession,
    request_id: str,
    status: str,
    result_url: Optional[str] = None,
) -> Optional[GenerationTask]:
    """Обновить статус задачи."""
    task = await get_task_by_request_id(session, request_id)
    if task:
        task.status = status
        if result_url:
            task.result_url = result_url
        await session.commit()
        await session.refresh(task)
    return task


