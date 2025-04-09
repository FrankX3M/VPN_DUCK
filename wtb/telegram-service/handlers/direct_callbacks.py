from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO
import logging

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
        
    # Теперь проверим, есть ли в callback_query.data атрибут _handled
    if hasattr(callback_query, 'data') and hasattr(callback_query.data, '_handled') and callback_query.data._handled:
        logger.info("Колбэк уже обработан middleware через data, пропускаем")
        return
    
    # В случае если ни одна проверка не сработала, продолжаем обычную обработку
    logger.info("Обрабатываем колбэк в прямом обработчике")
    await bot.answer_callback_query(callback_query.id)
    
    # Остальной код обработчика остается без изменений
    # ...
    

# Прямой обработчик для отмены создания конфигурации
async def direct_cancel_handler(callback_query: types.CallbackQuery):
    """Обработчик прямой отмены создания."""
    logger.info(f"Вызван direct_cancel_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
        
    # Теперь проверим, есть ли в callback_query.data атрибут _handled
    if hasattr(callback_query, 'data') and hasattr(callback_query.data, '_handled') and callback_query.data._handled:
        logger.info("Колбэк уже обработан middleware через data, пропускаем")
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