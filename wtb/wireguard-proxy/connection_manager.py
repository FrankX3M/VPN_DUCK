import logging
import requests
import time
from utils.errors import RemoteServerError, NoAvailableServerError
from auth.auth_handler import get_auth_headers

logger = logging.getLogger('wireguard-proxy.connection_manager')

class ConnectionManager:
    """
    Менеджер соединений с удаленными серверами WireGuard
    
    Отвечает за:
    - Установление соединений с удаленными серверами
    - Отправку запросов к удаленным серверам
    - Обработку ответов от удаленных серверов
    - Обработку ошибок соединения
    """
    
    def __init__(self, server_manager):
        self.server_manager = server_manager
        self.timeout = 10  # Таймаут для запросов в секундах
    
    def get_suitable_server(self, geolocation_id=None):
        """
        Получение подходящего сервера на основе критериев
        
        Args:
            geolocation_id (str, optional): ID геолокации
            
        Returns:
            dict: Информация о выбранном сервере или None
        """
        if geolocation_id:
            # Если указана геолокация, ищем сервер с этой геолокацией
            server = self.server_manager.get_server_by_geolocation(geolocation_id)
            if server:
                return server
            
            logger.warning(f"No available server for geolocation_id: {geolocation_id}, falling back to best server")
        
        # Если геолокация не указана или подходящий сервер не найден,
        # выбираем сервер с наименьшей нагрузкой
        return self.server_manager.get_best_server()
    
    def get_all_servers(self):
        """
        Получение списка всех доступных серверов
        
        Returns:
            list: Список доступных серверов
        """
        return self.server_manager.get_available_servers()
    
    def send_create_request(self, server_id, data):
    """
    Отправка запроса на создание конфигурации на удаленный сервер
    
    Args:
        server_id (str): ID сервера
        data (dict): Данные для создания конфигурации
        
    Returns:
        dict: Результат выполнения запроса
        
    Raises:
        RemoteServerError: Если произошла ошибка при обращении к удаленному серверу
    """
    server = self.server_manager.get_server_by_id(server_id)
    if not server:
        raise NoAvailableServerError(f"Server with ID {server_id} not found")
    
    # Проверка, является ли сервер тестовым (ID начинается с 'test-')
    if server_id.startswith('test-'):
        logger.info(f"Generating mock response for test server {server_id}")
        import uuid
        import time
        
        # Генерируем тестовые данные для ответа
        test_private_key = "test_" + str(uuid.uuid4()).replace("-", "")
        test_public_key = "test_" + str(uuid.uuid4()).replace("-", "")
        
        # Симуляция задержки для более реалистичного поведения
        time.sleep(0.2)
        
        # Запись метрик
        self.server_manager.record_server_metrics(
            server_id,
            success=True,
            response_time=0.2
        )
        
        # Формирование тестового ответа
        return {
            "public_key": test_public_key,
            "private_key": test_private_key,
            "server_endpoint": f"{server.get('api_url', 'test.example.com').split('//')[1].split('/')[0]}:51820",
            "allowed_ips": "0.0.0.0/0",
            "dns": "1.1.1.1",
            "config": f"# WireGuard configuration\n[Interface]\nPrivateKey = {test_private_key}\nAddress = 10.0.0.2/24\nDNS = 1.1.1.1\n\n[Peer]\nPublicKey = {test_public_key}\nAllowedIPs = 0.0.0.0/0\nEndpoint = test.example.com:51820",
            "server_id": server_id
        }
    
    # Оригинальный код для реальных серверов
    server_url = server.get('api_url')
    if not server_url:
        raise ValueError(f"Invalid server URL for server {server_id}")
    
    try:
        logger.info(f"Sending create request to server {server_id} ({server_url})")
        
        # Измерение времени ответа
        start_time = time.time()
        
        # Получение заголовков аутентификации
        headers = get_auth_headers(server)
        
        # Отправка запроса на удаленный сервер
        response = requests.post(
            f"{server_url}/create",
            json=data,
            headers=headers,
            timeout=self.timeout
        )
        
        # Вычисление времени ответа
        response_time = time.time() - start_time
        
        # Запись метрик
        self.server_manager.record_server_metrics(
            server_id,
            success=(response.status_code == 200),
            response_time=response_time
        )
        
        # Проверка статуса ответа
        if response.status_code != 200:
            error_msg = f"Error from remote server {server_id}: {response.status_code} {response.text}"
            logger.error(error_msg)
            raise RemoteServerError(error_msg)
        
        # Обработка успешного ответа
        result = response.json()
        logger.info(f"Create request to server {server_id} completed successfully")
        
        return result
        
    except requests.RequestException as e:
        error_msg = f"Connection error to server {server_id} ({server_url}): {e}"
        logger.error(error_msg)
        
        # Запись метрик о неудачном запросе
        self.server_manager.record_server_metrics(
            server_id,
            success=False,
            response_time=time.time() - start_time if 'start_time' in locals() else 0
        )
        
        raise RemoteServerError(error_msg)
    
    def send_remove_request(self, server_id, public_key):
    """
    Отправка запроса на удаление пира на удаленный сервер
    
    Args:
        server_id (str): ID сервера
        public_key (str): Публичный ключ пира
        
    Returns:
        dict: Результат выполнения запроса
        
    Raises:
        RemoteServerError: Если произошла ошибка при обращении к удаленному серверу
    """
    server = self.server_manager.get_server_by_id(server_id)
    if not server:
        raise NoAvailableServerError(f"Server with ID {server_id} not found")
    
    # Проверка, является ли сервер тестовым
    if server_id.startswith('test-'):
        logger.info(f"Generating mock response for removing peer from test server {server_id}")
        
        # Симуляция задержки
        time.sleep(0.1)
        
        # Запись метрик
        self.server_manager.record_server_metrics(
            server_id,
            success=True,
            response_time=0.1
        )
        
        # Формирование тестового ответа
        return {
            "success": True,
            "message": f"Peer {public_key} removed successfully from test server"
        }
    
    # Оригинальный код для реальных серверов
    server_url = server.get('api_url')
    if not server_url:
        raise ValueError(f"Invalid server URL for server {server_id}")
    
    try:
        logger.info(f"Sending remove request for peer {public_key} to server {server_id} ({server_url})")
        
        # Измерение времени ответа
        start_time = time.time()
        
        # Получение заголовков аутентификации
        headers = get_auth_headers(server)
        
        # Отправка запроса на удаленный сервер
        response = requests.delete(
            f"{server_url}/remove/{public_key}",
            headers=headers,
            timeout=self.timeout
        )
        
        # Вычисление времени ответа
        response_time = time.time() - start_time
        
        # Запись метрик
        self.server_manager.record_server_metrics(
            server_id,
            success=(response.status_code == 200),
            response_time=response_time
        )
        
        # Проверка статуса ответа
        if response.status_code != 200:
            error_msg = f"Error from remote server {server_id}: {response.status_code} {response.text}"
            logger.error(error_msg)
            raise RemoteServerError(error_msg)
        
        # Обработка успешного ответа
        result = response.json()
        logger.info(f"Remove request for peer {public_key} to server {server_id} completed successfully")
        
        return result
        
    except requests.RequestException as e:
        error_msg = f"Connection error to server {server_id} ({server_url}): {e}"
        logger.error(error_msg)
        
        # Запись метрик о неудачном запросе
        self.server_manager.record_server_metrics(
            server_id,
            success=False,
            response_time=time.time() - start_time if 'start_time' in locals() else 0
        )
        
        raise RemoteServerError(error_msg)
        
    def find_server_for_peer(self, public_key):
        """
        Поиск сервера для пира по публичному ключу в базе данных
        
        Args:
            public_key (str): Публичный ключ пира
            
        Returns:
            str: ID сервера или None, если не найден
        """
        # В реальной системе этот метод должен делать запрос к базе данных
        # для поиска информации о том, на каком сервере размещен пир
        # с указанным публичным ключом
        
        try:
            # Запрос к сервису базы данных
            database_service_url = self.server_manager.database_service_url
            response = requests.get(
                f"{database_service_url}/api/peers/find",
                params={"public_key": public_key},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Database error when finding server for peer: {response.status_code} {response.text}")
                return None
            
            result = response.json()
            server_id = result.get('server_id')
            
            if server_id:
                logger.info(f"Found server {server_id} for peer {public_key}")
                return server_id
            else:
                logger.warning(f"No server found for peer {public_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error when finding server for peer {public_key}: {e}")
            return None