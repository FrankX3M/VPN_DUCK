import logging
import asyncio
from aiogram import executor

from core.settings import dp, bot
from handlers.init import register_all_handlers

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Обновление команд при старте бота
async def on_startup(dp):
    """Set up bot on startup."""
    logging.info("Bot started!")
    
    # Регистрация всех обработчиков
    register_all_handlers(dp)
    
    # Установка команд бота
    from handlers.start import setup_bot_commands
    await setup_bot_commands(bot)

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)