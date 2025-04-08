from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from keyboards.keyboards import get_permanent_keyboard

# Универсальный обработчик отмены для FSM состояний
async def cancel_handler(message: types.Message, state: FSMContext):
    """Универсальный обработчик отмены для всех состояний."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        await message.reply(
            "❌ Операция отменена.\n\n"
            "Вы можете продолжить использование бота.",
            reply_markup=get_permanent_keyboard()
        )
    else:
        await message.reply(
            "В данный момент нет активных операций для отмены.",
            reply_markup=get_permanent_keyboard()
        )

def register_handlers_cancel(dp: Dispatcher):
    """Регистрирует обработчики отмены операций."""
    dp.register_message_handler(cancel_handler, commands=['cancel'], state='*')
    dp.register_message_handler(cancel_handler, Text(equals='отмена', ignore_case=True), state='*')