from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO
import html

from core.settings import bot, logger
from keyboards.keyboards import get_recreate_confirm_keyboard 
from utils.bd import recreate_config, get_user_config, get_available_geolocations
from utils.qr import generate_config_qr

# Обработчик для пересоздания конфигурации
async def recreate_config_handler(callback_query: types.CallbackQuery):
    """Пересоздание конфигурации WireGuard - показывает выбор геолокации."""
    await bot.answer_callback_query(callback_query.id)
    await choose_geo_for_recreate(callback_query)

# Обработчик для выбора геолокации при пересоздании
async def choose_geo_for_recreate(callback_query: types.CallbackQuery):
    """Выбор геолокации для пересоздания конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    
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
        
        # Получаем данные о текущей конфигурации пользователя
        user_id = callback_query.from_user.id
        config = await get_user_config(user_id)
        
        # Определяем текущую геолокацию
        current_geo_id = None
        current_geo_name = "Неизвестно"
        if config and "geolocation_id" in config:
            current_geo_id = config.get("geolocation_id")
            for geo in geolocations:
                if geo.get('id') == current_geo_id:
                    current_geo_name = geo.get('name')
                    break
        
        # Формируем клавиатуру с геолокациями
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        # Добавляем кнопки для каждой геолокации
        for geo in geolocations:
            geo_id = geo.get('id')
            geo_name = geo.get('name', "")
            server_count = geo.get('active_servers_count', 0)
            
            # Форматируем текст кнопки (помечаем текущую локацию)
            button_text = f"✅ {geo_name} ({server_count} серверов)" if geo_id == current_geo_id else f"{geo_name} ({server_count} серверов)"
            
            keyboard.add(
                InlineKeyboardButton(button_text, callback_data=f"recreate_geo_{geo_id}")
            )
        
        # Добавляем кнопку отмены
        keyboard.add(
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_recreate")
        )
        
        # Экранируем имя геолокации
        safe_geo_name = html.escape(current_geo_name)
        
        await bot.edit_message_text(
            f"🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
            f"От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.\n\n"
            f"Текущая геолокация: <b>{safe_geo_name}</b>\n\n"
            f"При пересоздании конфигурации ваша новая конфигурация будет создана с выбранной локацией.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе геолокации: {str(e)}", exc_info=True)
        error_message = html.escape(str(e))
        await bot.edit_message_text(
            f"❌ <b>Произошла ошибка</b>\n\n{error_message}",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

# Обработчик для выбора конкретной геолокации при пересоздании
async def select_geo_for_recreate(callback_query: types.CallbackQuery):
    """Обработка выбора конкретной геолокации для пересоздания."""
    await bot.answer_callback_query(callback_query.id)
    
    try:
        # Получаем ID выбранной геолокации из callback_data
        callback_data = callback_query.data
        logger.info(f"Получен callback_data: {callback_data}")
        
        try:
            geolocation_id = int(callback_data.split('_')[2])
            logger.info(f"Извлечен geolocation_id: {geolocation_id}")
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка при извлечении geolocation_id из {callback_data}: {str(e)}")
            geolocation_id = None
        
        user_id = callback_query.from_user.id
        
        # Получаем информацию о выбранной геолокации
        geolocations = await get_available_geolocations()
        selected_geo = None
        
        for geo in geolocations:
            if geo.get('id') == geolocation_id:
                selected_geo = geo
                break
        
        if not selected_geo:
            await bot.edit_message_text(
                "⚠️ <b>Ошибка при выборе геолокации</b>\n\n"
                "Выбранная геолокация не найдена. Пожалуйста, попробуйте снова.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
        
        geo_name = selected_geo.get('name', "")
        # Экранируем имя геолокации
        safe_geo_name = html.escape(geo_name)
        logger.info(f"Выбрана геолокация: {geo_name} (ID: {geolocation_id})")
        
        # Формируем клавиатуру для подтверждения пересоздания
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_recreate_{geolocation_id}"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_recreate")
        )
        
        await bot.edit_message_text(
            f"⚠️ <b>Пересоздание конфигурации WireGuard</b>\n\n"
            f"Выбрана геолокация: <b>{safe_geo_name}</b>\n\n"
            f"Внимание! При пересоздании конфигурации:\n"
            f"• Текущая конфигурация будет деактивирована\n"
            f"• Вы получите новую конфигурацию с новыми ключами\n"
            f"• Срок действия будет установлен на 7 дней\n"
            f"• Будет использована выбранная геолокация: <b>{safe_geo_name}</b>\n\n"
            f"Вам потребуется обновить настройки на всех ваших устройствах.\n\n"
            f"Подтвердите пересоздание конфигурации:",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе геолокации: {str(e)}", exc_info=True)
        error_message = html.escape(str(e))
        await bot.edit_message_text(
            f"❌ <b>Произошла ошибка</b>\n\n{error_message}",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

# Обработчик для подтверждения пересоздания конфигурации
async def confirm_recreate_config(callback_query: types.CallbackQuery):
    """Подтверждение пересоздания конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    try:
        # Проверяем, была ли выбрана геолокация
        callback_data = callback_query.data
        logger.info(f"Подтверждение пересоздания. Callback_data: {callback_data}")
        
        geolocation_id = None
        # Извлекаем geolocation_id из callback_data, если он там есть
        parts = callback_data.split('_')
        if len(parts) > 2:
            try:
                geolocation_id = int(parts[2])
                logger.info(f"Извлечен geolocation_id из callback_data: {geolocation_id}")
            except (ValueError, IndexError) as e:
                logger.error(f"Ошибка при извлечении geolocation_id из {callback_data}: {str(e)}")
                geolocation_id = None
        
        # Получаем информацию о геолокации для отображения
        geo_name = None
        if geolocation_id:
            geolocations = await get_available_geolocations()
            for geo in geolocations:
                if geo.get('id') == geolocation_id:
                    geo_name = geo.get('name', "")
                    logger.info(f"Найдено название геолокации: {geo_name} для ID: {geolocation_id}")
                    break
        
        # Если геолокация не была выбрана, получаем текущую
        if not geolocation_id:
            logger.info("Геолокация не была выбрана, получаем текущую")
            config = await get_user_config(user_id)
            if config and "geolocation_id" in config:
                geolocation_id = config.get("geolocation_id")
                geo_name = config.get("geolocation_name", "Неизвестно")
                logger.info(f"Используем текущую геолокацию: {geo_name} (ID: {geolocation_id})")
        
        # Экранируем имя геолокации
        safe_geo_name = html.escape(geo_name) if geo_name else ""
        
        # Информация о выбранной геолокации для отображения
        geo_info = f"\nГеолокация: <b>{safe_geo_name}</b>" if safe_geo_name else ""
        
        # Дополнительное логирование
        logger.info(f"Пересоздание конфигурации для пользователя {user_id}, геолокация: {geo_name} (ID: {geolocation_id})")
        
        # Сообщаем пользователю о начале процесса пересоздания
        await bot.edit_message_text(
            f"🔄 <b>Пересоздание конфигурации...</b>{geo_info}\n\n"
            f"Пожалуйста, подождите. Это может занять несколько секунд.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Отправляем запрос на пересоздание конфигурации
        logger.info(f"Вызываем функцию recreate_config с параметрами: user_id={user_id}, geolocation_id={geolocation_id}")
        config_data = await recreate_config(user_id, geolocation_id=geolocation_id)
        logger.info(f"Результат recreate_config: {config_data}")
        
        if "error" in config_data:
            error_message = html.escape(config_data['error'])
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
                "❌ <b>Ошибка при пересоздании конфигурации</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем данные о сроке действия из базы данных
        db_data = await get_user_config(user_id)
        logger.info(f"Полученные данные из БД после пересоздания: {db_data}")
        
        expiry_text = ""
        if db_data:
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                try:
                    expiry_dt = datetime.fromisoformat(expiry_time)
                    expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                    expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
                except (ValueError, TypeError):
                    pass
            
            # Если геолокация не была указана явно, получаем её из обновленной конфигурации
            if not geo_name and "geolocation_name" in db_data:
                geo_name = db_data.get("geolocation_name", "")
                safe_geo_name = html.escape(geo_name)
                logger.info(f"Получена геолокация из обновленной конфигурации: {geo_name}")
        
        # Добавляем информацию о геолокации
        geo_text = f"▫️ Геолокация: <b>{safe_geo_name}</b>\n" if safe_geo_name else ""
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код
        qr_buffer = await generate_config_qr(config_text)
        
        # Обновляем сообщение об успешном пересоздании
        await bot.edit_message_text(
            f"✅ <b>Конфигурация успешно пересоздана!</b>\n\n"
            f"{geo_text}"
            f"{expiry_text}\n"
            f"Файл конфигурации и QR-код будут отправлены отдельными сообщениями.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        if qr_buffer:
            # Отправляем QR-код
            caption = "🔑 <b>QR-код вашей новой конфигурации WireGuard</b>\n\n"
            if safe_geo_name:
                caption += f"Геолокация: <b>{safe_geo_name}</b>\n\n"
            caption += "Отсканируйте этот код в приложении WireGuard для быстрой настройки."
            
            await bot.send_photo(
                user_id,
                qr_buffer,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем файл конфигурации
        caption = "📋 <b>Файл конфигурации WireGuard</b>\n\n"
        if safe_geo_name:
            caption += f"Геолокация: <b>{safe_geo_name}</b>\n\n"
        caption += "Импортируйте этот файл в приложение WireGuard для настройки соединения."
        
        await bot.send_document(
            user_id,
            config_file,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        # Отправляем напоминание
        reminder_text = (
            "⚠️ <b>Важное напоминание</b>\n\n"
            "Не забудьте обновить конфигурацию на всех ваших устройствах!\n"
            "Старая конфигурация больше не будет работать."
        )
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend")
        )
        
        await bot.send_message(
            user_id,
            reminder_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        error_message = html.escape(str(e))
        await bot.edit_message_text(
            f"❌ <b>Произошла ошибка</b>\n\n{error_message}",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

# Обработчик для отмены пересоздания конфигурации
async def cancel_recreate_config(callback_query: types.CallbackQuery):
    """Отмена процесса пересоздания конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    
    try:
        # Получаем данные о конфигурации
        user_id = callback_query.from_user.id
        config = await get_user_config(user_id)
        
        if config and config.get("active", False):
            try:
                expiry_time = config.get("expiry_time")
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                # Получаем информацию о геолокации
                geo_name = config.get("geolocation_name", "Неизвестно")
                safe_geo_name = html.escape(geo_name)
                geo_text = f"▫️ Геолокация: <b>{safe_geo_name}</b>\n" if geo_name else ""
                
                keyboard = InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
                    InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
                )
                keyboard.add(
                    InlineKeyboardButton("🌍 Изменить геолокацию", callback_data="choose_geo")
                )
                
                await bot.edit_message_text(
                    f"✅ <b>Текущая конфигурация сохранена</b>\n\n"
                    f"{geo_text}"
                    f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n\n"
                    f"Вы можете продлить срок действия, получить файл конфигурации снова "
                    f"или изменить геолокацию.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка при обработке даты: {str(e)}")
                # В случае ошибки при парсинге даты
                await bot.edit_message_text(
                    "✅ <b>Текущая конфигурация сохранена</b>\n\n"
                    "Пересоздание конфигурации отменено.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
        else:
            await bot.edit_message_text(
                "❌ Пересоздание конфигурации отменено.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id
            )
    except Exception as e:
        logger.error(f"Ошибка при отмене пересоздания: {str(e)}", exc_info=True)
        error_message = html.escape(str(e))
        await bot.edit_message_text(
            f"❌ <b>Произошла ошибка</b>\n\n{error_message}",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

def register_handlers_recreate(dp: Dispatcher):
    """Регистрирует обработчики для пересоздания конфигурации."""
    dp.register_callback_query_handler(recreate_config_handler, lambda c: c.data == 'recreate_config')
    dp.register_callback_query_handler(choose_geo_for_recreate, lambda c: c.data == 'recreate_choose_geo')
    dp.register_callback_query_handler(select_geo_for_recreate, lambda c: c.data.startswith('recreate_geo_'))
    dp.register_callback_query_handler(confirm_recreate_config, lambda c: c.data.startswith('confirm_recreate'))
    dp.register_callback_query_handler(cancel_recreate_config, lambda c: c.data == 'cancel_recreate')