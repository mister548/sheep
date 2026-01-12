"""Состояния FSM для генерации изображений."""
from aiogram.fsm.state import State, StatesGroup


class ImageGenerationStates(StatesGroup):
    """Состояния процесса генерации изображения."""

    waiting_image = State()  # Ожидание изображения
    waiting_prompt = State()  # Ожидание описания (prompt)
    waiting_confirmation = State()  # Ожидание подтверждения


