import os
import logging
import requests
import json
import uuid
from datetime import datetime, timedelta
import asyncio
import qrcode
from io import BytesIO

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, Invoice
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token from environment variable
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
WIREGUARD_SERVICE_URL = os.getenv('WIREGUARD_SERVICE_URL')
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL')

# Initialize bot and dispatcher with FSM storage
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Создаем состояния для FSM (машина состояний)
class ExtendConfigStates(StatesGroup):
    selecting_duration = State()
    confirming_payment = State()

# Константы для продления
EXTEND_OPTIONS = [
    {"days": 7, "stars": 500, "label": "7 дней - 500 ⭐"},
    {"days": 30, "stars": 1800, "label": "30 дней - 1800 ⭐"},
    {"days": 90, "stars": 5000, "label": "90 дней - 5000 ⭐"},
    {"days": 365, "stars": 18000, "label": "365 дней - 18000 ⭐"}
]

# Existing functions like get_permanent_keyboard(), send_welcome(), etc. remain the same...

# Функция для получения баланса Telegram Stars
async def get_stars_balance(user_id):
    """Получение баланса Telegram Stars пользователя."""
    try:
        # Используем Stars API для получения баланса
        result = await bot.get_stars_balance(user_id)
        return result.stars_amount
    except Exception as e:
        logger.error(f"Ошибка при получении баланса звезд: {str(e)}")
        return 0  # В случае ошибки возвращаем 0

# Функция для создания invoice для оплаты звездами
async def create_stars_invoice(user_id, days, stars):
    """Создание invoice для оплаты звездами."""
    # Уникальный идентификатор платежа
    payment_id = str(uuid.uuid4())
    
    # Формируем информацию о платеже
    title = f"Продление WireGuard на {days} дней"
    description = f"Продление доступа к VPN через WireGuard на {days} дней"
    
    # Создаем invoice с использованием Stars
    prices = [LabeledPrice(label=f"Продление на {days} дней", amount=stars)]
    
    try:
        # Создаем invoice для оплаты звездами
        invoice = await bot.create_invoice(
            title=title,
            description=description,
            payload=f"extend_{user_id}_{days}_{stars}_{payment_id}",
            provider_token="stars",  # Указываем, что используем Stars
            currency="STARS",  # Валюта - звезды
            prices=prices,
            max_tip_amount=0,
            suggested_tip_amounts=[],
            start_parameter=payment_id,
            provider_data=None
        )
        
        return payment_id, title, description, invoice
    except Exception as e:
        logger.error(f"Ошибка при создании invoice: {str(e)}")
        raise e

