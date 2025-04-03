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
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(level=logging.INFO)

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

# Create a permanent keyboard that will be shown all the time
def get_permanent_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton("🔑 Создать конфигурацию"),
        KeyboardButton("⏰ Продлить")
    )
    keyboard.row(
        KeyboardButton("📊 Статус"),
        KeyboardButton("ℹ️ Помощь")
    )
    keyboard.row(
        KeyboardButton("📥 Скачать WireGuard"),
        KeyboardButton("💳 История платежей")
    )
    return keyboard

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Send welcome message when /start command is issued."""
    welcome_text = (
        "🔐 *Добро пожаловать в WireGuard Бот!* 🔐\n\n"
        "Этот бот поможет вам управлять вашей WireGuard конфигурацией.\n\n"
        "Используйте кнопки ниже для управления:"
    )
    
    # Create inline keyboard for quick access
    inline_keyboard = InlineKeyboardMarkup(row_width=1)
    inline_keyboard.add(
        InlineKeyboardButton("📥 Скачать WireGuard", url="https://www.wireguard.com/install/"),
        InlineKeyboardButton("📘 Руководство пользователя", url="https://www.wireguard.com/quickstart/")
    )
    
    # Send welcome message with both keyboards
    await message.reply(
        welcome_text, 
        parse_mode=ParseMode.MARKDOWN, 
        reply_markup=inline_keyboard
    )
    
    # Set the permanent keyboard
    await message.answer(
        "Управление ботом:", 
        reply_markup=get_permanent_keyboard()
    )

@dp.message_handler(commands=['help'])
@dp.message_handler(lambda message: message.text == "ℹ️ Помощь")
async def send_help(message: types.Message):
    """Send help information when /help command is issued."""
    help_text = (
        "🔐 *WireGuard Бот - Справка* 🔐\n\n"
        "*Доступные команды:*\n\n"
        "🔹 `/create` или кнопка *🔑 Создать конфигурацию* - создать новую конфигурацию WireGuard (действует 24 часа)\n"
        "🔹 `/extend` или кнопка *⏰ Продлить* - продлить срок действия конфигурации WireGuard\n"
        "🔹 `/status` или кнопка *📊 Статус* - проверить статус вашей конфигурации\n"
        "🔹 `/payments` или кнопка *💳 История платежей* - просмотреть историю платежей\n"
        "🔹 `/stars_info` - информация о Telegram Stars\n"
        "🔹 `/help` или кнопка *ℹ️ Помощь* - показать это сообщение\n\n"
        "📥 Скачайте актуальную версию WireGuard для вашего устройства:\n"
        "[wireguard.com/install](https://www.wireguard.com/install/)"
    )
    
    # Add an inline keyboard with useful links
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            text="📱 Установка WireGuard", 
            url="https://www.wireguard.com/install/"
        ),
        InlineKeyboardButton(
            text="📘 Руководство пользователя", 
            url="https://www.wireguard.com/quickstart/"
        ),
        InlineKeyboardButton(
            text="⭐ О Telegram Stars", 
            callback_data="show_stars_info"
        )
    )
    
    await message.reply(
        help_text, 
        parse_mode=ParseMode.MARKDOWN, 
        reply_markup=keyboard
    )

@dp.message_handler(lambda message: message.text == "📥 Скачать WireGuard")
async def download_wireguard(message: types.Message):
    """Send WireGuard download info."""
    download_text = (
        "📥 *Скачать WireGuard* 📥\n\n"
        "Выберите вашу платформу для загрузки:"
    )
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🍎 iOS", url="https://itunes.apple.com/us/app/wireguard/id1441195209"),
        InlineKeyboardButton("🤖 Android", url="https://play.google.com/store/apps/details?id=com.wireguard.android")
    )
    keyboard.add(
        InlineKeyboardButton("🪟 Windows", url="https://download.wireguard.com/windows-client/wireguard-installer.exe"),
        InlineKeyboardButton("🍏 macOS", url="https://itunes.apple.com/us/app/wireguard/id1451685025")
    )
    keyboard.add(
        InlineKeyboardButton("🐧 Linux", url="https://www.wireguard.com/install/#ubuntu-module-tools")
    )
    
    await message.reply(
        download_text, 
        parse_mode=ParseMode.MARKDOWN, 
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data in ['create', 'status'])
async def process_callback(callback_query: types.CallbackQuery):
    """Process callback buttons."""
    if callback_query.data == 'create':
        await bot.answer_callback_query(callback_query.id)
        await create_config(callback_query.message)
    elif callback_query.data == 'status':
        await bot.answer_callback_query(callback_query.id)
        await check_status(callback_query.message)

@dp.message_handler(commands=['create'])
@dp.message_handler(lambda message: message.text == "🔑 Создать конфигурацию")
async def create_config(message: types.Message):
    """Create a new WireGuard configuration."""
    # If message is from callback, extract user_id from the original message
    if hasattr(message, 'reply_to_message') and message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        user_id = message.from_user.id
    
    # Check if user already has an active configuration
    response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}")
    
    if response.status_code == 200 and response.json().get("active", False):
        # User already has an active configuration
        expiry_time = response.json().get("expiry_time")
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        
        # Создаем inline-клавиатуру с опцией продления
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend")
        )
        
        await message.reply(
            f"⚠️ *У вас уже есть активная конфигурация!*\n\n"
            f"Она истекает: `{expiry_formatted}`\n\n"
            f"Вы можете продлить срок действия конфигурации или использовать /status для получения деталей.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    # Request new configuration from WireGuard service
    wireguard_response = requests.post(
        f"{WIREGUARD_SERVICE_URL}/create",
        json={"user_id": user_id}
    )
    
    if wireguard_response.status_code == 201:
        config_data = wireguard_response.json()
        config_text = config_data.get("config")
        
        # Calculate expiry time (24 hours from now)
        expiry_time = (datetime.now() + timedelta(hours=24)).isoformat()
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
        
        # Save configuration to database
        db_response = requests.post(
            f"{DATABASE_SERVICE_URL}/config",
            json={
                "user_id": user_id,
                "config": config_text,
                "expiry_time": expiry_time,
                "active": True
            }
        )
        
        if db_response.status_code == 201:
            # Send configuration to user
            await message.reply(
                f"✅ *Конфигурация WireGuard создана!*\n\n"
                f"🕒 Действует до: `{expiry_formatted}`\n\n"
                f"```\n{config_text}\n```",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(config_text)
            qr.make(fit=True)
            
            # Create an image from the QR Code
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save the image to a bytes buffer
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Send QR code as photo
            await bot.send_photo(
                chat_id=user_id,
                photo=buffer,
                caption="📱 QR-код с конфигурацией WireGuard. Отсканируйте его в приложении."
            )
            
            # Also send as a file
            config_filename = f"config{user_id}.conf"
            with open(config_filename, "w") as f:
                f.write(config_text)
            
            # Создаем inline-клавиатуру с опцией продления
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    "📥 Скачать WireGuard", 
                    url="https://www.wireguard.com/install/"
                ),
                InlineKeyboardButton(
                    "⏰ Продлить сейчас", 
                    callback_data="start_extend"
                )
            )
            
            await bot.send_document(
                chat_id=user_id,
                document=types.InputFile(config_filename),
                caption="📄 Ваша конфигурация WireGuard в виде файла",
                reply_markup=keyboard
            )
            
            # Remove the temporary file
            os.remove(config_filename)
        else:
            await message.reply("❌ Ошибка при сохранении конфигурации. Попробуйте позже.")
    else:
        await message.reply("❌ Ошибка при создании конфигурации. Попробуйте позже.")

@dp.message_handler(commands=['status'])
@dp.message_handler(lambda message: message.text == "📊 Статус")
async def check_status(message: types.Message):
    """Check the status of user's WireGuard configuration."""
    # If message is from callback, extract user_id from the original message
    if hasattr(message, 'reply_to_message') and message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        user_id = message.from_user.id
    
    # Get user configuration from database
    response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}")
    
    if response.status_code == 200:
        config_data = response.json()
        
        if config_data.get("active", False):
            expiry_time = config_data.get("expiry_time")
            current_time = datetime.now().isoformat()
            
            if expiry_time > current_time:
                # Calculate remaining time
                expiry_dt = datetime.fromisoformat(expiry_time)
                current_dt = datetime.now()
                remaining = expiry_dt - current_dt
                
                days = remaining.days
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                status_text = (
                    f"✅ *Статус вашей конфигурации WireGuard*\n\n"
                    f"🟢 *Статус:* Активна\n"
                    f"🕒 *Истекает:* {expiry_formatted}\n"
                    f"⏳ *Осталось времени:* {days} дн. {hours} ч. {minutes} мин.\n\n"
                )
                
                # Добавляем информацию о возможности продления
                if days < 7:  # Если осталось меньше 7 дней
                    status_text += "⚠️ *Скоро истечет срок действия!* Рекомендуем продлить конфигурацию.\n\n"
                
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend"),
                    InlineKeyboardButton("📱 Показать QR-код и файл", callback_data="show_config")
                )
                
                await message.reply(
                    status_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
                
                # Generate and send QR code and config file
                config_text = config_data.get("config")
                
                # Generate QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(config_text)
                qr.make(fit=True)
                
                # Create an image from the QR Code
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Save the image to a bytes buffer
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Send QR code as photo
                await bot.send_photo(
                    chat_id=user_id,
                    photo=buffer,
                    caption="📱 Ваш QR-код с конфигурацией WireGuard"
                )
                
                # Also send as a file
                config_filename = f"config{user_id}.conf"
                with open(config_filename, "w") as f:
                    f.write(config_text)
                
                await bot.send_document(
                    chat_id=user_id,
                    document=types.InputFile(config_filename),
                    caption="📄 Ваша текущая конфигурация WireGuard"
                )
                
                # Remove the temporary file
                os.remove(config_filename)
            else:
                # Конфигурация истекла
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    InlineKeyboardButton("🔄 Создать новую конфигурацию", callback_data="create"),
                    InlineKeyboardButton("⏰ Продлить текущую", callback_data="start_extend")
                )
                
                await message.reply(
                    "🔴 *Ваша конфигурация истекла.*\n\n"
                    "Вы можете создать новую конфигурацию или продлить текущую.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
        else:
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create")
            )
            
            await message.reply(
                "ℹ️ *У вас нет активной конфигурации.*\n\n"
                "Создайте новую конфигурацию, чтобы начать использовать WireGuard.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    else:
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create")
        )
        
        await message.reply(
            "ℹ️ *У вас нет активной конфигурации.*\n\n"
            "Создайте новую конфигурацию, чтобы начать использовать WireGuard.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

@dp.callback_query_handler(lambda c: c.data == 'show_config')
async def show_config(callback_query: types.CallbackQuery):
    """Show configuration QR code and file again."""
    await bot.answer_callback_query(callback_query.id)
    await check_status(callback_query.message)

# Функции для работы с продлением конфигурации

# Функция для получения баланса Telegram Stars
async def get_stars_balance(user_id):
    """Получение баланса Telegram Stars пользователя."""
    # Это должен быть вызов к API Telegram через MTProto или другой способ
    # В документации указано, что нужно использовать payments.getStarsStatus
    # Для примера просто вернем фиктивный баланс
    balance = 10000  # 10000 звезд
    return balance

# Функция для создания invoice для оплаты
def create_stars_invoice(user_id, days, stars):
    """Создание invoice для оплаты звездами."""
    # Уникальный идентификатор формы оплаты
    form_id = int(uuid.uuid4().int & (1<<63)-1)
    
    # Описание покупки
    title = f"Продление WireGuard на {days} дней"
    description = f"Продление доступа к VPN через WireGuard на {days} дней"
    
    # Создаем объект invoice (это JSON, который затем будет обработан на стороне Telegram)
    invoice = {
        "star_amount": stars,
        "telegram_payment_charge_id": f"wireguard_extension_{user_id}_{int(datetime.now().timestamp())}",
        "provider_payment_charge_id": f"extension_{days}d_{int(datetime.now().timestamp())}"
    }
    
    return form_id, title, description, invoice

# Обработчик для команды продления
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
    
    # Проверка баланса пользователя (опционально)
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
    
    # Создаем платежную форму
    form_id, title, description, invoice = create_stars_invoice(
        user_id=user_id,
        days=days,
        stars=stars
    )
    
    # Сохраняем данные платежной формы в состояние
    await state.update_data(
        form_id=form_id,
        title=title,
        description=description,
        invoice=json.dumps(invoice)
    )
    
    # Формируем клавиатуру для подтверждения оплаты
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            f"💳 Оплатить {stars} ⭐",
            # В реальной имплементации здесь может быть специальный флаг для оплаты звездами
            callback_data=f"pay_stars_{form_id}"
        )
    )
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_extend"))
    
    await bot.edit_message_text(
        f"⏰ *Продление конфигурации WireGuard*\n\n"
        f"Вы выбрали продление на *{days} дней* за *{stars} ⭐*\n\n"
        f"Нажмите кнопку оплаты для продолжения:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    
    # Переходим в состояние подтверждения оплаты
    await ExtendConfigStates.confirming_payment.set()

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

# Обработчик для оплаты звездами
@dp.callback_query_handler(lambda c: c.data.startswith('pay_stars_'), state=ExtendConfigStates.confirming_payment)
async def process_stars_payment(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка оплаты звездами."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем form_id из callback_data
    _, _, form_id = callback_query.data.split('_', 2)
    form_id = int(form_id)
    
    # Получаем данные из состояния
    data = await state.get_data()
    days = data.get('days')
    stars = data.get('stars')
    
    # Получаем user_id из callback_query
    user_id = callback_query.from_user.id
    
    # В реальной реализации здесь должен быть вызов к API Telegram
    # для выполнения платежа звездами
    # Например, что-то вроде payments.sendStarsForm
    
    # Для примера считаем, что платеж прошел успешно
    payment_successful = True
    transaction_id = f"stars_payment_{user_id}_{int(datetime.now().timestamp())}"
    
    if payment_successful:
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
                
                await bot.edit_message_text(
                    f"✅ *Конфигурация успешно продлена!*\n\n"
                    f"▫️ Продление: *{days} дней*\n"
                    f"▫️ Оплачено: *{stars} ⭐*\n"
                    f"▫️ Действует до: *{expiry_formatted}*\n\n"
                    f"Спасибо за использование нашего сервиса!",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await bot.edit_message_text(
                    f"✅ *Конфигурация успешно продлена на {days} дней!*\n\n"
                    f"Оплачено: *{stars} ⭐*\n\n"
                    f"Для просмотра обновленной информации используйте команду /status.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            error_message = "Ошибка при продлении конфигурации. Обратитесь в поддержку."
            if "error" in response.json():
                error_message = response.json().get("error")
            
            await bot.edit_message_text(
                f"❌ *Ошибка!*\n\n{error_message}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await bot.edit_message_text(
            "❌ *Ошибка при обработке платежа*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
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