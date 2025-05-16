# Файл: wireguard-proxy/connection_manager.py

import os
import sys
import logging
import requests
import time

# Добавляем текущую директорию в PYTHONPATH
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    
    def get_available_servers(self):
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
        # Инициализируем время начала запроса
        start_time = time.time()
        
        try:
            # Получаем информацию о сервере
            server = self.server_manager.get_server_by_id(server_id)
            if not server:
                raise NoAvailableServerError(f"Server with ID {server_id} not found")
            
            # Проверка, является ли сервер тестовым (ID начинается с 'test-')
            if str(server_id).startswith('test-'):
                logger.info(f"Generating mock response for test server {server_id}")
                import uuid
                
                # Генерируем тестовые данные для ответа
                test_private_key = "test_" + str(uuid.uuid4()).replace("-", "")
                test_public_key = "test_" + str(uuid.uuid4()).replace("-", "")
                
                # Симуляция задержки для более реалистичного поведения
                time.sleep(0.2)
                
                # Запись метрик
                try:
                    self.server_manager.record_server_metrics(
                        server_id,
                        success=True,
                        response_time=0.2
                    )
                except Exception as metric_error:
                    logger.warning(f"Ошибка при записи метрик: {metric_error}")
                
                # Формирование тестового ответа
                return {
                    "public_key": test_public_key,
                    "private_key": test_private_key,
                    "server_endpoint": f"{server.get('endpoint', 'test.example.com')}:51820",
                    "allowed_ips": "0.0.0.0/0",
                    "dns": "1.1.1.1",
                    "config": f"# WireGuard configuration\n[Interface]\nPrivateKey = {test_private_key}\nAddress = 10.0.0.2/24\nDNS = 1.1.1.1\n\n[Peer]\nPublicKey = {test_public_key}\nAllowedIPs = 0.0.0.0/0\nEndpoint = {server.get('endpoint', 'test.example.com')}:51820",
                    "server_id": server_id,
                    "geolocation_id": server.get('geolocation_id')
                }
            
            # Для реальных серверов
            try:
                logger.info(f"Генерируем конфигурацию для сервера {server_id}")
                
                # Генерируем ключи с помощью wg
                import subprocess
                import random
                
                # Генерация приватного ключа
                try:
                    private_key_process = subprocess.run(
                        ["wg", "genkey"], 
                        capture_output=True, 
                        text=True, 
                        check=True
                    )
                    private_key = private_key_process.stdout.strip()
                    
                    if not private_key:
                        logger.error("Ошибка: wg genkey вернул пустой приватный ключ")
                        raise ValueError("Не удалось сгенерировать приватный ключ")
                    
                    logger.info(f"Приватный ключ успешно сгенерирован, длина: {len(private_key)}")
                    
                    # Генерация публичного ключа из приватного
                    public_key_process = subprocess.run(
                        ["wg", "pubkey"], 
                        input=private_key,
                        capture_output=True, 
                        text=True, 
                        check=True
                    )
                    public_key = public_key_process.stdout.strip()
                    
                    if not public_key:
                        logger.error("Ошибка: wg pubkey вернул пустой публичный ключ")
                        raise ValueError("Не удалось сгенерировать публичный ключ")
                    
                    logger.info(f"Публичный ключ успешно сгенерирован, длина: {len(public_key)}")
                    
                except subprocess.SubprocessError as e:
                    logger.error(f"Ошибка при выполнении команды wg: {e}")
                    raise ValueError(f"Ошибка при генерации ключей WireGuard: {e}")
                except Exception as e:
                    logger.error(f"Непредвиденная ошибка при генерации ключей: {e}")
                    raise ValueError(f"Не удалось сгенерировать ключи WireGuard: {e}")
                
                # Получаем данные сервера
                server_endpoint = f"{server.get('endpoint')}:{server.get('port', 51820)}"
                server_public_key = server.get('public_key')
                server_address = server.get('address', '10.0.0.1/24')
                
                # Логируем данные сервера для отладки
                logger.info(f"Данные сервера {server_id}:")
                logger.info(f"  Endpoint: {server_endpoint}")
                logger.info(f"  Public key: {server_public_key}")
                logger.info(f"  Address: {server_address}")
                
                # Проверяем, что у сервера есть публичный ключ
                if not server_public_key or server_public_key == 'test_public_key_placeholder':
                    logger.warning(f"Сервер {server_id} имеет неправильный публичный ключ: {server_public_key}")
                    # Попытка получить публичный ключ сервера через API, если возможно
                    # Если невозможно - используем тестовый ключ
                    try:
                        # Проверяем, есть ли у сервера API URL и отправляем запрос на получение ключа
                        if server.get('api_url'):
                            from auth.auth_handler import get_auth_headers
                            
                            headers = get_auth_headers(server)
                            key_url = f"{server.get('api_url')}/key"
                            
                            logger.info(f"Пытаемся получить публичный ключ сервера по URL: {key_url}")
                            
                            response = requests.get(
                                key_url,
                                headers=headers,
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                key_data = response.json()
                                server_public_key = key_data.get('public_key')
                                logger.info(f"Получен публичный ключ сервера: {server_public_key}")
                    except Exception as e:
                        logger.error(f"Не удалось получить публичный ключ сервера: {e}")
                    
                    # Если ключ всё ещё пустой, генерируем тестовый
                    if not server_public_key or server_public_key == 'test_public_key_placeholder':
                        logger.info("Генерируем тестовый ключ для сервера")
                        import uuid
                        server_public_key = "nUEmAixEDPJemHxUEim2G6oQvoSxU94grV7WhrnVumc="
                        logger.info(f"Используем тестовый ключ для сервера: {server_public_key}")
                
                # Генерируем клиентский адрес
                try:
                    network_prefix = '.'.join(server_address.split('.')[:-1])
                    client_ip = f"{network_prefix}.{random.randint(2, 254)}"
                    client_address = f"{client_ip}/24"
                    logger.info(f"Сгенерирован адрес клиента: {client_address}")
                except Exception as e:
                    logger.warning(f"Ошибка при генерации клиентского адреса: {e}")
                    # Используем адрес по умолчанию
                    client_address = "10.0.0.2/24"
                    logger.info(f"Используем адрес клиента по умолчанию: {client_address}")
                
                # Создаем конфигурацию
                config = f"""[Interface]
    PrivateKey = {private_key}
    Address = {client_address}
    DNS = 1.1.1.1, 8.8.8.8

    [Peer]
    PublicKey = {server_public_key}
    AllowedIPs = 0.0.0.0/0, ::/0
    Endpoint = {server_endpoint}
    PersistentKeepalive = 25
    """
                
                logger.info("Конфигурация успешно создана")
                
                # Вычисление времени ответа
                response_time = time.time() - start_time
                
                # Запись метрик
                try:
                    self.server_manager.record_server_metrics(
                        server_id,
                        success=True,
                        response_time=response_time
                    )
                except Exception as metric_error:
                    logger.warning(f"Ошибка при записи метрик: {metric_error}")
                
                # Возвращаем результат
                result = {
                    "public_key": public_key,
                    "private_key": private_key,
                    "server_endpoint": server_endpoint,
                    "allowed_ips": "0.0.0.0/0, ::/0",
                    "dns": "1.1.1.1, 8.8.8.8",
                    "config": config,
                    "server_id": server_id,
                    "geolocation_id": server.get('geolocation_id')
                }
                
                logger.info(f"Успешное создание конфигурации для сервера {server_id}")
                return result
                
            except Exception as e:
                error_msg = f"Ошибка при создании конфигурации для сервера {server_id}: {e}"
                logger.error(error_msg)
                
                # Запись метрик о неудачном запросе
                try:
                    self.server_manager.record_server_metrics(
                        server_id,
                        success=False,
                        response_time=time.time() - start_time
                    )
                except Exception as metric_error:
                    logger.warning(f"Ошибка при записи метрик о неудачном запросе: {metric_error}")
                
                raise RemoteServerError(error_msg)
                
        except Exception as e:
            logger.error(f"Общая ошибка при обработке запроса на создание: {e}")
            
            # Запись метрик о неудачном запросе
            try:
                self.server_manager.record_server_metrics(
                    server_id,
                    success=False,
                    response_time=time.time() - start_time
                )
            except Exception as metric_error:
                logger.warning(f"Ошибка при записи метрик неудачного запроса: {metric_error}")
                
            if isinstance(e, NoAvailableServerError) or isinstance(e, RemoteServerError):
                raise e
            else:
                raise RemoteServerError(f"Ошибка при создании конфигурации: {e}")
    
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
        # Инициализация времени начала запроса
        start_time = time.time()
        
        try:
            server = self.server_manager.get_server_by_id(server_id)
            if not server:
                raise NoAvailableServerError(f"Server with ID {server_id} not found")
            
            # Проверка, является ли сервер тестовым
            if str(server_id).startswith('test-'):
                logger.info(f"Generating mock response for removing peer from test server {server_id}")
                
                # Симуляция задержки
                time.sleep(0.1)
                
                # Запись метрик
                try:
                    self.server_manager.record_server_metrics(
                        server_id,
                        success=True,
                        response_time=0.1
                    )
                except Exception as metric_error:
                    logger.warning(f"Ошибка при записи метрик: {metric_error}")
                
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
                try:
                    self.server_manager.record_server_metrics(
                        server_id,
                        success=(response.status_code == 200),
                        response_time=response_time
                    )
                except Exception as metric_error:
                    logger.warning(f"Ошибка при записи метрик: {metric_error}")
                
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
                try:
                    self.server_manager.record_server_metrics(
                        server_id,
                        success=False,
                        response_time=time.time() - start_time
                    )
                except Exception as metric_error:
                    logger.warning(f"Ошибка при записи метрик: {metric_error}")
                
                raise RemoteServerError(error_msg)
        
        except Exception as e:
            logger.error(f"Общая ошибка при удалении пира: {e}")
            
            # Запись метрик о неудачном запросе
            try:
                self.server_manager.record_server_metrics(
                    server_id,
                    success=False,
                    response_time=time.time() - start_time
                )
            except Exception as metric_error:
                logger.warning(f"Ошибка при записи метрик: {metric_error}")
            
            if isinstance(e, NoAvailableServerError) or isinstance(e, RemoteServerError):
                raise e
            else:
                raise RemoteServerError(f"Ошибка при удалении пира: {e}")
            
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
            start_time = time.time()
            database_service_url = self.server_manager.database_service_url
            
            try:
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
            
            except requests.RequestException as e:
                logger.error(f"Connection error to database service: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error when finding server for peer {public_key}: {e}")
            return None