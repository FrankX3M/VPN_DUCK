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


def get_user_config(user_id):
    """
    Получает конфигурацию для пользователя из базы данных.
    
    Args:
        user_id (int): ID пользователя
    
    Returns:
        dict: Конфигурация пользователя или None при ошибке
    """
    try:
        logger.info(f"Получение конфигурации для пользователя {user_id}")
        url = f"{DATABASE_SERVICE_URL}/api/config/{user_id}"
        logger.info(f"Используем URL: {url}")
        
        response = requests.get(url, timeout=5)
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.info(f"Конфигурация для пользователя {user_id} не найдена ({response.status_code})")
            return None
    except Exception as e:
        logger.error(f"Ошибка при получении конфигурации: {e}")
        return None

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