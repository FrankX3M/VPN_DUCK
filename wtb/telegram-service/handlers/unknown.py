from aiogram import types, Dispatcher
from keyboards.keyboards import get_permanent_keyboard

# Обработчик для неизвестных команд и сообщений
async def unknown_message(message: types.Message):
    """Обработка неизвестных команд и сообщений."""
    # Проверяем, является ли сообщение командой
    if message.text.startswith('/'):
        await message.reply(
            "⚠️ Неизвестная команда.\n\n"
            "Используйте /help для получения списка доступных команд.",
            reply_markup=get_permanent_keyboard()
        )
    else:
        # Отвечаем на обычное сообщение
        await message.reply(
            "Я понимаю только определенные команды и кнопки.\n"
            "Используйте /help для получения списка доступных команд.",
            reply_markup=get_permanent_keyboard()
        )

def register_handlers_unknown(dp: Dispatcher):
    """Регистрирует обработчики для неизвестных сообщений."""
    # Этот обработчик должен быть зарегистрирован последним
    dp.register_message_handler(unknown_message)