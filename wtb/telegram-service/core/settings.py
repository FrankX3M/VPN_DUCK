import os
import logging
import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка URL для API Gateway
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'http://kong:8000')

# Важно: пути соответствуют путям в Kong API Gateway
DATABASE_SERVICE_URL = f"{API_GATEWAY_URL}/api"  # В Kong определён маршрут /api
WIREGUARD_SERVICE_URL = f"{API_GATEWAY_URL}/vpn"  # В Kong определён маршрут /vpn

# Добавление заголовков аутентификации для запросов к API через Kong
API_HEADERS = {
    "apikey": os.environ.get('ADMIN_SECRET_KEY', 'fvcfq9d3ycefnvmftiaso'),
    "Content-Type": "application/json"
}

# ADMIN_CHAT_ID для уведомлений администраторам
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '12345678')

# Получаем токен бота из TELEGRAM_TOKEN или BOT_TOKEN (для обратной совместимости)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
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
    
    # Убираем завершающий слеш, если он есть
    url = url.rstrip('/')
    
    # Проверяем, содержит ли URL уже путь /api
    if not url.endswith('/api'):
        # Если URL содержит /api/ в середине, возвращаем URL до /api
        if '/api/' in url:
            url = url.split('/api/')[0] + '/api'
        # Если URL не заканчивается на /api, добавляем /api
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

# Дополнительные настройки
REMOTE_ONLY = os.getenv('REMOTE_ONLY', 'false').lower() == 'true'

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

# Функция для проверки доступности сервисов
def check_services_availability():
    """
    Проверяет доступность API Gateway и других сервисов.
    
    Returns:
        dict: Статус доступности каждого сервиса
    """
    services_status = {
        "api_gateway": False,
        "database": False,
        "wireguard": False
    }
    
    # Проверка API Gateway
    logger.info(f"Проверка доступности API Gateway: {API_GATEWAY_URL}")
    try:
        response = requests.get(API_GATEWAY_URL, timeout=5)
        if response.status_code:  # Любой статус-код означает, что сервис отвечает
            services_status["api_gateway"] = True
            logger.info(f"API Gateway доступен, статус: {response.status_code}")
    except Exception as e:
        logger.warning(f"API Gateway недоступен: {str(e)}")
    
    # Проверка database-service
    db_check_url = f"{DATABASE_SERVICE_URL}/status"
    logger.info(f"Проверка доступности database-service: {db_check_url}")
    try:
        response = requests.get(db_check_url, headers=API_HEADERS, timeout=5)
        if response.status_code == 200:
            services_status["database"] = True
            logger.info("database-service доступен")
        else:
            logger.warning(f"database-service недоступен, код: {response.status_code}")
            logger.warning(f"Тело ответа: {response.text}")
    except Exception as e:
        logger.warning(f"Ошибка при проверке database-service: {str(e)}")
    
    # Проверка wireguard-service
    logger.info(f"Проверка доступности wireguard-service по URL: {WIREGUARD_SERVICE_URL}/status")
    try:
        response = requests.get(f"{WIREGUARD_SERVICE_URL}/status", headers=API_HEADERS, timeout=5)
        if response.status_code == 200:
            services_status["wireguard"] = True
            logger.info("wireguard-service доступен")
        else:
            logger.warning(f"Эндпоинт /status вернул код: {response.status_code}")
            
            # Пробуем запасной URL
            logger.info(f"Пробуем запасной URL для проверки: {WIREGUARD_SERVICE_URL}/health")
            try:
                response = requests.get(f"{WIREGUARD_SERVICE_URL}/health", headers=API_HEADERS, timeout=5)
                if response.status_code == 200:
                    services_status["wireguard"] = True
                    logger.info("wireguard-service доступен через /health")
                else:
                    logger.warning(f"Эндпоинт /health вернул код: {response.status_code}")
                    
                    # Пробуем третий вариант
                    logger.info(f"Пробуем проверку через /servers: {WIREGUARD_SERVICE_URL}/servers")
                    response = requests.get(f"{WIREGUARD_SERVICE_URL}/servers", headers=API_HEADERS, timeout=5)
                    if response.status_code == 200:
                        services_status["wireguard"] = True
                        logger.info("wireguard-service доступен через /servers")
                    else:
                        logger.warning(f"Эндпоинт /servers вернул код: {response.status_code}")
            except Exception as e:
                logger.warning(f"Ошибка при проверке запасного URL: {str(e)}")
    except Exception as e:
        logger.warning(f"Ошибка при проверке wireguard-service: {str(e)}")
    
    logger.info(f"Состояние сервисов: database={services_status['database']}, wireguard={services_status['wireguard']}")
    return services_status

# Пробуем библиотеку requests, если её нет - устанавливаем через переменную, чтобы не импортировать в глобальной области
try:
    import requests
except ImportError:
    logger.warning("Библиотека requests не установлена, используйте pip install requests")
    requests = None

# Вывод информации о настройках при импорте модуля
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