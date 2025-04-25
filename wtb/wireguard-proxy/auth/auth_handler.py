import logging
import time
import json
import os
import base64
import hmac
import hashlib
import requests
from utils.errors import AuthenticationError

logger = logging.getLogger('wireguard-proxy.auth_handler')

# Кэш токенов аутентификации для каждого сервера
_auth_tokens = {}
_token_expiry = {}

def get_auth_headers(server):
    """
    Получение заголовков аутентификации для запроса к удаленному серверу
    
    Args:
        server (dict): Информация о сервере
        
    Returns:
        dict: Заголовки для аутентификации
    """
    server_id = server['id']
    
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

def init_auth_handler():
    """
    Инициализация обработчика аутентификации
    """
    # Здесь можно выполнить дополнительные действия при инициализации
    # Например, загрузить ключи из защищенного хранилища
    logger.info("Auth handler initialized")

def get_auth_status():
    """
    Получение статуса аутентификации для всех серверов
    
    Returns:
        dict: Статус аутентификации для каждого сервера
    """
    current_time = time.time()
    status = {}
    
    for server_id, expiry in _token_expiry.items():
        status[server_id] = {
            "authenticated": expiry > current_time,
            "expires_in": max(0, int(expiry - current_time)),
            "auth_type": "token" if server_id in _auth_tokens else "none"
        }
    
    return status