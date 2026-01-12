"""Главный файл приложения для запуска через python."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from database.base import init_db
from handlers import start, photo, subscription, status
from webhooks import gen_callback, yookassa

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Глобальные переменные для бота
bot: Bot = None
dp: Dispatcher = None
polling_task = None

# Создаем FastAPI приложение
app = FastAPI()

app.include_router(yookassa.router)
app.include_router(gen_callback.router)

# CORS (при необходимости)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    """Lifespan события для FastAPI."""
    global bot, dp, polling_task

    logger.info("Запуск приложения...")
    await init_db()
    logger.info("База данных инициализирована")

    # Создаем бота и диспетчер
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(photo.router)
    dp.include_router(subscription.router)
    dp.include_router(status.router)

    # Передаем bot instance в webhooks
    gen_callback.set_bot(bot)
    yookassa.set_bot(bot)


    logger.info("Запуск polling в фоновом режиме...")

    async def run_polling():
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            logger.error(f"Ошибка в polling: {e}", exc_info=True)

    polling_task = asyncio.create_task(run_polling())

    yield

    logger.info("Выключение приложения...")
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    if bot:
        await bot.session.close()


# Встраиваем lifespan в FastAPI
app.router.lifespan_context = lifespan_context


async def main():
    """Главная функция для запуска через python."""
    # Запуск FastAPI в фоне через uvicorn
    config = uvicorn.Config(app, host=settings.HOST, port=settings.PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    # Запуск event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено вручную")
