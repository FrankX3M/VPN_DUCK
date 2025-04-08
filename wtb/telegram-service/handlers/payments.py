from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from datetime import datetime

from core.settings import bot, logger
from utils.bd import get_payment_history

# Обработчик для истории платежей
async def get_payment_history_handler(message: types.Message):
    """Получение истории платежей пользователя."""
    user_id = message.from_user.id
    
    try:
        # Запрашиваем историю платежей
        result = await get_payment_history(user_id)
        
        if "error" in result:
            await message.reply(
                f"❌ {result['error']}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        payments = result.get("payments", [])
        
        if not payments:
            await message.reply(
                "📊 *История платежей*\n\n"
                "У вас еще нет платежей за продление конфигурации.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Формируем сообщение с историей платежей
        history_text = "📊 *История платежей*\n\n"
        
        for i, payment in enumerate(payments[:10], 1):  # Ограничиваем 10 последними платежами
            created_at = datetime.fromisoformat(payment["created_at"]).strftime("%d.%m.%Y %H:%M")
            history_text += (
                f"*{i}.* {created_at}\n"
                f"▫️ Продление: *{payment['days_extended']} дней*\n"
                f"▫️ Оплачено: *{payment['stars_amount']} ⭐*\n"
                f"▫️ Статус: *{payment['status']}*\n\n"
            )
        
        await message.reply(
            history_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Ошибка при получении истории платежей: {str(e)}")
        await message.reply(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

def register_handlers_payments(dp: Dispatcher):
    """Регистрирует обработчики для истории платежей."""
    dp.register_message_handler(get_payment_history_handler, commands=['payments'])
    dp.register_message_handler(get_payment_history_handler, lambda message: message.text == "💳 История платежей")