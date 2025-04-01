import os
import logging
import requests
from datetime import datetime, timedelta
import asyncio
import qrcode
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode

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

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Send welcome message when /start command is issued."""
    await message.reply("Привет! Я бот для управления WireGuard конфигурацией.\n"
                        "Используйте /create для создания новой конфигурации (действует 24 часа)\n"
                        "Используйте /status для проверки статуса вашей конфигурации\n"
                        "Используйте /help для получения помощи")

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    """Send help information when /help command is issued."""
    help_text = (
        "Доступные команды:\n"
        "/create - создать новую конфигурацию WireGuard (действует 24 часа)\n"
        "/status - проверить статус вашей конфигурации\n"
        "/help - показать это сообщение"
    )
    await message.reply(help_text)

@dp.message_handler(commands=['create'])
async def create_config(message: types.Message):
    """Create a new WireGuard configuration."""
    user_id = message.from_user.id
    
    # Check if user already has an active configuration
    response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}")
    
    if response.status_code == 200 and response.json().get("active", False):
        # User already has an active configuration
        expiry_time = response.json().get("expiry_time")
        await message.reply(
            f"У вас уже есть активная конфигурация!\n"
            f"Она истекает: {expiry_time}\n"
            f"Используйте /status для получения деталей."
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
        
        # Добавляем имя туннеля в начало конфигурации
        config_text = f"# Name = WireGuard VPN\n{config_text}"
        
        # Calculate expiry time (24 hours from now)
        expiry_time = (datetime.now() + timedelta(hours=24)).isoformat()
        
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
                f"Конфигурация WireGuard создана!\n"
                f"Действует до: {expiry_time}\n\n"
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
                caption="QR-код с конфигурацией WireGuard. Отсканируйте его в приложении."
            )
            
            # Also send as a file
            with open(f"config{user_id}.conf", "w") as f:
                f.write(config_text)
            
            await bot.send_document(
                chat_id=user_id,
                document=types.InputFile(f"config{user_id}.conf"),
                caption="Ваша конфигурация WireGuard в виде файла"
            )
            
            # Remove the temporary file
            os.remove(f"config{user_id}.conf")
        else:
            await message.reply("Ошибка при сохранении конфигурации. Попробуйте позже.")
    else:
        await message.reply("Ошибка при создании конфигурации. Попробуйте позже.")

@dp.message_handler(commands=['status'])
async def check_status(message: types.Message):
    """Check the status of user's WireGuard configuration."""
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
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                await message.reply(
                    f"У вас есть активная конфигурация WireGuard.\n"
                    f"Истекает: {expiry_time}\n"
                    f"Осталось времени: {hours} часов и {minutes} минут\n\n"
                    f"Используйте /create после истечения срока для создания новой конфигурации."
                )
                
                # Generate and send QR code again if requested
                config_text = config_data.get("config")
                
                # Проверяем, есть ли уже имя туннеля в конфигурации
                if not config_text.startswith("# Name ="):
                    config_text = f"# Name = WireGuard VPN\n{config_text}"
                
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
                    caption="Ваш QR-код с конфигурацией WireGuard"
                )
                
                # Also send as a file
                with open(f"config{user_id}.conf", "w") as f:
                    f.write(config_text)
                
                await bot.send_document(
                    chat_id=user_id,
                    document=types.InputFile(f"config{user_id}.conf"),
                    caption="Ваша текущая конфигурация WireGuard"
                )
                
                # Remove the temporary file
                os.remove(f"config{user_id}.conf")
            else:
                await message.reply(
                    "Ваша конфигурация истекла.\n"
                    "Используйте /create для создания новой конфигурации."
                )
        else:
            await message.reply(
                "У вас нет активной конфигурации.\n"
                "Используйте /create для создания новой конфигурации."
            )
    else:
        await message.reply(
            "У вас нет активной конфигурации.\n"
            "Используйте /create для создания новой конфигурации."
        )

async def on_startup(dp):
    """Set up bot on startup."""
    logging.info("Bot started!")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)