import os
import yaml
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

# Настройки подключения к database-service
DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:5002')

# Настройки кэширования
CACHE_MAX_SIZE = int(os.environ.get('CACHE_MAX_SIZE', 1000))
CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))  # 5 минут

# Настройки HTTP-клиента для запросов к удаленным серверам
HTTP_TIMEOUT = int(os.environ.get('HTTP_TIMEOUT', 10))
HTTP_MAX_RETRIES = int(os.environ.get('HTTP_MAX_RETRIES', 3))
HTTP_RETRY_BACKOFF = float(os.environ.get('HTTP_RETRY_BACKOFF', 1.5))

# Настройки маршрутизации
ROUTING_STRATEGY = os.environ.get('ROUTING_STRATEGY', 'load_balanced')  # load_balanced, round_robin, random
ROUTING_GEOLOCATION_PRIORITY = os.environ.get('ROUTING_GEOLOCATION_PRIORITY', 'True').lower() == 'true'

# Настройки логирования
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_FILE = os.environ.get('LOG_FILE', None)

# Пути к файлам конфигурации
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config')
MAIN_CONFIG_FILE = os.path.join(CONFIG_PATH, 'config.yml')

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

# Загрузка конфигурации из файла
file_config = load_config_from_file()

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