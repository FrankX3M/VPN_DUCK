import os
import sys
import logging
import time
import json
import base64
import hmac
import hashlib
import requests

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.errors import AuthenticationError
from utils.retry import retry_on_connection_error
from config.settings import USE_MOCK_DATA

logger = logging.getLogger('wireguard-proxy.auth_handler')

# Кэш токенов аутентификации для каждого сервера
_auth_tokens = {}
_token_expiry = {}
_auth_initialized = False

def init_auth_handler():
    """
    Инициализация обработчика аутентификации
    """
    global _auth_initialized
    
    if _auth_initialized:
        logger.debug("Auth handler already initialized")
        return
    
    try:
        # Загрузка ключей из защищенного хранилища
        _load_auth_keys_from_secure_storage()
        _auth_initialized = True
        logger.info("Auth handler initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing auth handler: {e}")
        # Продолжаем работу даже при ошибке инициализации
        _auth_initialized = True

def _load_auth_keys_from_secure_storage():
    """
    Загрузка ключей аутентификации из защищенного хранилища
    
    В реальной системе здесь должен быть код для загрузки ключей из
    хранилища секретов (HashiCorp Vault, AWS Secrets Manager и т.д.)
    """
    # В тестовом режиме загружаем предопределенные ключи
    if USE_MOCK_DATA:
        logger.info("Loading test authentication keys")
        
        # Путь к файлу с тестовыми ключами
        keys_file = os.path.join(os.path.dirname(__file__), 'test_keys.json')
        
        # Если файл существует, загружаем из него
        if os.path.exists(keys_file):
            try:
                with open(keys_file, 'r') as f:
                    test_keys = json.load(f)
                
                # Устанавливаем ключи в кэш с длительным сроком действия
                for server_id, key_data in test_keys.items():
                    _auth_tokens[server_id] = key_data.get('token')
                    _token_expiry[server_id] = time.time() + 3600  # 1 час
                
                logger.info(f"Loaded {len(test_keys)} test authentication keys")
            except Exception as e:
                logger.error(f"Error loading test authentication keys: {e}")
        else:
            logger.info("No test keys file found, using default test keys")
            
            # Добавляем тестовые ключи для серверов из конфигурации
            from config.settings import MOCK_SERVERS
            
            for server in MOCK_SERVERS:
                server_id = server.get('id')
                _auth_tokens[server_id] = server.get('api_key', f"test-key-{server_id}")
                _token_expiry[server_id] = time.time() + 3600  # 1 час
            
            logger.info(f"Created default test keys for {len(MOCK_SERVERS)} servers")

def get_auth_headers(server):
    """
    Получение заголовков аутентификации для запроса к удаленному серверу
    
    Args:
        server (dict): Информация о сервере
        
    Returns:
        dict: Заголовки для аутентификации
    """
    server_id = server['id']
    
    # Для тестовых серверов возвращаем предопределенные заголовки
    if str(server_id).startswith(('test-', 'mock-')):
        test_key = server.get('api_key', f'test-key-{server_id}')
        logger.debug(f"Using test auth token for server {server_id}")
        return {
            "Authorization": f"Bearer {test_key}",
            "Content-Type": "application/json"
        }
    
    # Проверка наличия действительного токена в кэше
    if server_id in _auth_tokens and _token_expiry.get(server_id, 0) > time.time():
        logger.debug(f"Using cached auth token for server {server_id}")
        return {
            "Authorization": f"Bearer {_auth_tokens[server_id]}",
            "Content-Type": "application/json"
        }
    
    # Получение нового токена
    try:
        token = _get_auth_token(server)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        logger.error(f"Error getting auth token for server {server_id}: {e}")
        # Возвращаем базовые заголовки без токена
        return {"Content-Type": "application/json"}

