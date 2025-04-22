import logging
import asyncio
from aiogram import executor

from core.settings import dp, bot, logger
from handlers.init import register_all_handlers
from core.callback_middleware import CallbackMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_startup(dp):
    """Set up bot on startup."""
    logging.info("Bot started!")
    
    try:
        # Логируем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"Bot connected as @{bot_info.username} (ID: {bot_info.id})")
        
        # Сначала регистрируем middleware (до регистрации обработчиков)
        logger.info("Setting up middleware...")
        dp.middleware.setup(CallbackMiddleware(bot, logger))
        
        # Затем регистрируем все обработчики
        logger.info("Registering handlers...")
        register_all_handlers(dp)
        
        # Установка команд бота
        logger.info("Setting up bot commands...")
        from handlers.start import setup_bot_commands
        await setup_bot_commands(bot)
        
        logger.info("Bot setup complete!")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        # Не делаем exit(1), чтобы увидеть полные логи
        raise

if __name__ == '__main__':
    try:
        logger.info("Starting bot polling...")
        # Явно указываем, что нужно принимать callback_query, это критически важно!
        executor.start_polling(
            dp, 
            on_startup=on_startup, 
            skip_updates=True, 
            allowed_updates=["message", "callback_query", "inline_query", "chosen_inline_result", "chat_member", "poll"]
        )
    except Exception as e:
        logger.critical(f"Critical error during polling: {str(e)}", exc_info=True)