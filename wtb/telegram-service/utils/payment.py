import uuid
import logging
from aiogram.types import LabeledPrice
from core.settings import bot, logger

# Функция для создания invoice для оплаты звездами
async def create_stars_invoice(user_id, days, stars):
    """Создание invoice для оплаты звездами."""
    # Уникальный идентификатор платежа
    payment_id = str(uuid.uuid4())
    
    # Формируем информацию о платеже
    title = f"VPN Duck: {days} дней"
    description = f"Продление доступа к VPN через WireGuard на {days} дней"
    
    # Создаем invoice с использованием Stars
    prices = [LabeledPrice(label=f"Продление на {days} дней", amount=stars)]
    
    try:
        # Отправляем invoice
        await bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=f"extend_{user_id}_{days}_{stars}_{payment_id}",
            provider_token="",  # Пустая строка для цифровых товаров
            currency="XTR",     # XTR - валюта для звезд Telegram
            prices=prices,
            start_parameter=payment_id
        )
        
        return payment_id, title, description
    except Exception as e:
        logger.error(f"Ошибка при создании invoice: {str(e)}")
        raise e