"""Клиент для работы с YooKassa."""
import logging
import uuid

from yookassa import Configuration, Payment

from config.settings import settings

logger = logging.getLogger(__name__)

# Конфигурация YooKassa
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

# Тарифы кредитов
SUBSCRIPTION_PLANS = {
    200: 10,   # 200 ₽ — 10 кредитов
    500: 25,   # 500 ₽ — 25 кредитов
    1000: 50,  # 1000 ₽ — 50 кредитов
}


def create_payment(user_id: int, amount: int) -> tuple[str, str]:
    """
    Создать платеж в YooKassa.

    Args:
        user_id: ID пользователя Telegram
        amount: Сумма платежа в рублях

    Returns:
        Tuple (payment_id, payment_url)
    """
    if amount not in SUBSCRIPTION_PLANS:
        raise ValueError(f"Неподдерживаемая сумма: {amount}. Доступны: {list(SUBSCRIPTION_PLANS.keys())}")

    credits = SUBSCRIPTION_PLANS[amount]
    return_url = f"https://t.me/{settings.BOT_USERNAME}?start=success"

    payment = Payment.create(
        {
            "amount": {"value": f"{amount}.00", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "description": f"Покупка {credits} кредитов для пользователя {user_id}",
            "metadata": {"user_id": user_id, "credits": credits, "amount": amount},
            "capture": True,
        },
        uuid.uuid4(),
    )

    payment_id = payment.id
    payment_url = payment.confirmation.confirmation_url

    logger.info(f"Создан платеж {payment_id} для пользователя {user_id} на сумму {amount}₽")

    return payment_id, payment_url


