from aiogram import types, Dispatcher
from aiogram.types import ParseMode
from aiogram.dispatcher import FSMContext
from datetime import datetime

from core.settings import bot, logger
from states.states import ExtendConfigStates
from keyboards.keyboards import get_extend_keyboard, get_status_keyboard
from utils.bd import get_user_config, extend_config
from utils.payment import create_stars_invoice

# Обработчик начала процесса продления
async def extend_config_start(message: types.Message):
    user_id = message.from_user.id

    try:
        config = await get_user_config(user_id)
        if not config or not config.get("active", False):
            await message.reply(
                "⚠️ <b>У вас нет активной конфигурации для продления!</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return

        expiry_time = config.get("expiry_time")
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        keyboard = get_extend_keyboard()

        await message.reply(
            f"⏰ <b>Продление конфигурации WireGuard</b>\n\n"
            f"Текущий срок действия: до <b>{expiry_formatted}</b>\n\n"
            f"Выберите длительность продления:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        await ExtendConfigStates.selecting_duration.set()

    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик inline-кнопки начала продления
async def start_extend_from_button(callback_query: types.CallbackQuery, state: FSMContext):
    if getattr(callback_query, '_handled', False):
        logger.info(f"Колбэк {callback_query.data} уже обработан, пропускаем")
        return

    logger.info(f"Вызван start_extend_from_button с callback_data: {callback_query.data}")
    await bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    try:
        config = await get_user_config(user_id)
        if not config or not config.get("active", False):
            await bot.send_message(
                user_id,
                "⚠️ <b>У вас нет активной конфигурации для продления!</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return

        expiry_time = config.get("expiry_time")
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        keyboard = get_extend_keyboard()

        await bot.send_message(
            user_id,
            f"⏰ <b>Продление конфигурации WireGuard</b>\n\n"
            f"Текущий срок действия: до <b>{expiry_formatted}</b>\n\n"
            f"Выберите длительность продления:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        await ExtendConfigStates.selecting_duration.set()

    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработка выбора опции продления
async def process_extend_option(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    _, days, stars = callback_query.data.split('_')
    days = int(days)
    stars = int(stars)
    await state.update_data(days=days, stars=stars)

    user_id = callback_query.from_user.id

    try:
        payment_id, title, description = await create_stars_invoice(user_id, days, stars)

        await bot.edit_message_text(
            f"⏰ <b>Продление конфигурации WireGuard</b>\n\n"
            f"Вы выбрали продление на <b>{days} дней</b> за <b>{stars} ⭐</b>\n\n"
            f"Для оплаты используйте форму оплаты, отправленную выше.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

        await ExtendConfigStates.confirming_payment.set()

    except Exception as e:
        logger.error(f"Ошибка при создании платежной формы: {str(e)}", exc_info=True)
        await bot.edit_message_text(
            f"❌ <b>Ошибка при создании платежной формы</b>\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        await state.finish()

# Отмена продления
async def cancel_extend(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await bot.edit_message_text(
        "❌ Продление конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )

    await state.finish()

# Pre-checkout
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    try:
        payload = pre_checkout_query.invoice_payload
        _, user_id, days, stars, payment_id = payload.split('_')
        user_id = int(user_id)
        days = int(days)
        stars = int(stars)

        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        await state.update_data(payment_id=payment_id, days=days, stars=stars)

    except Exception as e:
        logger.error(f"Ошибка при обработке pre-checkout: {str(e)}", exc_info=True)
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message="Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
        )

# Успешный платёж
# async def process_successful_payment(message: types.Message, state: FSMContext):
#     data = await state.get_data()
#     payment_id = data.get('payment_id')
#     days = data.get('days')
#     stars = data.get('stars')
#     payment_info = message.successful_payment
#     transaction_id = payment_info.telegram_payment_charge_id
#     user_id = message.from_user.id

#     try:
#         result = await extend_config(user_id, days, stars, transaction_id)

#         if "error" in result:
#             await message.reply(
#                 f"❌ <b>Ошибка!</b>\n\n{result['error']}",
#                 parse_mode=ParseMode.HTML
#             )
#         else:
#             config = await get_user_config(user_id)

#             if config and config.get("active", False):
#                 expiry_time = config.get("expiry_time")
#                 expiry_dt = datetime.fromisoformat(expiry_time)
#                 expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
#                 keyboard = get_status_keyboard()

#                 await message.reply(
#                     f"✅ <b>Конфигурация успешно продлена!</b>\n\n"
#                     f"▫️ Продление: <b>{days} дней</b>\n"
#                     f"▫️ Оплачено: <b>{stars} ⭐</b>\n"
#                     f"▫️ Действует до: <b>{expiry_formatted}</b>\n\n"
#                     f"Спасибо за использование нашего сервиса!",
#                     parse_mode=ParseMode.HTML,
#                     reply_markup=keyboard
#                 )
#             else:
#                 await message.reply(
#                     f"✅ <b>Конфигурация успешно продлена на {days} дней!</b>\n\n"
#                     f"Оплачено: <b>{stars} ⭐</b>\n\n"
#                     f"Для просмотра обновленной информации используйте команду /status.",
#                     parse_mode=ParseMode.HTML
#                 )
#     except Exception as e:
#         logger.error(f"Ошибка при обработке платежа: {str(e)}", exc_info=True)
#         await message.reply(
#             "❌ <b>Ошибка при обработке платежа</b>\n\n"
#             "Пожалуйста, свяжитесь с поддержкой для решения проблемы.",
#             parse_mode=ParseMode.HTML
#         )

#     await state.finish()
async def process_successful_payment(message: types.Message, state: FSMContext):
    """Обработка успешного платежа за продление."""
    data = await state.get_data()
    payment_id = data.get('payment_id')
    days = data.get('days')
    stars = data.get('stars')
    payment_info = message.successful_payment
    transaction_id = payment_info.telegram_payment_charge_id
    user_id = message.from_user.id
    
    logger.info(f"Обработка успешного платежа: пользователь {user_id}, {days} дней, {stars} звезд, ID транзакции: {transaction_id}")

    try:
        # Сообщаем пользователю о начале процесса продления
        processing_message = await message.reply(
            "🔄 <b>Обработка платежа и продление конфигурации...</b>\n\n"
            "Пожалуйста, подождите.",
            parse_mode=ParseMode.HTML
        )
        
        # Выполняем продление
        result = await extend_config(user_id, days, stars, transaction_id)
        
        if "error" in result:
            logger.error(f"Ошибка при продлении: {result['error']}")
            await message.reply(
                f"❌ <b>Ошибка!</b>\n\n{result['error']}\n\n"
                "Платеж был успешно обработан, но возникла проблема при продлении конфигурации.\n"
                "Пожалуйста, свяжитесь с поддержкой для решения проблемы.",
                parse_mode=ParseMode.HTML
            )
            
            # Сохраняем информацию о проблемном платеже для администратора
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,  # Требуется добавить в settings.py
                text=f"⚠️ <b>Проблемный платеж</b>\n\n"
                     f"Пользователь: {user_id}\n"
                     f"Продление: {days} дней\n"
                     f"Оплачено: {stars} ⭐\n"
                     f"Транзакция: {transaction_id}\n"
                     f"Ошибка: {result['error']}",
                parse_mode=ParseMode.HTML
            )
        else:
            # Получаем обновленную информацию о конфигурации
            config = await get_user_config(user_id)
            
            if config and config.get("active", False):
                try:
                    expiry_time = config.get("expiry_time")
                    expiry_dt = datetime.fromisoformat(expiry_time)
                    expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                    
                    # Рассчитываем оставшееся время
                    now = datetime.now()
                    remaining_time = expiry_dt - now
                    remaining_days = max(0, remaining_time.days)
                    remaining_hours = max(0, remaining_time.seconds // 3600)
                    
                    keyboard = get_status_keyboard()
                    
                    await message.reply(
                        f"✅ <b>Конфигурация успешно продлена!</b>\n\n"
                        f"▫️ Продление: <b>{days} дней</b>\n"
                        f"▫️ Оплачено: <b>{stars} ⭐</b>\n"
                        f"▫️ Действует до: <b>{expiry_formatted}</b>\n"
                        f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n\n"
                        f"Спасибо за использование нашего сервиса!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
                except (ValueError, TypeError) as e:
                    logger.error(f"Ошибка при обработке даты: {str(e)}")
                    await message.reply(
                        f"✅ <b>Конфигурация успешно продлена на {days} дней!</b>\n\n"
                        f"Оплачено: <b>{stars} ⭐</b>\n\n"
                        f"Для просмотра обновленной информации используйте команду /status.",
                        parse_mode=ParseMode.HTML
                    )
            else:
                await message.reply(
                    f"✅ <b>Платеж успешно обработан!</b>\n\n"
                    f"Оплачено: <b>{stars} ⭐</b> за <b>{days} дней</b>\n\n"
                    f"Однако, не удалось найти активную конфигурацию. "
                    f"Пожалуйста, создайте новую с помощью команды /create.",
                    parse_mode=ParseMode.HTML
                )
        
        # Удаляем сообщение о обработке
        try:
            await bot.delete_message(chat_id=processing_message.chat.id, message_id=processing_message.message_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {str(e)}")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке платежа: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Ошибка при обработке платежа</b>\n\n"
            "Пожалуйста, свяжитесь с поддержкой для решения проблемы. "
            "Сохраните ID транзакции для подтверждения оплаты.",
            parse_mode=ParseMode.HTML
        )
        
        # Сохраняем информацию о проблемном платеже для администратора
        try:
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,  # Требуется добавить в settings.py
                text=f"⚠️ <b>Критическая ошибка платежа</b>\n\n"
                     f"Пользователь: {user_id}\n"
                     f"Продление: {days} дней\n"
                     f"Оплачено: {stars} ⭐\n"
                     f"Транзакция: {transaction_id}\n"
                     f"Ошибка: {str(e)}",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            logger.error("Не удалось отправить уведомление администратору", exc_info=True)

    # Завершаем состояние FSM
    await state.finish()
    
# Регистрируем все обработчики продления
def register_handlers_extend(dp: Dispatcher):
    dp.register_message_handler(extend_config_start, commands=['extend'])
    dp.register_message_handler(extend_config_start, lambda message: message.text == "⏰ Продлить")

    dp.register_callback_query_handler(start_extend_from_button, lambda c: c.data == 'start_extend', state='*')
    dp.register_callback_query_handler(process_extend_option, lambda c: c.data.startswith('extend_'), state=ExtendConfigStates.selecting_duration)
    dp.register_callback_query_handler(cancel_extend, lambda c: c.data == 'cancel_extend', state=[ExtendConfigStates.selecting_duration, ExtendConfigStates.confirming_payment])
    dp.register_pre_checkout_query_handler(process_pre_checkout, state=ExtendConfigStates.confirming_payment)
    dp.register_message_handler(process_successful_payment, content_types=types.ContentTypes.SUCCESSFUL_PAYMENT, state=ExtendConfigStates.confirming_payment)
