from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from datetime import datetime
from io import BytesIO

from core.settings import bot, logger
from states.states import CreateConfigStates
from keyboards.keyboards import get_create_confirm_keyboard, get_active_config_keyboard
from utils.bd import get_user_config, create_new_config, get_config_from_wireguard
from utils.qr import generate_config_qr

# поддержка выбора геолокации во время создания конфигурации
async def confirm_create_config(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение создания новой конфигурации с возможностью выбора геолокации."""
    logger.info(f"Вызван обработчик confirm_create_config с данными: {callback_query.data}")
    
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
        # Получаем доступные геолокации
        geolocations = await get_available_geolocations()
        if geolocations:
            # Формируем клавиатуру с геолокациями
            keyboard = get_geolocation_keyboard(geolocations)
            
            await message.reply(
                "🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
                "От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
            # Переходим в состояние выбора геолокации
            await GeoLocationStates.selecting_geolocation.set()
        else:
            default_geolocation_id = None
        
        # Выбираем геолокацию по умолчанию (например, первую из списка)
        if geolocations:
            default_geolocation_id = geolocations[0].get('id')
        
        # Создаем новую конфигурацию с указанием геолокации
        config_data = await create_new_config(user_id, geolocation_id=default_geolocation_id)
        
        if "error" in config_data:
            await bot.edit_message_text(
                f"❌ <b>Ошибка!</b>\n\n{config_data['error']}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
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
            await state.finish()
            return
        
        # Получаем данные о сроке действия и геолокации из базы данных
        db_data = await get_user_config(user_id)
        
        expiry_text = ""
        geo_text = ""
        
        if db_data:
            # Информация о сроке действия
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
            
            # Информация о геолокации
            geo_name = db_data.get("geolocation_name", "Неизвестно")
            geo_text = f"▫️ Геолокация: <b>{geo_name}</b>\n"
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код
        qr_buffer = await generate_config_qr(config_text)
        
        # Обновляем сообщение об успешном создании
        await bot.edit_message_text(
            f"✅ <b>Конфигурация успешно создана!</b>\n\n"
            f"{expiry_text}"
            f"{geo_text}\n"
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
        
        # Отправляем инструкции и кнопки для выбора геолокации и продления
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Изменить геолокацию", callback_data="choose_geo")
        )
        
        instructions_text = (
            "📱 <b>Как использовать конфигурацию:</b>\n\n"
            "1️⃣ Установите приложение WireGuard на ваше устройство\n"
            "2️⃣ Откройте приложение и нажмите кнопку '+'\n"
            "3️⃣ Выберите 'Сканировать QR-код' или 'Импорт из файла'\n"
            "4️⃣ После импорта нажмите на добавленную конфигурацию для подключения\n\n"
            "Готово! Теперь ваше соединение защищено VPN Duck 🦆\n\n"
            "Вы можете изменить геолокацию вашего VPN в любое время, что позволит оптимизировать скорость и доступность сервисов."
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
    
    # Сбрасываем состояние
    await state.finish()

# Прямой обработчик для подтверждения создания конфигурации
async def direct_confirm_create(callback_query: types.CallbackQuery):
    """Прямой обработчик подтверждения создания конфигурации."""
    # Проверка что колбэк не был уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info(f"Колбэк {callback_query.data} уже обработан middleware, пропускаем")
        return
        
    logger.info(f"Вызван прямой обработчик direct_confirm_create с данными: {callback_query.data}")
    
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
async def direct_cancel_create(callback_query: types.CallbackQuery):
    """Прямой обработчик отмены создания конфигурации."""
    # Проверка что колбэк не был уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info(f"Колбэк {callback_query.data} уже обработан middleware, пропускаем")
        return
        
    logger.info(f"Вызван прямой обработчик direct_cancel_create с данными: {callback_query.data}")
    
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Создание конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )

# Обработчик для создания новой конфигурации
async def create_config(message: types.Message, state: FSMContext):
    """Создание новой конфигурации WireGuard."""
    # Сначала завершаем предыдущее состояние, если было
    current_state = await state.get_state()
    if current_state:
        await state.finish()
        
    user_id = message.from_user.id
    
    try:
        # Проверяем, есть ли уже активная конфигурация
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            # У пользователя уже есть активная конфигурация
            expiry_time = config.get("expiry_time")
            expiry_dt = datetime.fromisoformat(expiry_time)
            expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
            
            await message.reply(
                f"⚠️ <b>У вас уже есть активная конфигурация!</b>\n\n"
                f"Срок действия: до <b>{expiry_formatted}</b>\n\n"
                f"Вы можете продлить срок действия, получить файл конфигурации снова "
                f"или пересоздать конфигурацию (текущая будет деактивирована).",
                parse_mode=ParseMode.HTML,
                reply_markup=get_active_config_keyboard()
            )
            return
        
        # Отправляем сообщение с запросом подтверждения
        await message.reply(
            "🔑 <b>Создание новой конфигурации WireGuard</b>\n\n"
            "После создания вы получите файл конфигурации и QR-код для быстрой настройки.\n\n"
            "Начальный срок действия: <b>7 дней</b>\n\n"
            "Подтвердите создание новой конфигурации:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_create_confirm_keyboard()
        )
        
        # Переходим в состояние подтверждения создания
        logger.info(f"Устанавливаем состояние CreateConfigStates.confirming_create для пользователя {message.from_user.id}")
        await CreateConfigStates.confirming_create.set()
    except Exception as e:
        logger.error(f"Ошибка при создании конфигурации: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик для inline-кнопки создания конфигурации
async def create_config_from_button(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса создания через inline кнопку."""
    logger.info(f"Вызван обработчик create_config_from_button с callback_data: {callback_query.data}")
    
    await bot.answer_callback_query(callback_query.id)
    
    # Сначала завершаем предыдущее состояние, если было
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    
    # Получаем user_id из callback_query
    user_id = callback_query.from_user.id
    
    try:
        # Проверяем, есть ли уже активная конфигурация
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            # У пользователя уже есть активная конфигурация
            expiry_time = config.get("expiry_time")
            expiry_dt = datetime.fromisoformat(expiry_time)
            expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
            
            await bot.send_message(
                user_id,
                f"⚠️ <b>У вас уже есть активная конфигурация!</b>\n\n"
                f"Срок действия: до <b>{expiry_formatted}</b>\n\n"
                f"Вы можете продлить срок действия, получить файл конфигурации снова "
                f"или пересоздать конфигурацию (текущая будет деактивирована).",
                parse_mode=ParseMode.HTML,
                reply_markup=get_active_config_keyboard()
            )
            return
        
        # Формируем клавиатуру для подтверждения создания
        keyboard = get_create_confirm_keyboard()
        
        # Отправляем сообщение с запросом подтверждения
        await bot.send_message(
            user_id,
            "🔑 <b>Создание новой конфигурации WireGuard</b>\n\n"
            "После создания вы получите файл конфигурации и QR-код для быстрой настройки.\n\n"
            "Начальный срок действия: <b>7 дней</b>\n\n"
            "Подтвердите создание новой конфигурации:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        # Переходим в состояние подтверждения создания
        logger.info(f"Устанавливаем состояние CreateConfigStates.confirming_create для пользователя {user_id}")
        await CreateConfigStates.confirming_create.set()
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Ошибка при проверке существующей конфигурации</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

def register_handlers_create(dp: Dispatcher):
    """Регистрирует обработчики для создания конфигурации."""
    # Основные хендлеры
    dp.register_message_handler(create_config, commands=['create'])
    dp.register_message_handler(create_config, lambda message: message.text == "🔑 Создать")
    dp.register_callback_query_handler(create_config_from_button, lambda c: c.data == 'create_config')
    
    # Регистрация колбэк-обработчиков с фильтрами, которые не пересекаются с middleware
    dp.register_callback_query_handler(
        direct_confirm_create, 
        lambda c: c.data == 'confirm_create',
        state='*'
    )
    dp.register_callback_query_handler(
        direct_cancel_create,
        lambda c: c.data == 'cancel_create',
        state='*'
    )