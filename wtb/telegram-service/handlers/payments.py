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
                f"❌ {result['error']}"
            )
            return
        
        payments = result.get("payments", [])
        
        if not payments:
            await message.reply(
                "📊 <b>История платежей</b>\n\n"
                "У вас еще нет платежей за продление конфигурации.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Формируем сообщение с историей платежей
        history_text = "📊 <b>История платежей</b>\n\n"
        
        for i, payment in enumerate(payments[:10], 1):  # Ограничиваем 10 последними платежами
            created_at = datetime.fromisoformat(payment["created_at"]).strftime("%d.%m.%Y %H:%M")
            history_text += (
                f"<b>{i}.</b> {created_at}\n"
                f"▫️ Продление: <b>{payment['days_extended']} дней</b>\n"
                f"▫️ Оплачено: <b>{payment['stars_amount']} ⭐</b>\n"
                f"▫️ Статус: <b>{payment['status']}</b>\n\n"
            )
        
        await message.reply(
            history_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при получении истории платежей: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

def register_handlers_payments(dp: Dispatcher):
    """Регистрирует обработчики для истории платежей."""
    dp.register_message_handler(get_payment_history_handler, commands=['payments'])
    dp.register_message_handler(get_payment_history_handler, lambda message: message.text == "💳 История платежей")