from aiogram import types, Dispatcher
from aiogram.types import ParseMode

# Обработчик команды /help
async def send_help(message: types.Message):
    """Обрабатывает команду /help."""
    help_text = (
        "🦆 <b>VPN Duck - Справка</b>\n\n"
        "<b>Основные команды:</b>\n"
        "▫️ /start - Начать работу с ботом\n"
        "▫️ /create - Создать новую конфигурацию WireGuard\n"
        "▫️ /status - Проверить статус вашей конфигурации\n"
        "▫️ /extend - Продлить срок действия конфигурации\n"
        "▫️ /payments - Посмотреть историю платежей\n"
        "▫️ /stars_info - Информация о Telegram Stars\n"
        "▫️ /help - Показать это сообщение\n\n"
        
        "<b>О сервисе:</b>\n"
        "VPN Duck предоставляет вам доступ к безопасному VPN через протокол WireGuard. "
        "После создания конфигурации вы получите файл и QR-код для быстрой настройки на ваших устройствах.\n\n"
        
        "<b>Оплата:</b>\n"
        "Сервис использует Telegram Stars для оплаты. "
        "Для пополнения баланса звезд используйте официальный интерфейс Telegram.\n\n"
        
        "Если у вас возникли вопросы или проблемы, свяжитесь с поддержкой."
    )
    
    # Используем HTML форматирование вместо Markdown
    await message.reply(help_text, parse_mode=ParseMode.HTML)

def register_handlers_help(dp: Dispatcher):
    """Регистрирует обработчики для справки."""
    dp.register_message_handler(send_help, commands=['help'])
    dp.register_message_handler(send_help, lambda message: message.text == "ℹ️ Помощь")