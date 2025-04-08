from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from core.settings import bot
from keyboards.keyboards import get_permanent_keyboard
from utils.bd import get_user_config

# Обработчик команды /start
async def send_welcome(message: types.Message):
    """Обрабатывает команду /start."""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    welcome_text = (
        f"👋 Привет, {user_name}!\n\n"
        f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
        f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN.\n\n"
        f"🔑 Для создания новой конфигурации используйте команду /create\n"
        f"📊 Для проверки статуса используйте команду /status\n"
        f"⏰ Для продления доступа используйте команду /extend\n"
        f"ℹ️ Для получения справки используйте команду /help"
    )
    
    # Проверяем, есть ли у пользователя активная конфигурация
    config = await get_user_config(user_id)
    
    keyboard = get_permanent_keyboard()
    
    await message.reply(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# Функция для установки команд бота
async def setup_bot_commands(bot):
    """Устанавливает команды для меню бота."""
    commands = [
        types.BotCommand("start", "Начать работу с ботом"),
        types.BotCommand("create", "Создать конфигурацию"),
        types.BotCommand("extend", "Продлить конфигурацию"),
        types.BotCommand("status", "Проверить статус"),
        types.BotCommand("payments", "История платежей"),
        types.BotCommand("stars_info", "Информация о Telegram Stars"),
        types.BotCommand("help", "Показать справку"),
        types.BotCommand("cancel", "Отменить текущую операцию")
    ]
    await bot.set_my_commands(commands)

def register_handlers_start(dp: Dispatcher):
    """Регистрирует обработчики для старта бота."""
    dp.register_message_handler(send_welcome, commands=['start'])