from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO

from core.settings import bot, logger
from keyboards.keyboards import get_recreate_confirm_keyboard
from utils.bd import recreate_config, get_user_config
from utils.qr import generate_config_qr

# Обработчик для пересоздания конфигурации
async def recreate_config_handler(callback_query: types.CallbackQuery):
    """Пересоздание конфигурации WireGuard."""
    await bot.answer_callback_query(callback_query.id)
    
    # Формируем клавиатуру для подтверждения пересоздания
    keyboard = get_recreate_confirm_keyboard()
    
    await bot.edit_message_text(
        "⚠️ <b>Пересоздание конфигурации WireGuard</b>\n\n"
        "Внимание! При пересоздании конфигурации:\n"
        "• Текущая конфигурация будет деактивирована\n"
        "• Вы получите новую конфигурацию с новыми ключами\n"
        "• Срок действия будет установлен на 7 дней\n\n"
        "Вам потребуется обновить настройки на всех ваших устройствах.\n\n"
        "Подтвердите пересоздание конфигурации:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

# Обработчик для подтверждения пересоздания конфигурации
async def confirm_recreate_config(callback_query: types.CallbackQuery):
    """Подтверждение пересоздания конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    # Сообщаем пользователю о начале процесса пересоздания
    await bot.edit_message_text(
        "🔄 <b>Пересоздание конфигурации...</b>\n\n"
        "Пожалуйста, подождите. Это может занять несколько секунд.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Отправляем запрос на пересоздание конфигурации
        config_data = await recreate_config(user_id)
        
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
                "❌ <b>Ошибка при пересоздании конфигурации</b>\n\n"
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
        
        # Обновляем сообщение об успешном пересоздании
        await bot.edit_message_text(
            f"✅ <b>Конфигурация успешно пересоздана!</b>\n\n"
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
                caption="🔑 <b>QR-код вашей новой конфигурации WireGuard</b>\n\n"
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
        await bot.edit_message_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

# Обработчик для отмены пересоздания конфигурации
async def cancel_recreate_config(callback_query: types.CallbackQuery):
    """Отмена процесса пересоздания конфигурации."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем данные о конфигурации
    user_id = callback_query.from_user.id
    config = await get_user_config(user_id)
    
    if config and config.get("active", False):
        expiry_time = config.get("expiry_time")
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        
        await bot.edit_message_text(
            f"✅ <b>Текущая конфигурация сохранена</b>\n\n"
            f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n\n"
            f"Вы можете продлить срок действия или получить файл конфигурации снова.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    else:
        await bot.edit_message_text(
            "❌ Пересоздание конфигурации отменено.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id
        )

def register_handlers_recreate(dp: Dispatcher):
    """Регистрирует обработчики для пересоздания конфигурации."""
    dp.register_callback_query_handler(recreate_config_handler, lambda c: c.data == 'recreate_config')
    dp.register_callback_query_handler(confirm_recreate_config, lambda c: c.data == 'confirm_recreate')
    dp.register_callback_query_handler(cancel_recreate_config, lambda c: c.data == 'cancel_recreate')