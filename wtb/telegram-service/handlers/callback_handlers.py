from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from core.settings import bot, logger

# Универсальный обработчик неизвестных колбэков
async def process_unknown_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка неизвестных колбэков."""
    try:
        await bot.answer_callback_query(callback_query.id)
        callback_data = callback_query.data
        
        # Логируем неизвестный колбэк
        logger.info(f"Получен неизвестный колбэк: {callback_data}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке неизвестного колбэка: {str(e)}")
        await bot.send_message(
            callback_query.from_user.id,
            "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
        )

def register_handlers_callbacks(dp: Dispatcher):
    """Регистрирует обработчики для колбэков."""
    # Создайте список известных колбэков, которые должны обрабатываться специфическими обработчиками
    known_callbacks = ['confirm_create', 'cancel_create', 'create_config', 
                      'start_extend', 'confirm_recreate', 'cancel_recreate',
                      'status', 'get_config', 'recreate_config']
    
    # Регистрируем обработчик только для неизвестных колбэков
    dp.register_callback_query_handler(
        process_unknown_callback, 
        lambda c: c.data not in known_callbacks, 
        state='*'
    )