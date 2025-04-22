import logging
import asyncio
from aiogram import executor

from core.settings import dp, bot, logger
from handlers.init import register_all_handlers
from core.callback_middleware import CallbackMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Обновление команд при старте бота
# async def on_startup(dp):
#     """Set up bot on startup."""
#     logging.info("Bot started!")
    
#     # Сначала регистрируем все обработчики
#     register_all_handlers(dp)
    
#     # Затем устанавливаем middleware
#     dp.middleware.setup(CallbackMiddleware(bot, logger))
    
#     # Установка команд бота
#     from handlers.start import setup_bot_commands
#     await setup_bot_commands(bot)

# if __name__ == '__main__':
#     # Явно указываем, что нужно принимать callback_query, это критически важно!
#     executor.start_polling(
#         dp, 
#         on_startup=on_startup, 
#         skip_updates=True, 
#         allowed_updates=["message", "callback_query", "inline_query", "chosen_inline_result", "chat_member", "poll"]
#     )
async def on_startup(dp):
    """Set up bot on startup."""
    logging.info("Bot started!")
    
    # Сначала регистрируем middleware (до регистрации обработчиков)
    dp.middleware.setup(CallbackMiddleware(bot, logger))
    
    # Затем регистрируем все обработчики
    register_all_handlers(dp)
    
    # Установка команд бота
    from handlers.start import setup_bot_commands
    await setup_bot_commands(bot)
    