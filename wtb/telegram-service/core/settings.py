import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Конфигурация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token из переменных окружения
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not API_TOKEN:
    logger.error("TELEGRAM_TOKEN not found in environment variables!")
    exit(1)

# URL-ы сервисов
WIREGUARD_SERVICE_URL = os.getenv('WIREGUARD_SERVICE_URL', 'http://wireguard-service:8080')
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL', 'http://database-service:8081')

# Инициализация бота и диспетчера с хранилищем FSM
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Константы для продления
EXTEND_OPTIONS = [
    {"days": 7, "stars": 50, "label": "7 дней - 50 ⭐"},
    {"days": 30, "stars": 210, "label": "30 дней - 210 ⭐"},
    {"days": 90, "stars": 560, "label": "90 дней - 560 ⭐"},
    {"days": 180, "stars": 950, "label": "180 дней - 950 ⭐"},
    {"days": 365, "stars": 1550, "label": "365 дней - 1550 ⭐"}
]