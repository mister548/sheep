"""Обработчики команды /photo."""
import logging
from io import BytesIO

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import settings
from database.base import async_session_maker
from database.models import User
from services.image_generation.client import ImageGenerationClient
from services.image_generation.tasks import create_generation_task
from states.image_generation import ImageGenerationStates

logger = logging.getLogger(__name__)

router = Router(name="photo")

# Хранение временных данных для FSM
user_data_storage = {}


@router.message(Command("photo"))
async def cmd_photo(message: Message, state: FSMContext):
    """Начало процесса генерации изображения."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return

        if user.credits < settings.GENERATION_COST:
            await message.answer(
                f"❌ Недостаточно кредитов. Нужно {settings.GENERATION_COST}, у вас {user.credits}.\n"
                f"Используйте /buy_subscription для покупки кредитов."
            )
            return

    await state.set_state(ImageGenerationStates.waiting_image)
    await message.answer(
        "📸 Отправьте изображение для обработки.\n\n"
        "После этого вы сможете добавить описание (prompt)."
    )


@router.message(ImageGenerationStates.waiting_image, F.photo)
async def process_image(message: Message, state: FSMContext):
    """Обработка полученного изображения."""
    user_id = message.from_user.id

    # Скачиваем изображение
    photo = message.photo[-1]  # Берем самое большое разрешение
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)

    # Сохраняем в состояние
    await state.update_data(image_bytes=image_bytes.read())

    # Переходим к следующему состоянию
    await state.set_state(ImageGenerationStates.waiting_prompt)
    await message.answer(
        "✅ Изображение получено!\n\n"
        "📝 Теперь отправьте описание (prompt) для генерации изображения."
    )


@router.message(ImageGenerationStates.waiting_image)
async def process_image_invalid(message: Message):
    """Обработка некорректного сообщения в состоянии ожидания изображения."""
    await message.answer("❌ Пожалуйста, отправьте изображение (фото).")


@router.message(ImageGenerationStates.waiting_prompt, F.text)
async def process_prompt(message: Message, state: FSMContext):
    """Обработка prompt и запрос подтверждения."""
    prompt = message.text
    user_id = message.from_user.id

    # Получаем данные из состояния
    data = await state.get_data()
    image_bytes = data.get("image_bytes")

    if not image_bytes:
        await message.answer("❌ Ошибка: изображение не найдено. Начните заново с /photo")
        await state.clear()
        return

    # Сохраняем prompt
    await state.update_data(prompt=prompt)

    # Создаем клавиатуру для выбора параметров (по желанию)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить (1024x1024)", callback_data="confirm_1024x1024"
                ),
                InlineKeyboardButton(
                    text="✅ Подтвердить (1536x1024)", callback_data="confirm_1536x1024"
                ),
            ]
        ]
    )

    await state.set_state(ImageGenerationStates.waiting_confirmation)
    await message.answer(
        f"📋 Проверьте параметры:\n\n"
        f"📝 Prompt: {prompt}\n"
        f"🎨 Модель: gpt-image-1\n"
        f"💳 Стоимость: {settings.GENERATION_COST} кредита(ов)\n\n"
        f"Выберите размер изображения:",
        reply_markup=keyboard,
    )


@router.message(ImageGenerationStates.waiting_prompt)
async def process_prompt_invalid(message: Message):
    """Обработка некорректного сообщения в состоянии ожидания prompt."""
    await message.answer("❌ Пожалуйста, отправьте текстовое описание (prompt).")


@router.callback_query(ImageGenerationStates.waiting_confirmation, F.data.startswith("confirm_"))
async def confirm_generation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и запуск генерации."""
    user_id = callback.from_user.id
    
    if callback.data == "confirm_1024x1024":
        size = "1024x1024" 
    elif callback.data == "confirm_1536x1024":
        size = "1536x1024"
    else:
        await callback.answer(
            f"❌ Некорректный размер картинки",
            show_alert=True,
        )
        await state.clear()
        return

    # Получаем данные из состояния
    data = await state.get_data()
    image_bytes = data.get("image_bytes")
    prompt = data.get("prompt")

    if not image_bytes or not prompt:
        await callback.answer("❌ Ошибка: данные не найдены")
        await state.clear()
        return

    async with async_session_maker() as session:
        from sqlalchemy import select

        # Проверяем кредиты и списываем
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None or user.credits < settings.GENERATION_COST:
            await callback.answer(
                f"❌ Недостаточно кредитов. Нужно {settings.GENERATION_COST}",
                show_alert=True,
            )
            await state.clear()
            return

        # Списываем кредиты
        user.credits -= settings.GENERATION_COST
        await session.commit()

        # Запускаем генерацию
        client = ImageGenerationClient()
        response = await client.generate_image(
            image_bytes=BytesIO(image_bytes).read(),
            prompt=prompt,
            model="gpt-image-1",
            size=size,
        )

        if response and response.get("request_id"):
            request_id = str(response["request_id"])
            
            # Создаем задачу генерации
            from database.models import GenerationTask

            task = await create_generation_task(
                session=session,
                user_id=user_id,
                chat_id=callback.message.chat.id,
                request_id=request_id,
                prompt=prompt,
                model="gpt-image-1",
                size=size,
            )

            await callback.message.edit_text(
                f"⏳ Генерация запущена!\n\n"
                f"💳 Списано: {settings.GENERATION_COST} кредита(ов)\n"
                f"💰 Осталось кредитов: {user.credits}\n\n"
                f"🔄 Ожидайте результат..."
            )
            await callback.answer("Генерация запущена!")
        else:
            # Возвращаем кредиты при ошибке
            user.credits += settings.GENERATION_COST
            await session.commit()

            await callback.message.edit_text(
                "❌ Ошибка при запуске генерации. Кредиты возвращены. Попробуйте позже."
            )
            await callback.answer("Ошибка генерации", show_alert=True)

    await state.clear()


