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

# Обработчик для создания новой конфигурации
async def create_config(message: types.Message, state: FSMContext):
    """Создание новой конфигурации WireGuard."""
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
                f"⚠️ *У вас уже есть активная конфигурация!*\n\n"
                f"Срок действия: до *{expiry_formatted}*\n\n"
                f"Вы можете продлить срок действия, получить файл конфигурации снова "
                f"или пересоздать конфигурацию (текущая будет деактивирована).",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_active_config_keyboard()
            )
            return
        
        # Отправляем сообщение с запросом подтверждения
        await message.reply(
            "🔑 *Создание новой конфигурации WireGuard*\n\n"
            "После создания вы получите файл конфигурации и QR-код для быстрой настройки.\n\n"
            "Начальный срок действия: *7 дней*\n\n"
            "Подтвердите создание новой конфигурации:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_create_confirm_keyboard()
        )
        
        # Переходим в состояние подтверждения создания
        logger.info(f"Устанавливаем состояние CreateConfigStates.confirming_create для пользователя {message.from_user.id}")
        await CreateConfigStates.confirming_create.set()
    except Exception as e:
        logger.error(f"Ошибка при создании конфигурации: {str(e)}")
        await message.reply(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# Обработчик для подтверждения создания конфигурации
async def confirm_create_config(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение создания новой конфигурации."""
    logger.info(f"Вызван обработчик confirm_create_config с callback_data: {callback_query.data}")
    current_state = await state.get_state()
    logger.info(f"Текущее состояние пользователя: {current_state}")
    
    # Добавляем подробное логирование для отладки
    user_state_data = await state.get_data()
    logger.info(f"Данные состояния пользователя: {user_state_data}")
    
    # Проверяем наличие текущего состояния явно
    if current_state is None:
        logger.warning(f"Состояние пользователя не установлено. Устанавливаем его вручную.")
        await CreateConfigStates.confirming_create.set()
    
    # Остальной код остается без изменений
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
# async def confirm_create_config(callback_query: types.CallbackQuery, state: FSMContext):
#     """Подтверждение создания новой конфигурации."""
#     logger.info(f"Вызван обработчик confirm_create_config с callback_data: {callback_query.data}")
#     current_state = await state.get_state()
#     logger.info(f"Текущее состояние пользователя: {current_state}")
    
#     await bot.answer_callback_query(callback_query.id)
#     user_id = callback_query.from_user.id
    
    # Сообщаем пользователю о начале процесса создания
    await bot.edit_message_text(
        "🔄 *Создание конфигурации...*\n\n"
        "Пожалуйста, подождите. Это может занять несколько секунд.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Создаем новую конфигурацию
        config_data = await create_new_config(user_id)
        
        if "error" in config_data:
            await bot.edit_message_text(
                f"❌ *Ошибка!*\n\n{config_data['error']}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
            await state.finish()
            return
        
        config_text = config_data.get("config_text")
        
        if not config_text:
            await bot.edit_message_text(
                "❌ *Ошибка при создании конфигурации*\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
            await state.finish()
            return
        
        # Получаем данные о сроке действия из базы данных
        db_data = await get_user_config(user_id)
        
        expiry_text = ""
        if db_data:
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                expiry_text = f"▫️ Срок действия: до *{expiry_formatted}*\n"
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код
        qr_buffer = await generate_config_qr(config_text)
        
        # Обновляем сообщение об успешном создании
        await bot.edit_message_text(
            f"✅ *Конфигурация успешно создана!*\n\n"
            f"{expiry_text}\n"
            f"Файл конфигурации и QR-код будут отправлены отдельными сообщениями.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
        
        if qr_buffer:
            # Отправляем QR-код
            await bot.send_photo(
                user_id,
                qr_buffer,
                caption="🔑 *QR-код вашей конфигурации WireGuard*\n\n"
                        "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Отправляем файл конфигурации
        await bot.send_document(
            user_id,
            config_file,
            caption="📋 *Файл конфигурации WireGuard*\n\n"
                    "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Отправляем инструкции
        instructions_text = (
            "📱 *Как использовать конфигурацию:*\n\n"
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
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        await bot.edit_message_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Сбрасываем состояние
    await state.finish()

# Обработчик для отмены создания конфигурации
async def cancel_create_config(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена процесса создания конфигурации."""
    logger.info(f"Вызван обработчик cancel_create_config с callback_data: {callback_query.data}")
    current_state = await state.get_state()
    logger.info(f"Текущее состояние пользователя: {current_state}")
    
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Создание конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    
    # Сбрасываем состояние
    await state.finish()

# Обработчик для inline-кнопки создания конфигурации
async def create_config_from_button(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса создания через inline кнопку."""
    logger.info(f"Вызван обработчик create_config_from_button с callback_data: {callback_query.data}")
    
    await bot.answer_callback_query(callback_query.id)
    
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
                f"⚠️ *У вас уже есть активная конфигурация!*\n\n"
                f"Срок действия: до *{expiry_formatted}*\n\n"
                f"Вы можете продлить срок действия, получить файл конфигурации снова "
                f"или пересоздать конфигурацию (текущая будет деактивирована).",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_active_config_keyboard()
            )
            return
        
        # Формируем клавиатуру для подтверждения создания
        keyboard = get_create_confirm_keyboard()
        
        # Отправляем сообщение с запросом подтверждения
        await bot.send_message(
            user_id,
            "🔑 *Создание новой конфигурации WireGuard*\n\n"
            "После создания вы получите файл конфигурации и QR-код для быстрой настройки.\n\n"
            "Начальный срок действия: *7 дней*\n\n"
            "Подтвердите создание новой конфигурации:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
        # Переходим в состояние подтверждения создания
        logger.info(f"Устанавливаем состояние CreateConfigStates.confirming_create для пользователя {user_id}")
        await CreateConfigStates.confirming_create.set()
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        await bot.send_message(
            user_id,
            "❌ *Ошибка при проверке существующей конфигурации*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# def register_handlers_create(dp: Dispatcher):
#     """Регистрирует обработчики для создания конфигурации."""
#     dp.register_message_handler(create_config, commands=['create'])
#     dp.register_message_handler(create_config, lambda message: message.text == "🔑 Создать")
#     dp.register_callback_query_handler(create_config_from_button, lambda c: c.data == 'create_config')
    
#     # Регистрация обработчиков с привязкой к состоянию
#     dp.register_callback_query_handler(confirm_create_config, lambda c: c.data == 'confirm_create', state=CreateConfigStates.confirming_create)
#     dp.register_callback_query_handler(cancel_create_config, lambda c: c.data == 'cancel_create', state=CreateConfigStates.confirming_create)
    
#     # Если нужно отлаживать без привязки к состоянию, раскомментируйте эти строки
#     # dp.register_callback_query_handler(confirm_create_config, lambda c: c.data == 'confirm_create')
#     # dp.register_callback_query_handler(cancel_create_config, lambda c: c.data == 'cancel_create')

def register_handlers_create(dp: Dispatcher):
    """Регистрирует обработчики для создания конфигурации."""
    dp.register_message_handler(create_config, commands=['create'])
    dp.register_message_handler(create_config, lambda message: message.text == "🔑 Создать")
    dp.register_callback_query_handler(create_config_from_button, lambda c: c.data == 'create_config')
    
    # Fix: Move these handlers outside state checking to debug
    dp.register_callback_query_handler(confirm_create_config, lambda c: c.data == 'confirm_create')
    dp.register_callback_query_handler(cancel_create_config, lambda c: c.data == 'cancel_create')