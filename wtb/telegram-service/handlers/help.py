from aiogram import types, Dispatcher
from aiogram.types import ParseMode

# Обработчик команды /help
async def send_help(message: types.Message):
    """Обрабатывает команду /help."""
    help_text = (
        "🦆 *VPN Duck - Справка*\n\n"
        "*Основные команды:*\n"
        "▫️ /start - Начать работу с ботом\n"
        "▫️ /create - Создать новую конфигурацию WireGuard\n"
        "▫️ /status - Проверить статус вашей конфигурации\n"
        "▫️ /extend - Продлить срок действия конфигурации\n"
        "▫️ /payments - Посмотреть историю платежей\n"
        "▫️ /stars_info - Информация о Telegram Stars\n"
        "▫️ /help - Показать это сообщение\n\n"
        
        "*О сервисе:*\n"
        "VPN Duck предоставляет вам доступ к безопасному VPN через протокол WireGuard. "
        "После создания конфигурации вы получите файл и QR-код для быстрой настройки на ваших устройствах.\n\n"
        
        "*Оплата:*\n"
        "Сервис использует Telegram Stars для оплаты. "
        "Для пополнения баланса звезд используйте официальный интерфейс Telegram.\n\n"
        
        "Если у вас возникли вопросы или проблемы, пожалуйста, свяжитесь с поддержкой."
    )
    
    await message.reply(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

def register_handlers_help(dp: Dispatcher):
    """Регистрирует обработчики для справки."""
    dp.register_message_handler(send_help, commands=['help'])
    dp.register_message_handler(send_help, lambda message: message.text == "ℹ️ Помощь")