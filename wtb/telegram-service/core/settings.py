import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Конфигурация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Отладочная информация о переменных окружения
logger.info("===== DEBUG INFO =====")
logger.info(f"All environment variables: {dict(os.environ)}")
logger.info(f"Current directory: {os.getcwd()}")

# Bot token из переменных окружения
telegram_token_raw = os.environ.get('TELEGRAM_TOKEN')
logger.info(f"Raw TELEGRAM_TOKEN from os.environ.get: {telegram_token_raw!r}")

API_TOKEN = os.getenv('TELEGRAM_TOKEN')
logger.info(f"API_TOKEN from os.getenv: {API_TOKEN!r}")

# Проверяем наличие токена различными способами
try:
    with open('/proc/self/environ', 'rb') as f:
        environ_content = f.read()
    logger.info(f"Found TELEGRAM_TOKEN in /proc/self/environ: {'TELEGRAM_TOKEN' in environ_content}")
except Exception as e:
    logger.error(f"Error reading /proc/self/environ: {e}")

if not API_TOKEN:
    logger.error("TELEGRAM_TOKEN not found in environment variables!")
    # Попробуем альтернативные источники
    try:
        with open('/.env', 'r') as f:
            env_content = f.read()
            for line in env_content.split('\n'):
                if line.startswith('TELEGRAM_TOKEN='):
                    API_TOKEN = line.split('=', 1)[1].strip()
                    logger.info(f"Loaded TELEGRAM_TOKEN from .env file: {API_TOKEN!r}")
                    break
    except Exception as e:
        logger.error(f"Failed to load from .env file: {e}")
        
    if not API_TOKEN:
        exit(1)

ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', 'ваш_id_чата')
# URL-ы сервисов - правильные URL-адреса с портами
WIREGUARD_SERVICE_URL = os.getenv('WIREGUARD_SERVICE_URL', 'http://wireguard-service:5001')
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL', 'http://database-service:5002')

logger.info(f"WIREGUARD_SERVICE_URL: {WIREGUARD_SERVICE_URL}")
logger.info(f"DATABASE_SERVICE_URL: {DATABASE_SERVICE_URL}")

# Инициализация бота и диспетчера с хранилищем FSM
logger.info("Initializing Bot with token...")
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
logger.info("Bot initialization complete.")

# Функция для установки состояния FSM
def set_state(user_id, state_name):
    """Устанавливает состояние для пользователя и логирует."""
    logger.info(f"Устанавливаем состояние {state_name} для пользователя {user_id}")
    # Реальная установка состояния происходит в обработчиках

# Константы для продления
EXTEND_OPTIONS = [
    {"days": 7, "stars": 50, "label": "7 дней - 50 ⭐"},
    {"days": 30, "stars": 210, "label": "30 дней - 210 ⭐"},
    {"days": 90, "stars": 560, "label": "90 дней - 560 ⭐"},
    {"days": 180, "stars": 950, "label": "180 дней - 950 ⭐"},
    {"days": 365, "stars": 1550, "label": "365 дней - 1550 ⭐"}
]