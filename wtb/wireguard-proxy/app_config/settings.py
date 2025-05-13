import os
import sys
import yaml
import json
import logging
import requests  # Добавлен импорт
import logging.config
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Настройки сервера
SERVER_HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.environ.get('PORT', 5001))
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Режим работы - использовать ли тестовые данные вместо реального API
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'

# Настройки подключения к database-service
DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:5002')

# Настройки для серверов
SERVER_CACHE_TTL = 300  # TTL кэша серверов в секундах
SERVER_TIMEOUT = 5  # Timeout для запросов к серверам

# Настройки кэширования
CACHE_MAX_SIZE = int(os.environ.get('CACHE_MAX_SIZE', 1000))
CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))  # 5 минут

# Настройки HTTP-клиента для запросов к удаленным серверам
HTTP_TIMEOUT = int(os.environ.get('HTTP_TIMEOUT', 10))
HTTP_MAX_RETRIES = int(os.environ.get('HTTP_MAX_RETRIES', 3))
HTTP_RETRY_BACKOFF = float(os.environ.get('HTTP_RETRY_BACKOFF', 1.5))
SERVER_STATUS_CHECK_TIMEOUT = int(os.environ.get('SERVER_STATUS_CHECK_TIMEOUT', 3))

# Настройки маршрутизации
ROUTING_STRATEGY = os.environ.get('ROUTING_STRATEGY', 'load_balanced')  # load_balanced, round_robin, random
ROUTING_GEOLOCATION_PRIORITY = os.environ.get('ROUTING_GEOLOCATION_PRIORITY', 'True').lower() == 'true'

# Настройки отказоустойчивости
FALLBACK_MODE_ENABLED = os.environ.get('FALLBACK_MODE_ENABLED', 'true').lower() == 'true'
MAX_RETRY_ATTEMPTS = int(os.environ.get('MAX_RETRY_ATTEMPTS', 10))
RETRY_BACKOFF_FACTOR = float(os.environ.get('RETRY_BACKOFF_FACTOR', 1.5))
HEALTH_CHECK_TIMEOUT = int(os.environ.get('HEALTH_CHECK_TIMEOUT', 5))
STARTUP_WAIT_TIMEOUT = int(os.environ.get('STARTUP_WAIT_TIMEOUT', 60))

# Настройки логирования
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_FILE = os.environ.get('LOG_FILE', None)

# Пути к файлам конфигурации
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config')
MAIN_CONFIG_FILE = os.path.join(CONFIG_PATH, 'config.yml')

# Настройка тестовых серверов
MOCK_SERVERS = [
    {
        'id': 'test-server-1',
        'name': 'Test Server US',
        'endpoint': 'test-us.example.com',
        'port': 51820,
        'api_url': 'http://localhost:5002',
        'location': 'US/New York',
        'geolocation_id': 1,
        'auth_type': 'api_key',
        'api_key': 'test-server-key-1',
        'status': 'active'
    },
    {
        'id': 'test-server-2',
        'name': 'Test Server EU',
        'endpoint': 'test-eu.example.com',
        'port': 51820,
        'api_url': 'http://localhost:5002',
        'location': 'EU/Amsterdam',
        'geolocation_id': 2,
        'auth_type': 'api_key',
        'api_key': 'test-server-key-2',
        'status': 'active'
    },
    {
        'id': 'test-server-3',
        'name': 'Test Server Asia',
        'endpoint': 'test-asia.example.com',
        'port': 51820,
        'api_url': 'http://localhost:5002',
        'location': 'Asia/Tokyo',
        'geolocation_id': 3,
        'auth_type': 'api_key',
        'api_key': 'test-server-key-3',
        'status': 'degraded'
    }
]