# Обработчик pre-checkout для подтверждения оплаты звездами
@dp.pre_checkout_query_handler(lambda query: True, state=ExtendConfigStates.confirming_payment)
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    """Обработка pre-checkout запроса при оплате звездами."""
    try:
        # Получаем данные из payload
        payload = pre_checkout_query.invoice_payload
        _, user_id, days, stars, payment_id = payload.split('_')
        user_id = int(user_id)
        days = int(days)
        stars = int(stars)
        
        # Проверяем, достаточно ли у пользователя звезд
        user_balance = await get_stars_balance(user_id)
        
        if user_balance < stars:
            # Если недостаточно звезд, отклоняем платеж
            await bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="На вашем счету недостаточно звезд для оплаты. Пожалуйста, пополните баланс."
            )
            return
        
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
@dp.message_handler(content_types=types.ContentTypes.SUCCESSFUL_PAYMENT, state=ExtendConfigStates.confirming_payment)
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
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/config/extend",
            json={
                "user_id": user_id,
                "days": days,
                "stars_amount": stars,
                "transaction_id": transaction_id
            }
        )
        
        if response.status_code == 200:
            # Получаем обновленные данные о конфигурации
            config_response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}")
            
            if config_response.status_code == 200:
                config_data = config_response.json()
                expiry_time = config_data.get("expiry_time")
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                # Создаем клавиатуру для проверки статуса
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    InlineKeyboardButton("📊 Проверить статус", callback_data="status")
                )
                
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
        else:
            error_message = "Ошибка при продлении конфигурации. Обратитесь в поддержку."
            if "error" in response.json():
                error_message = response.json().get("error")
            
            await message.reply(
                f"❌ *Ошибка!*\n\n{error_message}",
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

# Обработчик для выбора опции продления
@dp.callback_query_handler(lambda c: c.data.startswith('extend_'), state=ExtendConfigStates.selecting_duration)
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
    
    # Проверка баланса пользователя
    user_balance = await get_stars_balance(user_id)
    
    if user_balance < stars:
        # Если у пользователя недостаточно звезд, предлагаем пополнить баланс
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("💵 Пополнить баланс звезд", callback_data="topup_stars")
        )
        keyboard.add(
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_extend")
        )
        
        await bot.edit_message_text(
            f"⚠️ *Недостаточно звезд для продления*\n\n"
            f"Для продления на {days} дней требуется {stars} ⭐\n"
            f"Ваш текущий баланс: {user_balance} ⭐\n\n"
            f"Пожалуйста, пополните баланс звезд.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    try:
        # Создаем платежную форму
        payment_id, title, description, invoice = await create_stars_invoice(
            user_id=user_id,
            days=days,
            stars=stars
        )
        
        # Создаем сообщение с инвойсом
        await bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=f"extend_{user_id}_{days}_{stars}_{payment_id}",
            provider_token="stars",  # Используем Stars
            currency="STARS",
            prices=[LabeledPrice(label=f"Продление на {days} дней", amount=stars)],
            max_tip_amount=0,
            suggested_tip_amounts=[],
            start_parameter=payment_id,
            provider_data=None,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
            disable_notification=False,
            protect_content=False,
            reply_markup=None
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

# Обработчик для пополнения баланса звезд
@dp.callback_query_handler(lambda c: c.data == 'topup_stars')
async def topup_stars(callback_query: types.CallbackQuery):
    """Пополнение баланса звезд."""
    await bot.answer_callback_query(callback_query.id)
    
    # Здесь должна быть интеграция с Telegram Stars API для пополнения баланса
    # Согласно документации, используется метод payments.getStarsTopupOptions
    # и далее payments.getPaymentForm с inputInvoiceStars
    
    # В данном примере просто показываем информационное сообщение
    await bot.edit_message_text(
        "💵 *Пополнение баланса Telegram Stars*\n\n"
        "Для пополнения баланса звезд Telegram, пожалуйста, воспользуйтесь официальным интерфейсом Telegram.\n\n"
        "1. Откройте любой чат\n"
        "2. Нажмите на кнопку прикрепления (скрепка)\n"
        "3. Выберите пункт \"⭐️ Stars\"\n"
        "4. Следуйте инструкциям для пополнения баланса",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN
    )

# Обработчик для показа информации о Telegram Stars
@dp.callback_query_handler(lambda c: c.data == 'show_stars_info')
@dp.message_handler(commands=['stars_info'])
async def stars_info(message: types.Message):
    """Информация о Telegram Stars."""
    # Проверяем, откуда пришел запрос - от callback или от команды
    is_callback = False
    if not isinstance(message, types.Message):
        is_callback = True
        callback_query = message
        await bot.answer_callback_query(callback_query.id)
        message = callback_query.message
    
    info_text = (
        "⭐ *Telegram Stars - Информация*\n\n"
        "Telegram Stars - это виртуальная валюта Telegram, которую можно использовать для покупки "
        "цифровых товаров и услуг в экосистеме Telegram.\n\n"
        "С помощью Stars вы можете:\n"
        "• Продлевать ваш доступ к VPN-сервису\n"
        "• Отправлять подарки создателям контента\n"
        "• Покупать товары и услуги в ботах\n\n"
        "Для пополнения баланса Stars, используйте официальный интерфейс Telegram."
    )
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⏰ Продлить VPN", callback_data="start_extend")
    )
    
    if is_callback:
        await bot.edit_message_text(
            info_text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        await message.reply(
            info_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

# Обработчик для отмены продления
@dp.callback_query_handler(lambda c: c.data == 'cancel_extend', state=[ExtendConfigStates.selecting_duration, ExtendConfigStates.confirming_payment])
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

# Обработчик для начала процесса продления
@dp.message_handler(commands=['extend'])
@dp.message_handler(lambda message: message.text == "⏰ Продлить")
async def extend_config_start(message: types.Message):
    """Начать процесс продления конфигурации."""
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя активная конфигурация
    response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}")
    
    if response.status_code != 200 or not response.json().get("active", False):
        await message.reply(
            "⚠️ *У вас нет активной конфигурации для продления!*\n\n"
            "Сначала создайте конфигурацию с помощью команды /create.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Получаем данные о конфигурации
    config_data = response.json()
    expiry_time = config_data.get("expiry_time")
    expiry_dt = datetime.fromisoformat(expiry_time)
    expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
    
    # Формируем клавиатуру с опциями продления
    keyboard = InlineKeyboardMarkup(row_width=1)
    for option in EXTEND_OPTIONS:
        keyboard.add(
            InlineKeyboardButton(
                option["label"],
                callback_data=f"extend_{option['days']}_{option['stars']}"
            )
        )
    
    # Добавляем кнопку для отмены
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_extend"))
    
    await message.reply(
        f"⏰ *Продление конфигурации WireGuard*\n\n"
        f"Текущий срок действия: до *{expiry_formatted}*\n\n"
        f"Выберите длительность продления:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    
    # Переходим в состояние выбора длительности
    await ExtendConfigStates.selecting_duration.set()

# Обработчик для inline-кнопки начала продления
@dp.callback_query_handler(lambda c: c.data == 'start_extend')
async def start_extend_from_button(callback_query: types.CallbackQuery):
    """Начало процесса продления через inline кнопку."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем user_id из callback_query
    user_id = callback_query.from_user.id
    
    # Проверяем, есть ли у пользователя активная конфигурация
    response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}")
    
    if response.status_code != 200 or not response.json().get("active", False):
        await bot.send_message(
            user_id,
            "⚠️ *У вас нет активной конфигурации для продления!*\n\n"
            "Сначала создайте конфигурацию с помощью команды /create.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Получаем данные о конфигурации
    config_data = response.json()
    expiry_time = config_data.get("expiry_time")
    expiry_dt = datetime.fromisoformat(expiry_time)
    expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
    
    # Формируем клавиатуру с опциями продления
    keyboard = InlineKeyboardMarkup(row_width=1)
    for option in EXTEND_OPTIONS:
        keyboard.add(
            InlineKeyboardButton(
                option["label"],
                callback_data=f"extend_{option['days']}_{option['stars']}"
            )
        )
    
    # Добавляем кнопку для отмены
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_extend"))
    
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

# Обработчик для истории платежей
@dp.message_handler(commands=['payments'])
@dp.message_handler(lambda message: message.text == "💳 История платежей")
async def get_payment_history(message: types.Message):
    """Получение истории платежей пользователя."""
    user_id = message.from_user.id
    
    # Запрашиваем историю платежей
    response = requests.get(f"{DATABASE_SERVICE_URL}/payments/history/{user_id}")
    
    if response.status_code == 200:
        payments = response.json().get("payments", [])
        
        if not payments:
            await message.reply(
                "📊 *История платежей*\n\n"
                "У вас еще нет платежей за продление конфигурации.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Формируем сообщение с историей платежей
        history_text = "📊 *История платежей*\n\n"
        
        for i, payment in enumerate(payments[:10], 1):  # Ограничиваем 10 последними платежами
            created_at = datetime.fromisoformat(payment["created_at"]).strftime("%d.%m.%Y %H:%M")
            history_text += (
                f"*{i}.* {created_at}\n"
                f"▫️ Продление: *{payment['days_extended']} дней*\n"
                f"▫️ Оплачено: *{payment['stars_amount']} ⭐*\n"
                f"▫️ Статус: *{payment['status']}*\n\n"
            )
        
        await message.reply(
            history_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply(
            "❌ Не удалось получить историю платежей. Попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

# Обновление команд при старте бота
async def on_startup(dp):
    """Set up bot on startup."""
    logging.info("Bot started!")

    # Set commands for the bot menu
    commands = [
        types.BotCommand("create", "Создать конфигурацию"),
        types.BotCommand("extend", "Продлить конфигурацию"),
        types.BotCommand("status", "Проверить статус"),
        types.BotCommand("payments", "История платежей"),
        types.BotCommand("stars_info", "Информация о Telegram Stars"),
        types.BotCommand("help", "Показать справку")
    ]
    await bot.set_my_commands(commands)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)