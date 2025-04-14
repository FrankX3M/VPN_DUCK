from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from core.settings import bot, logger

# Универсальный обработчик неизвестных колбэков
async def process_unknown_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка неизвестных колбэков."""
    try:
        await bot.answer_callback_query(callback_query.id)
        callback_data = callback_query.data
        
        # Детальное логирование для отладки
        logger.warning(f"Получен неизвестный колбэк: {callback_data}")
        current_state = await state.get_state()
        logger.warning(f"Текущее состояние: {current_state}")
        
        # Не отправляем сообщение пользователю, чтобы не спамить
        
    except Exception as e:
        logger.error(f"Ошибка при обработке неизвестного колбэка: {str(e)}")
        await bot.send_message(
            callback_query.from_user.id,
            "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
        )

# def register_handlers_callbacks(dp: Dispatcher):
#     """Регистрирует обработчики для колбэков."""
#     # Создаем список известных колбэков и их префиксов
#     known_callbacks = [
#         'confirm_create', 'cancel_create', 'create_config', 
#         'start_extend', 'confirm_recreate', 'cancel_recreate',
#         'status', 'get_config', 'recreate_config',
#         'show_stars_info', 'topup_stars', 'cancel_extend'
#     ]
    
#     known_prefixes = [
#         'extend_'  # Для колбэков с переменными частями
#     ]
    
#     # Регистрируем обработчик только для неизвестных колбэков
#     dp.register_callback_query_handler(
#         process_unknown_callback, 
#         lambda c: c.data not in known_callbacks and not any(c.data.startswith(prefix) for prefix in known_prefixes), 
#         state='*'
#     )

def register_handlers_callbacks(dp: Dispatcher):
    """Регистрирует обработчики для колбэков."""
    # Создаем список известных колбэков и их префиксов
    known_callbacks = [
        'confirm_create', 'cancel_create', 'create_config', 
        'start_extend', 'confirm_recreate', 'cancel_recreate',
        'status', 'get_config', 'recreate_config',
        'show_stars_info', 'topup_stars', 'cancel_extend',
        'choose_geo', 'back_to_main', 'get_all_configs', 'cancel_geo'  # Добавляем новые колбэки
    ]
    
    known_prefixes = [
        'extend_',  # Для колбэков продления
        'geo_'      # Для колбэков геолокаций
    ]
    
    # Регистрируем обработчик только для неизвестных колбэков
    dp.register_callback_query_handler(
        process_unknown_callback, 
        lambda c: c.data not in known_callbacks and not any(c.data.startswith(prefix) for prefix in known_prefixes), 
        state='*'
    )