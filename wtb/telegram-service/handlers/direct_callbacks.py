from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO
import asyncio
from core.settings import bot, logger
from utils.bd import get_user_config, create_new_config, get_config_from_wireguard, are_servers_available, check_services_availability
from utils.qr import generate_config_qr

# Прямой обработчик для создания конфигурации
async def direct_create_handler(callback_query: types.CallbackQuery):
    """Обработчик прямого создания конфигурации."""
    logger.info(f"Вызван direct_create_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
    
    # Помечаем колбэк как обработанный
    callback_query._handled = True

    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    # Проверяем наличие доступных серверов
    logger.info("Проверяем доступность сервисов перед созданием конфигурации")
    services_status = await check_services_availability()
    
    if not services_status["wireguard"]:
        await bot.edit_message_text(
            "⚠️ <b>Создание конфигурации невозможно</b>\n\n"
            "В данный момент VPN-сервер недоступен. "
            "Пожалуйста, попробуйте позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        return
    
    if not services_status["database"]:
        logger.warning("База данных недоступна, но продолжаем попытку создания конфигурации")
    
    # Сообщаем пользователю о начале процесса создания
    await bot.edit_message_text(
        "🔄 <b>Создание конфигурации...</b>\n\n"
        "Пожалуйста, подождите. Это может занять несколько секунд.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Создаем новую конфигурацию с таймаутом
        create_task = asyncio.create_task(create_new_config(user_id))
        
        try:
            config_data = await asyncio.wait_for(create_task, timeout=30)
        except asyncio.TimeoutError:
            await bot.edit_message_text(
                "⚠️ <b>Превышено время ожидания</b>\n\n"
                "Сервер слишком долго не отвечает. Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
        
        if "error" in config_data:
            error_message = config_data['error']
            if "Error communicating with remote server" in error_message:
                await bot.edit_message_text(
                    "⚠️ <b>Ошибка соединения с сервером</b>\n\n"
                    "В данный момент сервер WireGuard недоступен. Пожалуйста, попробуйте позже.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
            else:
                await bot.edit_message_text(
                    f"❌ <b>Ошибка!</b>\n\n{error_message}",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
            return
        
        config_text = config_data.get("config_text")
        
        if not config_text:
            await bot.edit_message_text(
                "❌ <b>Ошибка при создании конфигурации</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем данные о сроке действия и геолокации из базы данных
        get_config_task = asyncio.create_task(get_user_config(user_id))
        
        try:
            db_data = await asyncio.wait_for(get_config_task, timeout=10)
        except asyncio.TimeoutError:
            db_data = None
            logger.warning(f"Таймаут при получении данных конфигурации для пользователя {user_id}")
        
        expiry_text = ""
        geo_text = ""
        
        if db_data:
            # Информация о сроке действия
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                try:
                    expiry_dt = datetime.fromisoformat(expiry_time)
                    expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                    expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
                except ValueError:
                    pass
            
            # Информация о геолокации
            geo_name = db_data.get("geolocation_name", "")
            if geo_name:
                geo_text = f"▫️ Геолокация: <b>{geo_name}</b>\n"
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код с таймаутом
        qr_task = asyncio.create_task(generate_config_qr(config_text))
        
        try:
            qr_buffer = await asyncio.wait_for(qr_task, timeout=10)
        except asyncio.TimeoutError:
            qr_buffer = None
            logger.warning(f"Таймаут при генерации QR-кода для пользователя {user_id}")
        
        # Обновляем сообщение об успешном создании
        success_message = f"✅ <b>Конфигурация успешно создана!</b>\n\n"
        
        if geo_text:
            success_message += geo_text
        
        if expiry_text:
            success_message += expiry_text
        
        success_message += "\nФайл конфигурации и QR-код будут отправлены отдельными сообщениями."
        
        await bot.edit_message_text(
            success_message,
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        if qr_buffer:
            # Отправляем QR-код
            caption = "🔑 <b>QR-код вашей конфигурации WireGuard</b>\n\n"
            
            if geo_text:
                caption += geo_text.strip() + "\n\n"
                
            caption += "Отсканируйте этот код в приложении WireGuard для быстрой настройки."
            
            await bot.send_photo(
                user_id,
                qr_buffer,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем файл конфигурации
        caption = "📋 <b>Файл конфигурации WireGuard</b>\n\n"
        
        if geo_text:
            caption += geo_text.strip() + "\n\n"
            
        caption += "Импортируйте этот файл в приложение WireGuard для настройки соединения."
        
        await bot.send_document(
            user_id,
            config_file,
            caption=caption,
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
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        
        await bot.send_message(
            user_id,
            instructions_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        await bot.edit_message_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

# Прямой обработчик для отмены создания конфигурации
async def direct_cancel_handler(callback_query: types.CallbackQuery):
    """Обработчик прямого создания конфигурации."""
    logger.info(f"Вызван direct_create_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
    
    # Помечаем колбэк как обработанный
    callback_query._handled = True
    
    # В случае если ни одна проверка не сработала, продолжаем обычную обработку
    logger.info("Обрабатываем колбэк в прямом обработчике")
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Создание конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
 
def register_direct_handlers(dp: Dispatcher):
    """Регистрирует прямые обработчики."""
    # Регистрация прямых обработчиков без указания приоритета
    dp.register_callback_query_handler(
        direct_create_handler,
        lambda c: c.data == 'direct_create',
        state='*'
    )
    dp.register_callback_query_handler(
        direct_cancel_handler,
        lambda c: c.data == 'direct_cancel',
        state='*'
    )