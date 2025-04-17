import asyncio
import logging
from aiogram import Bot, Dispatcher
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

from handlers import register_handlers

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

settings = Settings()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# Регистрация обработчиков
register_handlers(dp)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 