def load_config_from_file():
    """
    Загрузка конфигурации из YAML-файла
    
    Returns:
        dict: Настройки из файла конфигурации
    """
    if os.path.exists(MAIN_CONFIG_FILE):
        try:
            with open(MAIN_CONFIG_FILE, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
    return {}

# Загрузка конфигурации из файла и объединение с настройками из переменных окружения
file_config = load_config_from_file()

# Если в файле конфигурации есть секция mock_servers, заменяем тестовые серверы
if 'mock_servers' in file_config and isinstance(file_config['mock_servers'], list):
    MOCK_SERVERS = file_config['mock_servers']

# Настройка логирования
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': LOG_FORMAT
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOG_LEVEL,
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': True
        },
        'wireguard-proxy': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False
        }
    }
}

# Добавление файлового обработчика, если указан файл логов
if LOG_FILE:
    logging_config['handlers']['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': LOG_LEVEL,
        'formatter': 'standard',
        'filename': LOG_FILE,
        'maxBytes': 10485760,  # 10 МБ
        'backupCount': 5
    }
    logging_config['loggers']['']['handlers'].append('file')
    logging_config['loggers']['wireguard-proxy']['handlers'].append('file')

# Применение конфигурации логирования
logging.config.dictConfig(logging_config)

# Логирование конфигурации при старте
logger = logging.getLogger('wireguard-proxy.settings')
logger.info(f"Server configuration: HOST={SERVER_HOST}, PORT={SERVER_PORT}")
logger.info(f"Mock data mode: {USE_MOCK_DATA}")
logger.info(f"Database service URL: {DATABASE_SERVICE_URL}")
logger.info(f"Cache settings: MAX_SIZE={CACHE_MAX_SIZE}, TTL={CACHE_TTL}")
logger.info(f"Routing strategy: {ROUTING_STRATEGY}, Geolocation priority: {ROUTING_GEOLOCATION_PRIORITY}")

def get_servers_from_database():
    """Загрузка информации о серверах из базы данных"""
    if USE_MOCK_DATA:
        logger.info("Using mock servers in test mode")
        return MOCK_SERVERS
        
    try:
        import requests
        # Необходимо убедиться, что переменная DATABASE_SERVICE_URL определена
        database_url = os.environ.get('DATABASE_SERVICE_URL')
        if not database_url:
            logger.error("DATABASE_SERVICE_URL is not defined in environment variables")
            return MOCK_SERVERS
            
        response = requests.get(
            f"{database_url}/api/servers",
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get servers from database: {response.status_code}")
            return MOCK_SERVERS
            
        data = response.json()
        if "servers" in data and isinstance(data["servers"], list):
            logger.info(f"Loaded {len(data['servers'])} servers from database")
            return data["servers"]
        else:
            logger.warning(f"Unexpected data format from database API: {data}")
            return MOCK_SERVERS
    except Exception as e:
        logger.error(f"Error loading servers from database: {str(e)}")
        return MOCK_SERVERS

def wait_for_services():
    """
    Ожидание запуска зависимых сервисов
    
    Returns:
        bool: True если все сервисы успешно запустились, иначе False
    """
    if USE_MOCK_DATA:
        logger.info("Mock data mode enabled, skipping service availability check")
        return True
        
    logger.info("Checking service availability...")
    
    # Проверка доступности database-service
    import requests
    from requests.exceptions import RequestException
    import time
    
    max_attempts = 12  # 1 минута при интервале в 5 секунд
    attempt = 0
    
    while attempt < max_attempts:
        try:
            logger.info(f"Checking database service at {DATABASE_SERVICE_URL}...")
            response = requests.get(f"{DATABASE_SERVICE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
            
            if response.status_code == 200:
                logger.info("Database service is available!")
                return True
                
            logger.warning(f"Database service returned status code {response.status_code}, waiting...")
        except RequestException as e:
            logger.warning(f"Database service not available yet: {e}")
        
        attempt += 1
        if attempt < max_attempts:
            logger.info(f"Retrying in 5 seconds... ({attempt}/{max_attempts})")
            time.sleep(5)
    
    logger.warning("Could not connect to database service, continuing in fallback mode")
    return False