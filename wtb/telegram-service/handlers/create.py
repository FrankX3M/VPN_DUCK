from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from datetime import datetime
from io import BytesIO

from core.settings import bot, logger
from states.states import CreateConfigStates, GeoLocationStates
from keyboards.keyboards import get_create_confirm_keyboard, get_active_config_keyboard
from utils.bd import get_user_config, create_new_config, get_config_from_wireguard, get_available_geolocations
from utils.qr import generate_config_qr

from keyboards.keyboards import get_geolocation_keyboard


def safe_parse_datetime(dt_value):
    """Безопасно парсит datetime из различных форматов"""
    if dt_value is None:
        return None
    
    # Если уже datetime объект
    if isinstance(dt_value, datetime):
        return dt_value
    
    # Если строка
    if isinstance(dt_value, str):
        try:
            # Пробуем fromisoformat
            return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Пробуем strptime для других форматов
                return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # Пробуем без времени
                    return datetime.strptime(dt_value, '%Y-%m-%d')
                except ValueError:
                    logger.error(f"Не удалось распарсить дату: {dt_value}")
                    return None
    
    logger.error(f"Неизвестный тип даты: {type(dt_value)} = {dt_value}")
    return None


async def direct_create_handler(callback_query: types.CallbackQuery):
    """Прямое создание конфигурации - показывает список геолокаций."""
    logger.info(f"Вызван direct_create_handler с данными: {callback_query.data}")
    
    try:
        await bot.answer_callback_query(callback_query.id)
        user_id = callback_query.from_user.id
        
        # Получаем список доступных геолокаций
        try:
            geolocations = await get_available_geolocations()
            
            if not geolocations:
                await bot.edit_message_text(
                    "⚠️ <b>Нет доступных геолокаций</b>\n\n"
                    "Попробуйте позже.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Формируем клавиатуру с геолокациями
            keyboard = InlineKeyboardMarkup(row_width=1)
            
            # Добавляем кнопки для каждой геолокации
            for geo in geolocations:
                geo_id = geo.get('id')
                geo_name = geo.get('name', "")
                server_count = geo.get('active_servers_count', 0)
                
                # Форматируем текст кнопки
                button_text = f"{geo_name} ({server_count} серверов)"
                
                keyboard.add(
                    InlineKeyboardButton(button_text, callback_data=f"geo_{geo_id}")
                )
            
            # Добавляем кнопку отмены
            keyboard.add(
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_create")
            )
            
            await bot.edit_message_text(
                f"🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
                f"От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
            # Переводим пользователя в состояние выбора геолокации
            await GeoLocationStates.selecting_geolocation_for_create.set()
            
        except Exception as e:
            logger.error(f"Ошибка при получении геолокаций: {str(e)}", exc_info=True)
            await bot.edit_message_text(
                "❌ <b>Произошла ошибка при получении геолокаций</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Неожиданная ошибка в direct_create_handler: {str(e)}", exc_info=True)
        try:
            await bot.edit_message_text(
                "❌ <b>Произошла ошибка</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
        except Exception as message_error:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {str(message_error)}")


async def cancel_create_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена процесса создания конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    
    # Сбрасываем состояние
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    
    await bot.edit_message_text(
        "❌ <b>Создание конфигурации отменено</b>\n\n"
        "Вы можете создать конфигурацию позже, когда будете готовы.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


async def confirm_create_config(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение создания новой конфигурации с возможностью выбора геолокации."""
    logger.info(f"Вызван обработчик confirm_create_config с данными: {callback_query.data}")
    
    try:
        # Отвечаем на callback query сразу, чтобы не было "часиков" в Telegram
        await bot.answer_callback_query(callback_query.id)
        user_id = callback_query.from_user.id
        logger.info(f"Обработка запроса для пользователя {user_id}")
        
        # Сначала отправим пользователю сообщение, что начинаем процесс
        await bot.edit_message_text(
            "🔄 <b>Подготовка списка доступных геолокаций...</b>\n\n"
            "Пожалуйста, подождите.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Получаем доступные геолокации с подробным логированием
        logger.info("Запрашиваем список доступных геолокаций из базы данных")
        try:
            geolocations = await get_available_geolocations()
            logger.info(f"Получены геолокации: {len(geolocations) if geolocations else 0}")
            
            if not geolocations:
                logger.warning("Список геолокаций пуст")
                await bot.edit_message_text(
                    "❌ <b>Ошибка!</b>\n\n"
                    "Нет доступных геолокаций. Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
                await state.finish()
                return
        except Exception as geo_error:
            logger.error(f"Ошибка при получении геолокаций: {str(geo_error)}", exc_info=True)
            await bot.edit_message_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Произошла ошибка при получении списка геолокаций. Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
            return
        
        # Сохраняем список геолокаций в состоянии
        logger.info("Сохраняем список геолокаций в состоянии FSM")
        await state.update_data(geolocations=geolocations, is_creating=True)
        
        # Формируем клавиатуру с геолокациями
        logger.info("Формируем клавиатуру с геолокациями")
        try:
            keyboard = get_geolocation_keyboard(geolocations)
            logger.info("Клавиатура с геолокациями успешно создана")
        except Exception as keyboard_error:
            logger.error(f"Ошибка при создании клавиатуры: {str(keyboard_error)}", exc_info=True)
            await bot.edit_message_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Произошла ошибка при создании меню выбора геолокаций. Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
            return
        
        # Отправляем сообщение с просьбой выбрать геолокацию
        logger.info("Отправляем сообщение с просьбой выбрать геолокацию")
        try:
            await bot.edit_message_text(
                "🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
                "От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            logger.info("Сообщение успешно отправлено")
        except Exception as message_error:
            logger.error(f"Ошибка при отправке сообщения: {str(message_error)}", exc_info=True)
            # Пробуем отправить новое сообщение, если редактирование не удалось
            try:
                await bot.send_message(
                    callback_query.message.chat.id,
                    "🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
                    "От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                logger.info("Новое сообщение успешно отправлено")
            except Exception as retry_error:
                logger.error(f"Ошибка при повторной отправке сообщения: {str(retry_error)}", exc_info=True)
                await state.finish()
                return
        
        # Переходим в состояние выбора геолокации для создания
        logger.info("Переходим в состояние выбора геолокации для создания")
        await GeoLocationStates.selecting_geolocation_for_create.set()
        logger.info("Состояние успешно установлено")
        
    except Exception as e:
        logger.error(f"Общая ошибка в обработчике confirm_create_config: {str(e)}", exc_info=True)
        try:
            # Пытаемся сообщить пользователю об ошибке
            await bot.edit_message_text(
                "❌ <b>Произошла непредвиденная ошибка</b>\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
        except Exception as notify_error:
            logger.error(f"Не удалось уведомить пользователя об ошибке: {str(notify_error)}")
            # Пробуем отправить новое сообщение
            try:
                await bot.send_message(
                    callback_query.message.chat.id,
                    "❌ <b>Произошла непредвиденная ошибка</b>\n\n"
                    "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass  # Если и это не удалось, просто логируем
        
        # Сбрасываем состояние в любом случае
        await state.finish()


async def process_geolocation_for_create(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора геолокации при создании новой конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем выбранную геолокацию
    geolocation_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    
    # Получаем данные из состояния
    state_data = await state.get_data()
    geolocations = state_data.get('geolocations', [])
    
    # Находим название выбранной геолокации
    geolocation_name = "Неизвестная геолокация"
    for geo in geolocations:
        if geo.get('id') == geolocation_id:
            geolocation_name = geo.get('name')
            break
    
    # Сообщаем пользователю о начале процесса создания
    await bot.edit_message_text(
        f"🔄 <b>Создание конфигурации...</b>\n\n"
        f"Выбрана геолокация: <b>{geolocation_name}</b>\n\n"
        f"Пожалуйста, подождите. Это может занять несколько секунд.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Создаем новую конфигурацию с указанием геолокации
        config_data = await create_new_config(user_id, geolocation_id=geolocation_id)
        
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
            # Информация о сроке действия - ИСПРАВЛЕННАЯ ВЕРСИЯ
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                expiry_dt = safe_parse_datetime(expiry_time)
                if expiry_dt:
                    expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                    expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
                else:
                    logger.warning(f"Не удалось распарсить дату истечения: {expiry_time}")
                    expiry_text = f"▫️ Срок действия: <b>неизвестно</b>\n"
            
            # Информация о геолокации
            geo_name = db_data.get("geolocation_name") or geolocation_name
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
            
            # ИСПРАВЛЕНИЕ: Безопасный парсинг даты
            expiry_dt = safe_parse_datetime(expiry_time)
            if expiry_dt is None:
                logger.warning(f"Не удалось получить дату истечения для пользователя {user_id}, используем текущую дату")
                expiry_formatted = "неизвестно"
            else:
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
            
            # ИСПРАВЛЕНИЕ: Безопасный парсинг даты
            expiry_dt = safe_parse_datetime(expiry_time)
            if expiry_dt is None:
                logger.warning(f"Не удалось получить дату истечения для пользователя {user_id}, используем текущую дату")
                expiry_formatted = "неизвестно"
            else:
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
    dp.register_callback_query_handler(confirm_create_config, lambda c: c.data == "confirm_create", state=CreateConfigStates.confirming_create)
    dp.register_callback_query_handler(process_geolocation_for_create, lambda c: c.data.startswith("geo_"), state=GeoLocationStates.selecting_geolocation_for_create)
    dp.register_callback_query_handler(direct_create_handler, lambda c: c.data == 'direct_create')
    dp.register_callback_query_handler(cancel_create_handler, lambda c: c.data == 'cancel_create', state='*')
    