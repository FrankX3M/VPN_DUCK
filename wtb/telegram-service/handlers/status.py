from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from datetime import datetime

from core.settings import bot, logger
from keyboards.keyboards import get_active_config_keyboard, get_create_config_keyboard
from utils.bd import get_user_config

# Обработчик для команды /status
async def get_config_status(message: types.Message):
    """Получение статуса конфигурации пользователя."""
    user_id = message.from_user.id
    
    try:
        # Запрашиваем данные о конфигурации
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            # Парсим и форматируем данные о конфигурации
            created_at = datetime.fromisoformat(config.get("created_at")).strftime("%d.%m.%Y %H:%M:%S")
            expiry_time = datetime.fromisoformat(config.get("expiry_time"))
            expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
            
            # Рассчитываем оставшееся время
            now = datetime.now()
            remaining_time = expiry_time - now
            remaining_days = remaining_time.days
            remaining_hours = remaining_time.seconds // 3600
            
            # Статус конфигурации
            status_text = (
                f"📊 *Статус вашей конфигурации WireGuard*\n\n"
                f"▫️ Активна: *Да*\n"
                f"▫️ Создана: *{created_at}*\n"
                f"▫️ Действует до: *{expiry_formatted}*\n"
                f"▫️ Осталось: *{remaining_days} дн. {remaining_hours} ч.*\n"
            )
            
            # Формируем клавиатуру
            keyboard = get_active_config_keyboard()
            
            await message.reply(
                status_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        else:
            keyboard = get_create_config_keyboard()
            
            await message.reply(
                "⚠️ *У вас нет активной конфигурации*\n\n"
                "Для создания новой конфигурации нажмите кнопку ниже или используйте команду /create.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        await message.reply(
            "❌ *Ошибка при получении данных о конфигурации*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# Обработчик для callback кнопки status
async def status_callback(callback_query: types.CallbackQuery):
    """Обработка запроса статуса через callback."""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    try:
        # Запрашиваем данные о конфигурации
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            # Парсим и форматируем данные о конфигурации
            created_at = datetime.fromisoformat(config.get("created_at")).strftime("%d.%m.%Y %H:%M:%S")
            expiry_time = datetime.fromisoformat(config.get("expiry_time"))
            expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
            
            # Рассчитываем оставшееся время
            now = datetime.now()
            remaining_time = expiry_time - now
            remaining_days = remaining_time.days
            remaining_hours = remaining_time.seconds // 3600
            
            await bot.send_message(
                user_id,
                f"📊 *Статус вашей конфигурации*\n\n"
                f"▫️ Активна: *Да*\n"
                f"▫️ Срок действия: до *{expiry_formatted}*\n"
                f"▫️ Осталось: *{remaining_days} дн. {remaining_hours} ч.*\n",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await bot.send_message(
                user_id,
                "❌ *У вас нет активной конфигурации*\n\n"
                "Создайте новую с помощью команды /create.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        await bot.send_message(
            user_id,
            "❌ *Ошибка при получении данных о конфигурации*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# Обработчик для получения конфигурации
async def send_config_file(callback_query: types.CallbackQuery):
    """Отправка файла конфигурации пользователю."""
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    # Эту функцию нужно реализовать отдельно
    # Здесь должен быть код для получения и отправки конфигурации

def register_handlers_status(dp: Dispatcher):
    """Регистрирует обработчики для проверки статуса."""
    dp.register_message_handler(get_config_status, commands=['status'])
    dp.register_message_handler(get_config_status, lambda message: message.text == "📊 Статус")
    dp.register_callback_query_handler(status_callback, lambda c: c.data == "status")
    dp.register_callback_query_handler(send_config_file, lambda c: c.data == "get_config")