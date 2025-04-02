import os
import logging
import requests
from datetime import datetime, timedelta
import asyncio
import qrcode
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Configure logging
logging.basicConfig(level=logging.INFO)

# Bot token from environment variable
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
WIREGUARD_SERVICE_URL = os.getenv('WIREGUARD_SERVICE_URL')
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL')

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Create a permanent keyboard that will be shown all the time
def get_permanent_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton("🔑 Создать конфигурацию"),
        KeyboardButton("📊 Статус")
    )
    keyboard.row(
        KeyboardButton("ℹ️ Помощь"),
        KeyboardButton("📥 Скачать WireGuard")
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
        "🔹 `/status` или кнопка *📊 Статус* - проверить статус вашей конфигурации\n"
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
        
        await message.reply(
            f"⚠️ *У вас уже есть активная конфигурация!*\n\n"
            f"Она истекает: `{expiry_formatted}`\n\n"
            f"Используйте /status для получения деталей.",
            parse_mode=ParseMode.MARKDOWN
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
            with open(f"config_{user_id}.conf", "w") as f:
                f.write(config_text)
            
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    "📥 Скачать WireGuard", 
                    url="https://www.wireguard.com/install/"
                )
            )
            
            await bot.send_document(
                chat_id=user_id,
                document=types.InputFile(f"config{user_id}.conf"),
                caption="📄 Ваша конфигурация WireGuard в виде файла",
                reply_markup=keyboard
            )
            
            # Remove the temporary file
            os.remove(f"config{user_id}.conf")
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
                current_dt = datetime.fromisoformat(current_time)
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
                    f"Используйте *🔑 Создать конфигурацию* после истечения срока для создания новой конфигурации."
                )
                
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(
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
                with open(f"config{user_id}.conf", "w") as f:
                    f.write(config_text)
                
                await bot.send_document(
                    chat_id=user_id,
                    document=types.InputFile(f"config{user_id}.conf"),
                    caption="📄 Ваша текущая конфигурация WireGuard"
                )
                
                # Remove the temporary file
                os.remove(f"config{user_id}.conf")
            else:
                await message.reply(
                    "🔴 *Ваша конфигурация истекла.*\n\n"
                    "Используйте кнопку *🔑 Создать конфигурацию* для создания новой конфигурации.",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await message.reply(
                "ℹ️ *У вас нет активной конфигурации.*\n\n"
                "Используйте кнопку *🔑 Создать конфигурацию* для создания новой конфигурации.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await message.reply(
            "ℹ️ *У вас нет активной конфигурации.*\n\n"
            "Используйте кнопку *🔑 Создать конфигурацию* для создания новой конфигурации.",
            parse_mode=ParseMode.MARKDOWN
        )

@dp.callback_query_handler(lambda c: c.data == 'show_config')
async def show_config(callback_query: types.CallbackQuery):
    """Show configuration QR code and file again."""
    await bot.answer_callback_query(callback_query.id)
    await check_status(callback_query.message)

async def on_startup(dp):
    """Set up bot on startup."""
    logging.info("Bot started!")

    # Set commands for the bot menu
    commands = [
        types.BotCommand("create", "Создать конфигурацию"),
        types.BotCommand("status", "Проверить статус"),
        types.BotCommand("help", "Показать справку")
    ]
    await bot.set_my_commands(commands)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)