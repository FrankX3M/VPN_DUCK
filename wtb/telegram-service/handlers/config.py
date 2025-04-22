from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from io import BytesIO

from core.settings import bot, logger
from utils.bd import get_config_from_wireguard
from utils.qr import generate_config_qr

# Обработчик для получения файла конфигурации
# async def get_config_file(callback_query: types.CallbackQuery):
#     """Отправка файла конфигурации и QR-кода."""
#     # Проверка, что колбэк ещё не был обработан middleware
#     if getattr(callback_query, '_handled', False):
#         logger.info(f"Колбэк get_config уже обработан middleware, пропускаем")
#         return
    
#     await bot.answer_callback_query(callback_query.id)
#     user_id = callback_query.from_user.id
    
#     try:
#         # Запрашиваем данные о конфигурации из WireGuard сервиса
#         config_data = await get_config_from_wireguard(user_id)
        
#         if "error" in config_data:
#             await bot.send_message(
#                 user_id,
#                 f"⚠️ <b>Ошибка при получении конфигурации</b>\n\n{config_data['error']}",
#                 parse_mode=ParseMode.HTML
#             )
#             return
        
#         config_text = config_data.get("config_text")
        
#         if not config_text:
#             await bot.send_message(
#                 user_id,
#                 "⚠️ <b>Ошибка при получении конфигурации</b>\n\n"
#                 "Конфигурация не найдена. Пожалуйста, создайте новую с помощью команды /create.",
#                 parse_mode=ParseMode.HTML
#             )
#             return
        
#         # Создаем файл конфигурации
#         config_file = BytesIO(config_text.encode('utf-8'))
#         config_file.name = f"vpn_duck_{user_id}.conf"
        
#         # Генерируем QR-код
#         qr_buffer = await generate_config_qr(config_text)
        
#         if qr_buffer:
#             # Отправляем QR-код
#             await bot.send_photo(
#                 user_id,
#                 qr_buffer,
#                 caption="🔑 <b>QR-код вашей конфигурации WireGuard</b>\n\n"
#                         "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
#                 parse_mode=ParseMode.HTML
#             )
        
#         # Отправляем файл конфигурации
#         await bot.send_document(
#             user_id,
#             config_file,
#             caption="📋 <b>Файл конфигурации WireGuard</b>\n\n"
#                     "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
#             parse_mode=ParseMode.HTML
#         )
        
#         # Отправляем инструкции
#         instructions_text = (
#             "📱 <b>Как использовать конфигурацию:</b>\n\n"
#             "1️⃣ Установите приложение WireGuard на ваше устройство\n"
#             "2️⃣ Откройте приложение и нажмите кнопку '+'\n"
#             "3️⃣ Выберите 'Сканировать QR-код' или 'Импорт из файла'\n"
#             "4️⃣ После импорта нажмите на добавленную конфигурацию для подключения\n\n"
#             "Готово! Теперь ваше соединение защищено VPN Duck 🦆"
#         )
        
#         await bot.send_message(
#             user_id,
#             instructions_text,
#             parse_mode=ParseMode.HTML
#         )
#     except Exception as e:
#         logger.error(f"Ошибка при получении конфигурации: {str(e)}", exc_info=True)
#         await bot.send_message(
#             user_id,
#             "❌ <b>Ошибка при получении конфигурации</b>\n\n"
#             "Пожалуйста, попробуйте позже.",
#             parse_mode=ParseMode.HTML
#         )

# def register_handlers_config(dp: Dispatcher):
#     """Регистрирует обработчики для получения конфигурации."""
#     # Пониженный приоритет, чтобы middleware мог обработать сначала
#     dp.register_callback_query_handler(get_config_file, lambda c: c.data == "get_config", state="*")

# Обработчик для получения файла конфигурации
async def get_config_file(callback_query: types.CallbackQuery):
    """Отправка файла конфигурации и QR-кода."""
    # Проверка, что колбэк ещё не был обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info(f"Колбэк get_config уже обработан middleware, пропускаем")
        return
    
    # Проверяем, находится ли колбэк в процессе обработки middleware
    if hasattr(callback_query, '_processing_key'):
        logger.info(f"Колбэк get_config в процессе обработки middleware, пропускаем")
        return
    
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    try:
        # Запрашиваем данные о конфигурации из WireGuard сервиса
        config_data = await get_config_from_wireguard(user_id)
        
        if "error" in config_data:
            await bot.send_message(
                user_id,
                f"⚠️ <b>Ошибка при получении конфигурации</b>\n\n{config_data['error']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        config_text = config_data.get("config_text")
        
        if not config_text:
            await bot.send_message(
                user_id,
                "⚠️ <b>Ошибка при получении конфигурации</b>\n\n"
                "Конфигурация не найдена. Пожалуйста, создайте новую с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код
        qr_buffer = await generate_config_qr(config_text)
        
        if qr_buffer:
            # Отправляем QR-код
            await bot.send_photo(
                user_id,
                qr_buffer,
                caption="🔑 <b>QR-код вашей конфигурации WireGuard</b>\n\n"
                        "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем файл конфигурации
        await bot.send_document(
            user_id,
            config_file,
            caption="📋 <b>Файл конфигурации WireGuard</b>\n\n"
                    "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
            parse_mode=ParseMode.HTML
        )
        
        # Отправляем инструкции
        instructions_text = (
            "📱 <b>Как использовать конфигурацию:</b>\n\n"
            "1️⃣ Установите приложение WireGuard на ваше устройство\n"
            "2️⃣ Откройте приложение и нажмите кнопку '+'\n"
            "3️⃣ Выберите 'Сканировать QR-код' или 'Импорт из файла'\n"
            "4️⃣ После импорта нажмите на добавленную конфигурацию для подключения\n\n"
            "Готово! Теперь ваше соединение защищено VPN Duck 🦆"
        )
        
        await bot.send_message(
            user_id,
            instructions_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при получении конфигурации: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Ошибка при получении конфигурации</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

def register_handlers_config(dp: Dispatcher):
    """Регистрирует обработчики для получения конфигурации."""
    # Регистрируем с низким приоритетом, чтобы middleware мог обработать сначала
    dp.register_callback_query_handler(get_config_file, lambda c: c.data == "get_config", state="*")