from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton

from core.settings import bot

# Обработчик для показа информации о Telegram Stars через callback
async def stars_info_callback(callback_query: types.CallbackQuery):
    """Информация о Telegram Stars через callback."""
    await bot.answer_callback_query(callback_query.id)
    
    info_text = (
        "⭐ *Telegram Stars - Информация*\n\n"
        "Telegram Stars - это виртуальная валюта Telegram, которую можно использовать для покупки "
        "цифровых товаров и услуг в экосистеме Telegram.\n\n"
        "С помощью Stars вы можете:\n"
        "• Продлевать ваш доступ к VPN-сервису\n"
        "• Отправлять подарки создателям контента\n"
        "• Покупать товары и услуги в ботах\n\n"
        "Для пополнения баланса Stars, используйте официальный интерфейс Telegram."
    )
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⏰ Продлить VPN", callback_data="start_extend")
    )
    
    await bot.edit_message_text(
        info_text,
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# Обработчик команды для информации о Stars
async def stars_info_command(message: types.Message):
    """Информация о Telegram Stars через команду."""
    info_text = (
        "⭐ *Telegram Stars - Информация*\n\n"
        "Telegram Stars - это виртуальная валюта Telegram, которую можно использовать для покупки "
        "цифровых товаров и услуг в экосистеме Telegram.\n\n"
        "С помощью Stars вы можете:\n"
        "• Продлевать ваш доступ к VPN-сервису\n"
        "• Отправлять подарки создателям контента\n"
        "• Покупать товары и услуги в ботах\n\n"
        "Для пополнения баланса Stars, используйте официальный интерфейс Telegram."
    )
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⏰ Продлить VPN", callback_data="start_extend")
    )
    
    await message.reply(
        info_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# Обработчик для пополнения баланса звезд
async def topup_stars(callback_query: types.CallbackQuery):
    """Пополнение баланса звезд."""
    await bot.answer_callback_query(callback_query.id)
    
    # Информационное сообщение о пополнении звезд
    await bot.edit_message_text(
        "💵 *Пополнение баланса Telegram Stars*\n\n"
        "Для пополнения баланса звезд Telegram, пожалуйста, воспользуйтесь официальным интерфейсом Telegram.\n\n"
        "1. Откройте любой чат\n"
        "2. Нажмите на кнопку прикрепления (скрепка)\n"
        "3. Выберите пункт \"⭐️ Stars\"\n"
        "4. Следуйте инструкциям для пополнения баланса",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN
    )

def register_handlers_stars_info(dp: Dispatcher):
    """Регистрирует обработчики для информации о Stars."""
    dp.register_message_handler(stars_info_command, commands=['stars_info'])
    dp.register_callback_query_handler(stars_info_callback, lambda c: c.data == 'show_stars_info')
    dp.register_callback_query_handler(topup_stars, lambda c: c.data == 'topup_stars')