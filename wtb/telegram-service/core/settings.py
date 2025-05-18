import os
import logging
import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
# # Настройка логирования (может быть перемещена в отдельный модуль)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# # Функция для нормализации URL API
# def normalize_api_url(url: str) -> str:
#     """
#     Нормализует URL API для взаимодействия с микросервисами.
    
#     Args:
#         url (str): Исходный URL микросервиса
        
#     Returns:
#         str: Нормализованный URL с правильным путем /api
#     """
#     if not url:
#         return ""
    
#     # Убираем завершающий слеш, если он есть
#     url = url.rstrip('/')
    
#     # Проверяем, содержит ли URL уже путь /api
#     if 'wireguard-proxy' in url or 'wireguard-service' in url:
#         # Для wireguard-proxy, который имеет эндпоинты в корне, не добавляем /api
#         # Исправляем, если /api уже добавлен
#         if url.endswith('/api'):
#             logger.debug(f"Удаляем /api для wireguard-proxy: {url}")
#             url = url[:-4]  # Удаляем '/api'
#     else:
#         # Для других сервисов добавляем /api, если его нет
#         if not url.endswith('/api') and '/api/' not in url:
#             url += '/api'
    
#     # Исправляем случаи двойного /api/api
#     url = url.replace('/api/api', '/api')
    
#     logger.debug(f"Нормализованный URL: {url}")
#     return url
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка URL для API Gateway
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'http://kong:8000')  # URL API Gateway
DATABASE_SERVICE_URL = f"{API_GATEWAY_URL}/api"
WIREGUARD_SERVICE_URL = f"{API_GATEWAY_URL}/vpn"

# Добавление заголовков аутентификации для запросов к API через Kong
API_HEADERS = {
    "apikey": os.environ.get('ADMIN_SECRET_KEY', 'fvcfq9d3ycefnvmftiaso'),
    "Content-Type": "application/json"
}

# ADMIN_CHAT_ID для уведомлений администраторам
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '12345678')

# Получаем токен бота
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан! Проверьте переменные окружения.")
    raise ValueError("Не задан токен бота в переменных окружения.")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

def normalize_api_url(url):
    """
    Нормализует URL API, убирая лишние слеши.
    
    Args:
        url: URL для нормализации
        
    Returns:
        str: Нормализованный URL
    """
    if not url:
        return ""
    
    url = url.rstrip('/')
    if not url.endswith('/api'):
        if '/api/' in url:
            url = url.split('/api/')[0] + '/api'
        elif not url.endswith('/api'):
            url = url + '/api'
    
    return url

# Получение токена и базовой конфигурации
def get_telegram_token() -> str:
    """
    Получает Telegram токен из различных источников.
    
    Returns:
        str: Токен Telegram бота
    
    Raises:
        ValueError: Если токен не найден
    """
    # Приоритет источников:
    # 1. Переменная окружения TELEGRAM_TOKEN
    # 2. Переменная окружения TELEGRAM_API_TOKEN
    token = os.environ.get('TELEGRAM_TOKEN') or os.environ.get('TELEGRAM_API_TOKEN')
    
    if not token:
        # Попытка прочитать из .env файлов
        env_files = ['.env', '/app/.env', '/opt/.env', '/.env']
        for env_file in env_files:
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('TELEGRAM_TOKEN='):
                            token = line.split('=', 1)[1].strip().strip("'\"")
                            break
                    if token:
                        break
            except FileNotFoundError:
                continue
    
    if not token:
        logger.critical("Telegram Token не найден!")
        raise ValueError("Telegram Token не может быть пустым")
    
    return token

# Инициализация бота и диспетчера
def initialize_bot():
    """
    Инициализирует Telegram бота и диспетчера.
    
    Returns:
        tuple: Экземпляры бота и диспетчера
    """
    try:
        # Получение токена
        API_TOKEN = get_telegram_token()
        
        # Логирование базовой информации
        logger.info("Инициализация Telegram бота...")
        
        # Создание хранилища состояний
        storage = MemoryStorage()
        
        # Создание бота
        bot = Bot(token=API_TOKEN)
        
        # Создание диспетчера
        dp = Dispatcher(bot, storage=storage)
        
        # Добавление middleware для логирования
        dp.middleware.setup(LoggingMiddleware())
        
        logger.info("Инициализация бота завершена.")
        
        return bot, dp
    
    except Exception as e:
        logger.critical(f"Ошибка инициализации бота: {e}", exc_info=True)
        raise

# Глобальные переменные для использования в других модулях
bot = None
dp = None

def setup_bot():
    """
    Настраивает глобальные переменные бота.
    Вызывается при импорте модуля или в начале приложения.
    """
    global bot, dp
    bot, dp = initialize_bot()
    return bot, dp

# Получение дополнительных конфигураций
WIREGUARD_SERVICE_URL = normalize_api_url(os.getenv('WIREGUARD_SERVICE_URL', ''))
DATABASE_SERVICE_URL = normalize_api_url(os.getenv('DATABASE_SERVICE_URL', 'http://database-service:5002'))
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', 'ваш_id_чата')
REMOTE_ONLY = os.getenv('REMOTE_ONLY', 'false').lower() == 'true'

# Логируем информацию о сервисах при запуске
logger.info(f"WIREGUARD_SERVICE_URL: {WIREGUARD_SERVICE_URL}")
logger.info(f"DATABASE_SERVICE_URL: {DATABASE_SERVICE_URL}")

# Проверка работы функции нормализации URL
test_urls = [
    "http://example.com",
    "http://example.com/",
    "http://example.com/api",
    "http://example.com/api/",
    "http://example.com/api/endpoint",
    "http://example.com/api/api/endpoint"
]
logger.info("Тестирование функции normalize_api_url:")
for url in test_urls:
    normalized = normalize_api_url(url)
    logger.info(f"  Исходный: {url} -> Нормализованный: {normalized}")

# Константы для продления
EXTEND_OPTIONS = [
    {"days": 7, "stars": 50, "label": "7 дней - 50 ⭐"},
    {"days": 30, "stars": 210, "label": "30 дней - 210 ⭐"},
    {"days": 90, "stars": 560, "label": "90 дней - 560 ⭐"},
    {"days": 180, "stars": 950, "label": "180 дней - 950 ⭐"},
    {"days": 365, "stars": 1550, "label": "365 дней - 1550 ⭐"}
]

# Функция для установки состояния FSM
def set_state(user_id, state_name):
    """
    Устанавливает состояние для пользователя и логирует.
    
    Args:
        user_id (int): ID пользователя
        state_name (str): Название состояния
    """
    logger.info(f"Устанавливаем состояние {state_name} для пользователя {user_id}")
    # Реальная установка состояния происходит в обработчиках

# Автоматическая настройка при импорте
if bot is None or dp is None:
    setup_bot()