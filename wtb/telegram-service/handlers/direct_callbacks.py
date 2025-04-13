from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO

from core.settings import bot, logger
from utils.bd import get_user_config, create_new_config, get_config_from_wireguard
from utils.qr import generate_config_qr

# Прямой обработчик для создания конфигурации
async def direct_create_handler(callback_query: types.CallbackQuery):
    """Обработчик прямого создания конфигурации."""
    logger.info(f"Вызван direct_create_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
    
    # В случае если ни одна проверка не сработала, продолжаем обычную обработку
    logger.info("Обрабатываем колбэк в прямом обработчике")
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    # Сообщаем пользователю о начале процесса создания
    await bot.edit_message_text(
        "🔄 <b>Создание конфигурации...</b>\n\n"
        "Пожалуйста, подождите. Это может занять несколько секунд.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Создаем новую конфигурацию
        config_data = await create_new_config(user_id)
        
        if "error" in config_data:
            await bot.edit_message_text(
                f"❌ <b>Ошибка!</b>\n\n{config_data['error']}",
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
        
        # Получаем данные о сроке действия из базы данных
        db_data = await get_user_config(user_id)
        
        expiry_text = ""
        if db_data:
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код
        qr_buffer = await generate_config_qr(config_text)
        
        # Обновляем сообщение об успешном создании
        await bot.edit_message_text(
            f"✅ <b>Конфигурация успешно создана!</b>\n\n"
            f"{expiry_text}\n"
            f"Файл конфигурации и QR-код будут отправлены отдельными сообщениями.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
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
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend")
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
    """Обработчик прямой отмены создания."""
    logger.info(f"Вызван direct_cancel_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
    
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Создание конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )

def register_direct_handlers(dp: Dispatcher):
    """Регистрирует прямые обработчики."""
    # Регистрация прямых обработчиков с приоритетом
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
    
    # Регистрация дополнительных обработчиков для других колбэков с прямыми именами
    dp.register_callback_query_handler(
        direct_create_handler,
        lambda c: c.data == 'confirm_create',
        state='*'
    )
    dp.register_callback_query_handler(
        direct_cancel_handler,
        lambda c: c.data == 'cancel_create',
        state='*'
    )