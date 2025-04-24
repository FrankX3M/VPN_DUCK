from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from core.settings import bot
from keyboards.keyboards import get_permanent_keyboard
from utils.bd import get_user_config

# Handler for /start command
async def send_welcome(message: types.Message):
    """Обрабатывает команду /start."""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Проверяем, есть ли у пользователя активная конфигурация
    config = await get_user_config(user_id)
    
    if config and config.get("active", False):
        # Получаем информацию о геолокации
        geo_name = config.get("geolocation_name", "Россия")  # По умолчанию Россия, если не указано
        
        welcome_text = (
            f"👋 Привет, {user_name}!\n\n"
            f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
            f"Ваша активная конфигурация:\n"
            f"▫️ Геолокация: {geo_name}\n\n"
            f"⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
            f"Сервис находится в тестовом режиме.\n\n"
            f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
            f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
            f"Выберите действие из меню ниже:"
        )
        
        # Создаем inline-клавиатуру для активной конфигурации
        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        inline_keyboard.add(
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        inline_keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        inline_keyboard.add(
            InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config")
        )
    else:
        welcome_text = (
            f"👋 Привет, {user_name}!\n\n"
            f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
            f"⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
            f"Сервис находится в тестовом режиме.\n\n"
            f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
            f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
            f"Выберите действие из меню ниже:"
        )
        
        # Создаем inline-клавиатуру для неактивной конфигурации
        inline_keyboard = InlineKeyboardMarkup(row_width=1)
        inline_keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config")
        )
    
    # Отправляем приветственное сообщение с inline-клавиатурой
    await message.reply(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline_keyboard
    )
    
    # Отправляем постоянную клавиатуру
    await message.answer(
        "Используйте меню ниже для быстрого доступа к командам:",
        reply_markup=get_permanent_keyboard()
    )
    """Обрабатывает команду /start."""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Проверяем, есть ли у пользователя активная конфигурация
    config = await get_user_config(user_id)
    
    if config and config.get("active", False):
        # Получаем информацию о геолокации
        geo_name = config.get("geolocation_name", "Россия")  # По умолчанию Россия, если не указано
        
        welcome_text = (
            f"👋 Привет, {user_name}!\n\n"
            f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
            f"Ваша активная конфигурация:\n"
            f"▫️ Геолокация: {geo_name}\n\n"
            f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
            f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
            f"Выберите действие из меню ниже:"
        )
        
        # Создаем inline-клавиатуру для активной конфигурации
        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        inline_keyboard.add(
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        inline_keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        inline_keyboard.add(
            InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config")
        )
    else:
        welcome_text = (
            f"👋 Привет, {user_name}!\n\n"
            f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
            f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
            f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
            f"Выберите действие из меню ниже:"
        )
        
        # Создаем inline-клавиатуру для неактивной конфигурации
        inline_keyboard = InlineKeyboardMarkup(row_width=1)
        inline_keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config")
        )
    
    # Отправляем приветственное сообщение с inline-клавиатурой
    await message.reply(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline_keyboard
    )
    
    # Отправляем постоянную клавиатуру
    await message.answer(
        "Используйте меню ниже для быстрого доступа к командам:",
        reply_markup=get_permanent_keyboard()
    )
    
# Function to set bot commands
async def setup_bot_commands(bot):
    """Устанавливает команды для меню бота."""
    commands = [
        types.BotCommand("start", "Начать работу с ботом"),
        types.BotCommand("create", "Создать конфигурацию"),
        types.BotCommand("extend", "Продлить конфигурацию"),
        types.BotCommand("status", "Проверить статус"),
        types.BotCommand("geolocation", "Изменить геолокацию"),  # Добавляем команду
        types.BotCommand("allconfigs", "Получить все конфигурации"),  # Добавляем команду
        types.BotCommand("payments", "История платежей"),
        types.BotCommand("stars_info", "Информация о Telegram Stars"),
        types.BotCommand("help", "Показать справку"),
        types.BotCommand("cancel", "Отменить текущую операцию")
    ]
    await bot.set_my_commands(commands)

def register_handlers_start(dp: Dispatcher):
    """Register handlers for bot start."""
    dp.register_message_handler(send_welcome, commands=['start'])