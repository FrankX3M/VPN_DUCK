from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from aiogram.dispatcher import FSMContext
from datetime import datetime

from core.settings import bot, logger
from states.states import ExtendConfigStates
from keyboards.keyboards import get_extend_keyboard, get_status_keyboard
from utils.bd import get_user_config, extend_config
from utils.payment import create_stars_invoice

# Обработчик для начала процесса продления
async def extend_config_start(message: types.Message):
    """Начать процесс продления конфигурации."""
    user_id = message.from_user.id
    
    try:
        # Проверяем, есть ли у пользователя активная конфигурация
        config = await get_user_config(user_id)
        
        if not config or not config.get("active", False):
            await message.reply(
                "⚠️ *У вас нет активной конфигурации для продления!*\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Получаем данные о конфигурации
        expiry_time = config.get("expiry_time")
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        
        # Формируем клавиатуру с опциями продления
        keyboard = get_extend_keyboard()
        
        await message.reply(
            f"⏰ *Продление конфигурации WireGuard*\n\n"
            f"Текущий срок действия: до *{expiry_formatted}*\n\n"
            f"Выберите длительность продления:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
        # Переходим в состояние выбора длительности
        await ExtendConfigStates.selecting_duration.set()
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        await message.reply(
            "❌ *Ошибка при получении данных о конфигурации*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# Обработчик для inline-кнопки начала продления
async def start_extend_from_button(callback_query: types.CallbackQuery):
    """Начало процесса продления через inline кнопку."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем user_id из callback_query
    user_id = callback_query.from_user.id
    
    try:
        # Проверяем, есть ли у пользователя активная конфигурация
        config = await get_user_config(user_id)
        
        if not config or not config.get("active", False):
            await bot.send_message(
                user_id,
                "⚠️ *У вас нет активной конфигурации для продления!*\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Получаем данные о конфигурации
        expiry_time = config.get("expiry_time")
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        
        # Формируем клавиатуру с опциями продления
        keyboard = get_extend_keyboard()
        
        await bot.send_message(
            user_id,
            f"⏰ *Продление конфигурации WireGuard*\n\n"
            f"Текущий срок действия: до *{expiry_formatted}*\n\n"
            f"Выберите длительность продления:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
        # Переходим в состояние выбора длительности
        await ExtendConfigStates.selecting_duration.set()
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        await bot.send_message(
            user_id,
            "❌ *Ошибка при получении данных о конфигурации*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# Обработчик для выбора опции продления
async def process_extend_option(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбранной опции продления."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем параметры из callback_data
    _, days, stars = callback_query.data.split('_')
    days = int(days)
    stars = int(stars)
    
    # Сохраняем выбор пользователя в состояние
    await state.update_data(days=days, stars=stars)
    
    user_id = callback_query.from_user.id
    
    try:
        # Создаем платежную форму
        payment_id, title, description = await create_stars_invoice(
            user_id=user_id,
            days=days,
            stars=stars
        )
        
        # Обновляем сообщение с информацией о процессе оплаты
        await bot.edit_message_text(
            f"⏰ *Продление конфигурации WireGuard*\n\n"
            f"Вы выбрали продление на *{days} дней* за *{stars} ⭐*\n\n"
            f"Для оплаты используйте форму оплаты, отправленную выше.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Переходим в состояние подтверждения оплаты
        await ExtendConfigStates.confirming_payment.set()
    except Exception as e:
        logger.error(f"Ошибка при создании платежной формы: {str(e)}")
        await bot.edit_message_text(
            f"❌ *Ошибка при создании платежной формы*\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Сбрасываем состояние
        await state.finish()

# Обработчик для отмены продления
async def cancel_extend(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена процесса продления."""
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Продление конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    
    # Сбрасываем состояние
    await state.finish()

# Обработчик pre-checkout для подтверждения оплаты звездами
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    """Обработка pre-checkout запроса при оплате звездами."""
    try:
        # Получаем данные из payload
        payload = pre_checkout_query.invoice_payload
        _, user_id, days, stars, payment_id = payload.split('_')
        user_id = int(user_id)
        days = int(days)
        stars = int(stars)
        
        # Если все проверки пройдены, принимаем платеж
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=True
        )
        
        # Сохраняем данные о платеже в состоянии
        await state.update_data(
            payment_id=payment_id,
            days=days,
            stars=stars
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке pre-checkout: {str(e)}")
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message="Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
        )

# Обработчик успешного платежа звездами
async def process_successful_payment(message: types.Message, state: FSMContext):
    """Обработка успешного платежа звездами."""
    # Получаем данные из состояния
    data = await state.get_data()
    payment_id = data.get('payment_id')
    days = data.get('days')
    stars = data.get('stars')
    
    # Получаем информацию о транзакции
    payment_info = message.successful_payment
    transaction_id = payment_info.telegram_payment_charge_id
    
    # Получаем user_id
    user_id = message.from_user.id
    
    try:
        # Отправляем запрос на продление конфигурации
        result = await extend_config(user_id, days, stars, transaction_id)
        
        if "error" in result:
            await message.reply(
                f"❌ *Ошибка!*\n\n{result['error']}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Получаем обновленные данные о конфигурации
            config = await get_user_config(user_id)
            
            if config and config.get("active", False):
                expiry_time = config.get("expiry_time")
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                # Создаем клавиатуру для проверки статуса
                keyboard = get_status_keyboard()
                
                await message.reply(
                    f"✅ *Конфигурация успешно продлена!*\n\n"
                    f"▫️ Продление: *{days} дней*\n"
                    f"▫️ Оплачено: *{stars} ⭐*\n"
                    f"▫️ Действует до: *{expiry_formatted}*\n\n"
                    f"Спасибо за использование нашего сервиса!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await message.reply(
                    f"✅ *Конфигурация успешно продлена на {days} дней!*\n\n"
                    f"Оплачено: *{stars} ⭐*\n\n"
                    f"Для просмотра обновленной информации используйте команду /status.",
                    parse_mode=ParseMode.MARKDOWN
                )
    except Exception as e:
        logger.error(f"Ошибка при обработке платежа: {str(e)}")
        await message.reply(
            "❌ *Ошибка при обработке платежа*\n\n"
            "Пожалуйста, свяжитесь с поддержкой для решения проблемы.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Сбрасываем состояние
    await state.finish()

def register_handlers_extend(dp: Dispatcher):
    """Регистрирует обработчики для продления конфигурации."""
    dp.register_message_handler(extend_config_start, commands=['extend'])
    dp.register_message_handler(extend_config_start, lambda message: message.text == "⏰ Продлить")
    dp.register_callback_query_handler(start_extend_from_button, lambda c: c.data == 'start_extend')
    dp.register_callback_query_handler(process_extend_option, lambda c: c.data.startswith('extend_'), state=ExtendConfigStates.selecting_duration)
    dp.register_callback_query_handler(cancel_extend, lambda c: c.data == 'cancel_extend', state=[ExtendConfigStates.selecting_duration, ExtendConfigStates.confirming_payment])
    dp.register_pre_checkout_query_handler(process_pre_checkout, state=ExtendConfigStates.confirming_payment)
    dp.register_message_handler(process_successful_payment, content_types=types.ContentTypes.SUCCESSFUL_PAYMENT, state=ExtendConfigStates.confirming_payment)