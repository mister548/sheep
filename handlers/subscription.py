"""Обработчики команды /buy_subscription."""
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.base import async_session_maker
from database.models import Payment as PaymentModel
from payments.yookassa_client import create_payment, SUBSCRIPTION_PLANS

logger = logging.getLogger(__name__)

router = Router(name="subscription")


@router.message(Command("buy_subscription"))
async def cmd_buy_subscription(message: Message):
    """Показать планы подписки."""
    plans_text = "💰 Доступные планы:\n\n"
    keyboard_buttons = []

    for amount, credits in SUBSCRIPTION_PLANS.items():
        plans_text += f"💳 {amount} ₽ — {credits} кредитов\n"
        keyboard_buttons.append(
            [InlineKeyboardButton(text=f"{amount} ₽ ({credits} кредитов)", callback_data=f"plan_{amount}")]
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(plans_text + "\nВыберите план:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("plan_"))
async def process_plan_selection(callback: CallbackQuery):
    """Обработка выбора плана."""
    amount = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    if amount not in SUBSCRIPTION_PLANS:
        await callback.answer("❌ Неверный план", show_alert=True)
        return

    try:
        # Создаем платеж
        payment_id, payment_url = create_payment(user_id, amount)

        # Сохраняем платеж в БД
        async with async_session_maker() as session:
            payment = PaymentModel(
                user_id=user_id,
                payment_id=payment_id,
                amount=str(amount),
                credits=SUBSCRIPTION_PLANS[amount],
                status="pending",
            )
            session.add(payment)
            await session.commit()

        # Отправляем ссылку на оплату
        await callback.message.edit_text(
            f"💳 Перейдите по ссылке для оплаты:\n\n"
            f"💰 Сумма: {amount} ₽\n"
            f"🎁 Кредитов: {SUBSCRIPTION_PLANS[amount]}\n\n"
            f"🔗 <a href='{payment_url}'>Оплатить</a>",
            parse_mode="HTML",
        )
        await callback.answer("Ссылка на оплату отправлена")

    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании платежа", show_alert=True)


