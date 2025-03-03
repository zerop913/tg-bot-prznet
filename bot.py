import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import register_admin_handlers, register_user_handlers
from middlewares import RoleMiddleware
from database import setup_database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_log.log")
    ]
)

# Проверка наличия директории для базы данных
os.makedirs("database", exist_ok=True)

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Настройка базы данных
    await setup_database()
    
    # Регистрация middleware
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())
    
    # Регистрация обработчиков
    register_admin_handlers(dp)
    register_user_handlers(dp)
    
    # Вывод информации о запуске бота
    bot_info = await bot.get_me()
    logging.info(f"Бот {bot_info.full_name} (@{bot_info.username}) успешно запущен!")
    
    # Удаление вебхука на всякий случай
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен!")
    except Exception as e:
        logging.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)