@retry_on_connection_error(max_attempts=3, min_wait=1, max_wait=10)
def _get_auth_token(server):
    """
    Получение токена аутентификации для сервера
    
    Args:
        server (dict): Информация о сервере
        
    Returns:
        str: Токен аутентификации
        
    Raises:
        AuthenticationError: Если не удалось получить токен
    """
    server_id = server['id']
    auth_type = server.get('auth_type', 'api_key')
    
    if auth_type == 'api_key':
        # Простая аутентификация по API-ключу
        api_key = server.get('api_key')
        if not api_key:
            # Проверка наличия ключа в безопасном хранилище
            from utils.secure_storage import get_api_key_from_storage
            try:
                api_key = get_api_key_from_storage(server_id)
            except:
                # Если функция не определена или произошла ошибка
                pass
            
            if not api_key:
                raise AuthenticationError(f"Missing API key for server {server_id}")
        
        # Сохраняем API-ключ как токен с длительным временем жизни
        _auth_tokens[server_id] = api_key
        _token_expiry[server_id] = time.time() + 3600  # 1 час
        
        return api_key
        
    elif auth_type == 'oauth':
        # OAuth аутентификация
        client_id = server.get('oauth_client_id')
        client_secret = server.get('oauth_client_secret')
        token_url = server.get('oauth_token_url')
        
        if not all([client_id, client_secret, token_url]):
            raise AuthenticationError(f"Missing OAuth credentials for server {server_id}")
        
        try:
            response = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                },
                timeout=10
            )
            
            if response.status_code != 200:
                raise AuthenticationError(f"OAuth error: {response.status_code} {response.text}")
            
            token_data = response.json()
            token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            
            if not token:
                raise AuthenticationError("No access token in OAuth response")
            
            # Сохраняем токен в кэш
            _auth_tokens[server_id] = token
            _token_expiry[server_id] = time.time() + expires_in - 60  # -60 для гарантии
            
            return token
            
        except requests.RequestException as e:
            raise AuthenticationError(f"OAuth request error: {e}")
            
    elif auth_type == 'hmac':
        # HMAC аутентификация
        secret_key = server.get('hmac_secret')
        if not secret_key:
            raise AuthenticationError(f"Missing HMAC secret for server {server_id}")
        
        # Создаем подписанный токен
        timestamp = str(int(time.time()))
        message = f"{server_id}:{timestamp}"
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = base64.b64encode(f"{message}:{signature}".encode()).decode()
        
        # Сохраняем токен в кэш
        _auth_tokens[server_id] = token
        _token_expiry[server_id] = time.time() + 300  # 5 минут
        
        return token
        
    else:
        raise AuthenticationError(f"Unsupported authentication type: {auth_type}")

def revoke_auth_token(server_id):
    """
    Отзыв токена аутентификации для сервера
    
    Args:
        server_id (str): ID сервера
    """
    _auth_tokens.pop(server_id, None)
    _token_expiry.pop(server_id, None)
    logger.info(f"Auth token for server {server_id} has been revoked")

def get_auth_status():
    """
    Получение статуса аутентификации для всех серверов
    
    Returns:
        dict: Статус аутентификации для каждого сервера
    """
    current_time = time.time()
    status = {}
    
    for server_id, expiry in _token_expiry.items():
        # Скрываем полные токены в ответе
        token = _auth_tokens.get(server_id, '')
        token_preview = '•' * 8
        if token and len(token) > 4:
            token_preview = token[:2] + '•' * (len(token) - 4) + token[-2:]
        
        status[server_id] = {
            "authenticated": expiry > current_time,
            "expires_in": max(0, int(expiry - current_time)),
            "auth_type": "token" if server_id in _auth_tokens else "none",
            "token_preview": token_preview
        }
    
    return status

def rotate_auth_tokens():
    """
    Ротация токенов аутентификации для повышения безопасности
    """
    current_time = time.time()
    rotated = 0
    
    # Получаем список серверов
    from server_manager import ServerManager
    server_manager = None
    
    try:
        # Получение всех доступных серверов
        if not server_manager:
            from utils.service_locator import get_service
            server_manager = get_service('server_manager')
            
        if server_manager:
            servers = server_manager.servers
            
            # Обходим все серверы
            for server in servers:
                server_id = server['id']
                
                # Пропускаем тестовые серверы
                if str(server_id).startswith(('test-', 'mock-')):
                    continue
                
                # Проверяем необходимость ротации токена
                # (токен отсутствует, истек или скоро истечет)
                if server_id not in _auth_tokens or \
                   server_id not in _token_expiry or \
                   _token_expiry.get(server_id, 0) < current_time + 600:  # меньше 10 минут
                    try:
                        # Получаем новый токен
                        _get_auth_token(server)
                        rotated += 1
                        logger.info(f"Rotated authentication token for server {server_id}")
                    except Exception as e:
                        logger.error(f"Failed to rotate authentication token for server {server_id}: {e}")
        else:
            logger.warning("Server manager not available, skipping token rotation")
            
    except Exception as e:
        logger.error(f"Error rotating authentication tokens: {e}")
    
    return rotated

# Динамический импорт на случай отсутствия безопасного хранилища
try:
    from utils.secure_storage import get_api_key_from_storage
except ImportError:
    def get_api_key_from_storage(server_id):
        """
        Заглушка для функции получения API-ключа из хранилища
        
        Args:
            server_id (str): ID сервера
            
        Returns:
            str: API-ключ или None
        """
        return None