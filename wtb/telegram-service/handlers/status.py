from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from datetime import datetime

from core.settings import bot, logger
from keyboards.keyboards import get_active_config_keyboard, get_create_config_keyboard
from utils.bd import get_user_config

# Обработчик для команды /status
# async def get_config_status(message: types.Message):
#     """Получение статуса конфигурации пользователя."""
#     user_id = message.from_user.id
    
#     try:
#         # Запрашиваем данные о конфигурации
#         config = await get_user_config(user_id)
        
#         if config and config.get("active", False):
#             # Парсим и форматируем данные о конфигурации
#             created_at = datetime.fromisoformat(config.get("created_at")).strftime("%d.%m.%Y %H:%M:%S")
#             expiry_time = datetime.fromisoformat(config.get("expiry_time"))
#             expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
            
#             # Рассчитываем оставшееся время
#             now = datetime.now()
#             remaining_time = expiry_time - now
#             remaining_days = remaining_time.days
#             remaining_hours = remaining_time.seconds // 3600
            
#             # Получаем информацию о геолокации
#             geolocation_name = config.get("geolocation_name", "Неизвестно")
            
#             # Статус конфигурации
#             status_text = (
#                 f"📊 <b>Статус вашей конфигурации WireGuard</b>\n\n"
#                 f"▫️ Активна: <b>Да</b>\n"
#                 f"▫️ Создана: <b>{created_at}</b>\n"
#                 f"▫️ Действует до: <b>{expiry_formatted}</b>\n"
#                 f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n"
#                 f"▫️ Геолокация: <b>{geolocation_name}</b>"
#             )
            
#             # Формируем клавиатуру
#             keyboard = get_active_config_keyboard()
            
#             await message.reply(
#                 status_text,
#                 parse_mode=ParseMode.HTML,
#                 reply_markup=keyboard
#             )
#         else:
#             keyboard = get_create_config_keyboard()
            
#             await message.reply(
#                 "⚠️ <b>У вас нет активной конфигурации</b>\n\n"
#                 "Для создания новой конфигурации нажмите кнопку ниже или используйте команду /create.",
#                 parse_mode=ParseMode.HTML,
#                 reply_markup=keyboard
#             )
#     except Exception as e:
#         logger.error(f"Ошибка при запросе к API: {str(e)}", exc_info=True)
#         await message.reply(
#             "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
#             "Пожалуйста, попробуйте позже.",
#             parse_mode=ParseMode.HTML
#         )
async def get_config_status(message: types.Message):
    """Получение статуса конфигурации пользователя."""
    user_id = message.from_user.id
    
    try:
        # Запрашиваем данные о конфигурации
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            # Парсим и форматируем данные о конфигурации с обработкой ошибок
            try:
                created_at = datetime.fromisoformat(config.get("created_at")).strftime("%d.%m.%Y %H:%M:%S")
            except (ValueError, TypeError):
                created_at = "Неизвестно"
            
            try:
                expiry_time_str = config.get("expiry_time")
                expiry_time = datetime.fromisoformat(expiry_time_str)
                expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
                
                # Рассчитываем оставшееся время
                now = datetime.now()
                remaining_time = expiry_time - now
                remaining_days = max(0, remaining_time.days)
                remaining_hours = max(0, remaining_time.seconds // 3600)
            except (ValueError, TypeError, AttributeError):
                logger.error(f"Ошибка парсинга даты истечения: {config.get('expiry_time')}")
                expiry_formatted = "Неизвестно"
                remaining_days = 0
                remaining_hours = 0
            
            # Получаем информацию о геолокации
            geolocation_name = config.get("geolocation_name", "Неизвестно")
            
            # Статус конфигурации
            status_text = (
                f"📊 <b>Статус вашей конфигурации WireGuard</b>\n\n"
                f"▫️ Активна: <b>Да</b>\n"
                f"▫️ Создана: <b>{created_at}</b>\n"
                f"▫️ Действует до: <b>{expiry_formatted}</b>\n"
                f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n"
                f"▫️ Геолокация: <b>{geolocation_name}</b>"
            )
            
            # Формируем клавиатуру
            keyboard = get_active_config_keyboard()
            
            await message.reply(
                status_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            keyboard = get_create_config_keyboard()
            
            await message.reply(
                "⚠️ <b>У вас нет активной конфигурации</b>\n\n"
                "Для создания новой конфигурации нажмите кнопку ниже или используйте команду /create.",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик для callback кнопки status
async def status_callback(callback_query: types.CallbackQuery):
    """Обработка запроса статуса через callback."""
    # Проверка что колбэк не был уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info(f"Колбэк {callback_query.data} уже обработан middleware, пропускаем")
        return
        
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    try:
        # Запрашиваем данные о конфигурации
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            # Парсим и форматируем данные о конфигурации
            expiry_time = datetime.fromisoformat(config.get("expiry_time"))
            expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
            
            # Получаем информацию о геолокации
            geolocation_name = config.get("geolocation_name", "Неизвестно")
            
            # Рассчитываем оставшееся время
            now = datetime.now()
            remaining_time = expiry_time - now
            remaining_days = remaining_time.days
            remaining_hours = remaining_time.seconds // 3600
            
            await bot.send_message(
                user_id,
                f"📊 <b>Статус вашей конфигурации</b>\n\n"
                f"▫️ Активна: <b>Да</b>\n"
                f"▫️ Действует до: <b>{expiry_formatted}</b>\n"
                f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n"
                f"▫️ Геолокация: <b>{geolocation_name}</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                user_id,
                "❌ <b>У вас нет активной конфигурации</b>\n\n"
                "Создайте новую с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

def register_handlers_status(dp: Dispatcher):
    """Регистрирует обработчики для проверки статуса."""
    dp.register_message_handler(get_config_status, commands=['status'])
    dp.register_message_handler(get_config_status, lambda message: message.text == "📊 Статус")
    dp.register_callback_query_handler(status_callback, lambda c: c.data == "status", state="*")