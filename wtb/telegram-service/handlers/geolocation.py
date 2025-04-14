from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from datetime import datetime
from io import BytesIO

from core.settings import bot, logger
from states.states import GeoLocationStates
from keyboards.keyboards import get_permanent_keyboard
from utils.bd import get_user_config, get_available_geolocations, change_config_geolocation, get_all_user_configs
from utils.qr import generate_config_qr

# Функция для получения клавиатуры с геолокациями
def get_geolocation_keyboard(geolocations):
    """Создает клавиатуру с доступными геолокациями."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for geo in geolocations:
        geo_id = geo.get('id')
        geo_name = geo.get('name')
        server_count = geo.get('active_servers_count', 0)
        
        # Форматируем текст кнопки с дополнительной информацией
        button_text = f"{geo_name} ({server_count} серверов)"
        
        keyboard.add(
            InlineKeyboardButton(button_text, callback_data=f"geo_{geo_id}")
        )
    
    # Добавляем кнопку отмены
    keyboard.add(
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_geo")
    )
    
    return keyboard

# Обработчик для выбора геолокации
async def choose_geolocation(message: types.Message, state: FSMContext):
    """Выбор геолокации для конфигурации."""
    try:
        # Проверяем, есть ли у пользователя активная конфигурация
        user_id = message.from_user.id
        config = await get_user_config(user_id)
        
        if not config or not config.get("active", False):
            await message.reply(
                "⚠️ <b>У вас нет активной конфигурации</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем список доступных геолокаций
        geolocations = await get_available_geolocations()
        
        if not geolocations:
            await message.reply(
                "⚠️ <b>Нет доступных геолокаций</b>\n\n"
                "Попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем список геолокаций в состоянии
        await state.update_data(geolocations=geolocations)
        
        # Формируем клавиатуру с геолокациями
        keyboard = get_geolocation_keyboard(geolocations)
        
        # Определяем текущую геолокацию
        current_geo_id = config.get("geolocation_id")
        current_geo_name = "Неизвестно"
        
        for geo in geolocations:
            if geo.get('id') == current_geo_id:
                current_geo_name = geo.get('name')
                break
        
        await message.reply(
            f"🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
            f"От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.\n\n"
            f"Текущая геолокация: <b>{current_geo_name}</b>\n\n"
            f"При смене геолокации ваша текущая конфигурация будет обновлена, "
            f"срок действия останется прежним.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        # Переходим в состояние выбора геолокации
        await GeoLocationStates.selecting_geolocation.set()
    except Exception as e:
        logger.error(f"Ошибка при получении геолокаций: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик для callback-кнопки выбора геолокации
async def callback_choose_geolocation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик callback-кнопки выбора геолокации."""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    try:
        # Проверяем, есть ли у пользователя активная конфигурация
        config = await get_user_config(user_id)
        
        if not config or not config.get("active", False):
            await bot.send_message(
                user_id,
                "⚠️ <b>У вас нет активной конфигурации</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем список доступных геолокаций
        geolocations = await get_available_geolocations()
        
        if not geolocations:
            await bot.send_message(
                user_id,
                "⚠️ <b>Нет доступных геолокаций</b>\n\n"
                "Попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем список геолокаций в состоянии
        await state.update_data(geolocations=geolocations)
        
        # Формируем клавиатуру с геолокациями
        keyboard = get_geolocation_keyboard(geolocations)
        
        # Определяем текущую геолокацию
        current_geo_id = config.get("geolocation_id")
        current_geo_name = "Неизвестно"
        
        for geo in geolocations:
            if geo.get('id') == current_geo_id:
                current_geo_name = geo.get('name')
                break
        
        await bot.send_message(
            user_id,
            f"🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
            f"От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.\n\n"
            f"Текущая геолокация: <b>{current_geo_name}</b>\n\n"
            f"При смене геолокации ваша текущая конфигурация будет обновлена, "
            f"срок действия останется прежним.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        # Переходим в состояние выбора геолокации
        await GeoLocationStates.selecting_geolocation.set()
    except Exception as e:
        logger.error(f"Ошибка при получении геолокаций: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик выбора геолокации из списка
async def process_geolocation_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора геолокации."""
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
    
    try:
        # Сообщаем пользователю о начале процесса
        await bot.edit_message_text(
            f"🔄 <b>Анализ и выбор оптимального сервера...</b>\n\n"
            f"Геолокация: <b>{geolocation_name}</b>\n\n"
            f"Пожалуйста, подождите. Это может занять несколько секунд.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Обновляем геолокацию в базе данных
        result = await change_config_geolocation(user_id, geolocation_id)
        
        if "error" in result:
            await bot.edit_message_text(
                f"❌ <b>Ошибка!</b>\n\n{result['error']}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
            return
        
        # Сообщаем пользователю об успешном обновлении конфигурации
        await bot.edit_message_text(
            f"✅ <b>Геолокация успешно изменена на</b> <b>{geolocation_name}</b>\n\n"
            f"Все ваши устройства будут автоматически переключены на новую геолокацию.\n\n"
            f"Если вы используете стандартный клиент WireGuard, вам понадобится обновить конфигурацию. "
            f"Новая конфигурация будет отправлена вам сейчас.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Получаем обновленную конфигурацию
        config = await get_user_config(user_id)
        
        if config and config.get("config"):
            config_text = config.get("config")
            
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
                    caption=f"🔑 <b>QR-код вашей новой конфигурации WireGuard</b>\n\n"
                            f"Геолокация: <b>{geolocation_name}</b>\n\n"
                            f"Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                    parse_mode=ParseMode.HTML
                )
            
            # Отправляем файл конфигурации
            await bot.send_document(
                user_id,
                config_file,
                caption=f"📋 <b>Файл конфигурации WireGuard</b>\n\n"
                        f"Геолокация: <b>{geolocation_name}</b>\n\n"
                        f"Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем информацию о мобильном приложении
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📊 Проверить статус", callback_data="status")
            )
            
            await bot.send_message(
                user_id,
                f"📱 <b>Информация о приложении VPN Duck</b>\n\n"
                f"Для более комфортного использования сервиса вы можете скачать наше приложение, "
                f"которое автоматически переключается между серверами и геолокациями "
                f"без необходимости обновления конфигурации.\n\n"
                f"Название для поиска: <b>VPN Duck</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                user_id,
                "⚠️ <b>Не удалось получить обновленную конфигурацию</b>\n\n"
                "Пожалуйста, используйте команду /create для создания новой конфигурации.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Ошибка при обновлении геолокации: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )
    
    await state.finish()

# Обработчик для отмены выбора геолокации
async def cancel_geolocation_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена выбора геолокации."""
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Выбор геолокации отменен.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    
    await state.finish()

# Обработчик для получения всех конфигураций для разных серверов
async def get_all_configs(message: types.Message):
    """Получение всех конфигураций пользователя для разных серверов."""
    user_id = message.from_user.id
    
    try:
        # Получаем все конфигурации пользователя
        result = await get_all_user_configs(user_id)
        
        if "error" in result:
            await message.reply(
                f"⚠️ <b>Ошибка при получении конфигураций</b>\n\n{result['error']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        active_config = result.get("active_config", {})
        all_configs = result.get("all_configs", [])
        
        if not all_configs:
            await message.reply(
                "⚠️ <b>У вас нет сохраненных конфигураций</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Группируем конфигурации по геолокациям
        geo_configs = {}
        for config in all_configs:
            geo_code = config.get("geo_code")
            geo_name = config.get("geo_name")
            
            if geo_code not in geo_configs:
                geo_configs[geo_code] = {
                    "name": geo_name,
                    "configs": []
                }
            
            geo_configs[geo_code]["configs"].append(config)
        
        # Отправляем информацию о доступных конфигурациях
        message_text = f"📋 <b>Ваши конфигурации VPN Duck</b>\n\n"
        
        # Информация о текущей конфигурации
        expiry_time = active_config.get("expiry_time")
        if expiry_time:
            try:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                message_text += (
                    f"<b>Текущая конфигурация:</b>\n"
                    f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n\n"
                )
            except Exception:
                pass
        
        message_text += "Ниже будут отправлены конфигурации для всех доступных серверов по регионам.\n"
        
        await message.reply(message_text, parse_mode=ParseMode.HTML)
        
        # Отправляем конфигурации для каждой геолокации
        for geo_code, geo_data in geo_configs.items():
            geo_name = geo_data["name"]
            configs = geo_data["configs"]
            
            await message.reply(
                f"🌍 <b>Геолокация: {geo_name}</b>\n\n"
                f"Количество серверов: <b>{len(configs)}</b>\n\n"
                f"Отправляю конфигурации для всех серверов в этой геолокации...",
                parse_mode=ParseMode.HTML
            )
            
            # Создаем архив с конфигурациями для этой геолокации
            zip_buffer = BytesIO()
            
            # Используем модуль zipfile для создания архива
            import zipfile
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, config in enumerate(configs, 1):
                    server_endpoint = config.get("endpoint")
                    config_text = config.get("config_text")
                    
                    # Создаем имя файла конфигурации
                    config_filename = f"vpn_duck_{geo_code}_{i}_{server_endpoint}.conf"
                    
                    # Добавляем конфигурацию в архив
                    zip_file.writestr(config_filename, config_text)
            
            # Перемещаем указатель в начало буфера
            zip_buffer.seek(0)
            
            # Отправляем архив
            zip_buffer.name = f"vpn_duck_{geo_code}_configs.zip"
            await message.reply_document(
                zip_buffer,
                caption=f"📦 <b>Архив с конфигурациями для {geo_name}</b>\n\n"
                        f"Содержит конфигурации для всех серверов в этой геолокации.\n\n"
                        f"Для использования с приложением VPN Duck распакуйте архив и "
                        f"импортируйте все конфигурации.",
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем инструкцию для мобильного приложения
        await message.reply(
            "📱 <b>Инструкция для приложения VPN Duck</b>\n\n"
            "1. Скачайте и установите приложение VPN Duck\n"
            "2. Импортируйте все полученные конфигурации\n"
            "3. Приложение автоматически выберет оптимальный сервер\n"
            "4. При изменении геолокации приложение переключится на соответствующий сервер\n\n"
            "Приложение VPN Duck обеспечивает бесшовное переключение между серверами в случае "
            "недоступности текущего сервера или при смене геолокации.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при получении конфигураций: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик для возврата в главное меню
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в главное меню."""
    await bot.answer_callback_query(callback_query.id)
    
    # Завершаем все состояния
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    
    # Получаем информацию о пользователе
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    
    # Получаем конфигурацию пользователя
    config = await get_user_config(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if config and config.get("active", False):
        # Если есть активная конфигурация, показываем соответствующие кнопки
        # Получаем имя геолокации
        geo_name = config.get("geolocation_name", "Россия")
        
        keyboard.add(
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        keyboard.add(
            InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config")
        )
        
        await bot.edit_message_text(
            f"👋 Привет, {user_name}!\n\n"
            f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
            f"Ваша активная конфигурация:\n"
            f"▫️ Геолокация: <b>{geo_name}</b>\n\n"
            f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
            f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
            f"Выберите действие из меню ниже:",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    else:
        # Если нет активной конфигурации, показываем кнопку создания
        keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config")
        )
        
        await bot.edit_message_text(
            f"👋 Привет, {user_name}!\n\n"
            f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
            f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
            f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
            f"Выберите действие из меню ниже:",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

def register_handlers_geolocation(dp: Dispatcher):
    """Регистрирует обработчики для геолокаций."""
    dp.register_message_handler(choose_geolocation, commands=['geolocation'])
    dp.register_message_handler(choose_geolocation, lambda message: message.text == "🌍 Геолокация")
    dp.register_message_handler(get_all_configs, commands=['allconfigs'])
    dp.register_callback_query_handler(process_geolocation_selection, lambda c: c.data.startswith('geo_'), state=GeoLocationStates.selecting_geolocation)
    dp.register_callback_query_handler(cancel_geolocation_selection, lambda c: c.data == 'cancel_geo', state=GeoLocationStates.selecting_geolocation)
    
    # Дополнительные обработчики для UI-кнопок
    dp.register_callback_query_handler(callback_choose_geolocation, lambda c: c.data == 'choose_geo')
    dp.register_callback_query_handler(get_all_configs, lambda c: c.data == 'get_all_configs')
    
    # Обработчик для кнопки "Назад"
    dp.register_callback_query_handler(back_to_main_menu, lambda c: c.data == 'back_to_main', state='*')