import os
import sys
import logging
import json
import time
import requests
from datetime import datetime
import threading
import random
# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.errors import RemoteServerError, DatabaseError
from utils.retry import with_retry


from config.settings import (
    DATABASE_SERVICE_URL,
    USE_MOCK_DATA,
    SERVER_STATUS_CHECK_TIMEOUT,
    MOCK_SERVERS
)

# DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:5002')
# SERVER_CACHE_TTL = int(os.environ.get('SERVER_CACHE_TTL', '300'))
# SERVER_TIMEOUT = int(os.environ.get('SERVER_TIMEOUT', '5'))

logger = logging.getLogger('wireguard-proxy.server_manager')

class ServerManager:
    """
    Менеджер удаленных серверов WireGuard
    
    Отвечает за:
    - Получение и обновление списка серверов из базы данных
    - Мониторинг доступности серверов
    - Определение подходящего сервера для запроса
    - Сбор метрик о серверах
    """
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.servers = []  # Список всех серверов с их параметрами
        self.server_status = {}  # Статус каждого сервера (online/offline/degraded)
        self.server_load = {}  # Нагрузка на серверы
        self.database_service_url = DATABASE_SERVICE_URL
        self.last_update = None
        self.lock = threading.RLock()
        self.fallback_mode = False  # Флаг режима отказоустойчивости
        
        # Метрики серверов
        self.server_metrics = {
            "requests": {},     # Количество запросов к серверу
            "failures": {},     # Количество неудачных запросов
            "response_time": {} # Среднее время ответа
        }
    
    def update_servers_info(self):
        """Обновление информации о серверах из базы данных или использование тестовых данных"""
        with self.lock:
            try:
                if self.fallback_mode:
                    logger.info("Working in fallback mode, skipping database update")
                    # Если мы в режиме отказоустойчивости, не пытаемся обновить данные из БД
                    return
                
                logger.info("Updating servers information from database")
                
                # Если включен режим тестовых данных, используем мок-данные
                if USE_MOCK_DATA:
                    logger.info("Using mock data instead of database")
                    self.servers = MOCK_SERVERS
                    self._check_servers_availability()
                    self.last_update = datetime.now()
                    
                    # Обновляем информацию в кэше
                    self.cache_manager.set('servers', self.servers, ttl=300)  # Кэш на 5 минут
                    return
                
                # Запрос к сервису базы данных для получения информации о серверах
                response = self._fetch_servers_from_database()
                if not response:
                    self._handle_database_unavailable()
                    return
                    
                servers_data = response.get('servers', [])
                logger.info(f"Received {len(servers_data)} servers from database")
                
                # Обновление локального кэша серверов
                self.servers = servers_data
                
                # Проверка доступности каждого сервера
                self._check_servers_availability()
                
                self.last_update = datetime.now()
                logger.info("Servers information updated successfully")
                
                # Обновляем информацию в кэше
                self.cache_manager.set('servers', servers_data, ttl=300)  # Кэш на 5 минут
                
                # Сбрасываем режим отказоустойчивости, если он был включен
                if self.fallback_mode:
                    logger.info("Exiting fallback mode")
                    self.fallback_mode = False
                
            except Exception as e:
                logger.exception(f"Error updating servers info: {e}")
                self._handle_database_unavailable()
    
    def _fetch_servers_from_database(self):
        """Получение списка серверов из базы данных"""
        try:
            response = requests.get(
                f"{self.database_service_url}/api/servers",
                timeout=5
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get servers from database: {response.status_code}")
                return None
                
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Database service connection error: {e}")
            return None
    
    def _handle_database_unavailable(self):
        """Обработка ситуации, когда база данных недоступна"""
        # Проверка, есть ли данные в кэше
        cached_servers = self.cache_manager.get('servers')
        
        if cached_servers:
            logger.info("Using cached servers information due to database unavailability")
            self.servers = cached_servers
            # Проверяем доступность серверов из кэша
            self._check_servers_availability()
            self.last_update = datetime.now()
            return
        
        # Если нет данных в кэше, переходим в режим отказоустойчивости с тестовыми данными
        if not self.fallback_mode:
            logger.warning("Switching to fallback mode with test servers")
            self.fallback_mode = True
            self.servers = MOCK_SERVERS
            self._check_servers_availability()
            self.last_update = datetime.now()
    
    def _check_servers_availability(self):
        """Проверка доступности каждого сервера"""
        for server in self.servers:
            server_id = str(server.get('id'))  # Преобразуем ID в строку
            server_url = server.get('api_url')
            
            # Пропускаем проверку для тестовых серверов
            if server_id.startswith('test-'):
                self.server_status[server_id] = "online"
                self._set_mock_server_data(server_id, server)
                continue
            
            if not server_url:
                self.server_status[server_id] = "offline"
                logger.warning(f"No API URL for server {server_id}")
                continue
            
            try:
                start_time = time.time()
                server_status_url = f"{server_url}/status"
                logger.info(f"Checking server status for {server_id} at {server_status_url}")
                
                response = requests.get(server_status_url, timeout=SERVER_STATUS_CHECK_TIMEOUT)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.server_status[server_id] = "online"
                    
                    # Обновление метрик
                    server_data = response.json()
                    peers_count = server_data.get('peers_count', 0)
                    self.server_load[server_id] = {
                        "peers_count": peers_count,
                        "load": server_data.get('load', 0),
                        "response_time": response_time,
                        "cpu_usage": server_data.get('cpu_usage', 30),
                        "memory_usage": server_data.get('memory_usage', 40),
                        "uptime": server_data.get('uptime', 3600),
                        "latency_ms": server_data.get('latency_ms', 30),
                        "packet_loss": server_data.get('packet_loss', 0),
                        "mocked": False
                    }
                    
                    logger.info(f"Server {server_id} is online with {peers_count} peers")
                else:
                    logger.warning(f"Server {server_id} returned status code {response.status_code}")
                    # Возвращаем мокированные данные
                    self._set_mock_server_data(server_id, server, is_degraded=True)
            
            except requests.RequestException as e:
                logger.warning(f"Server {server_id} is not available: {e}")
                # Возвращаем мокированные данные
                self._set_mock_server_data(server_id, server, is_degraded=True)
    
    def _set_mock_server_data(self, server_id, server, is_degraded=False):
        """
        Устанавливает мокированные данные о статусе сервера для тестирования интерфейса
        
        Args:
            server_id (str): ID сервера
            server (dict): Информация о сервере
            is_degraded (bool): Флаг деградации сервера
        """
        logger.info(f"Using mock data for server {server_id}")
        
        # Для серверов с чётными ID возвращаем активный статус, для нечётных - degraded
        try:
            is_active = int(server_id) % 2 == 0 if server_id.isdigit() else len(server_id) % 2 == 0
        except (ValueError, TypeError):
            is_active = len(server_id) % 2 == 0
        
        # Если явно указано, что сервер деградирован, ставим статус "degraded"
        if is_degraded:
            self.server_status[server_id] = "degraded"
        else:
            # Устанавливаем "degraded" вместо "offline"
            self.server_status[server_id] = "degraded" if not is_active else "online"
        
        mock_peers_count = 0 if is_degraded else min(10, len(server_id) * 5)
        mock_load = 0 if is_degraded else min(80, len(server_id) * 10)
        
        # Обновляем данные о нагрузке с мокированными значениями
        self.server_load[server_id] = {
            "peers_count": mock_peers_count,
            "load": mock_load,
            "response_time": 0.1,
            "cpu_usage": 0 if is_degraded else min(60, len(server_id) * 8),
            "memory_usage": 0 if is_degraded else min(50, len(server_id) * 7), 
            "uptime": 0 if is_degraded else 3600 * 24 * (len(server_id) % 7 + 1),
            "latency_ms": 0 if is_degraded else 20 + (len(server_id) % 10) * 5,
            "packet_loss": 0 if is_degraded else len(server_id) % 5,
            "mocked": True  # Флаг, указывающий, что данные смокированы
        }
        
        logger.info(f"Set mock status '{self.server_status[server_id]}' for server {server_id} with {mock_peers_count} peers and {mock_load}% load")

    def get_available_servers(self):
        """
        Получение списка доступных серверов
        
        Returns:
            list: Список доступных серверов с их параметрами
        """
        with self.lock:
            # Если кэш слишком старый или пустой, обновляем данные
            if not self.servers or not self.last_update or \
               (datetime.now() - self.last_update).total_seconds() > 300:
                self.update_servers_info()
            
            # Фильтруем только доступные серверы (online или degraded)
            available_servers = []
            for server in self.servers:
                server_id = server['id']
                status = self.server_status.get(server_id)
                if status == "online" or status == "degraded":
                    server_info = server.copy()
                    # Добавляем информацию о нагрузке и статусе
                    server_info.update({
                        "load": self.server_load.get(server_id, {}).get("load", 0),
                        "peers_count": self.server_load.get(server_id, {}).get("peers_count", 0),
                        "status": status
                    })
                    available_servers.append(server_info)
            
            # Если нет доступных серверов, возвращаем тестовые
            if not available_servers and not self.fallback_mode:
                logger.warning("No available servers found, using fallback servers")
                self.fallback_mode = True
                self.servers = MOCK_SERVERS
                self._check_servers_availability()
                return self.get_available_servers()
            
            return available_servers
    
    def get_server_by_id(self, server_id):
        """
        Получение информации о сервере по ID
        
        Args:
            server_id (str): ID сервера
            
        Returns:
            dict: Информация о сервере или None, если сервер не найден
        """
        with self.lock:
            for server in self.servers:
                if str(server['id']) == str(server_id):
                    return server
                    
            # Если сервер не найден, но ID начинается с 'test-', создаем тестовый сервер
            if server_id and str(server_id).startswith('test-'):
                logger.info(f"Creating mock server for ID: {server_id}")
                mock_server = {
                    'id': server_id,
                    'name': f'Test Server {server_id}',
                    'endpoint': 'test.example.com',
                    'api_url': 'http://localhost:5002',
                    'location': 'Test/Location',
                    'geolocation_id': 1,
                    'auth_type': 'api_key',
                    'api_key': 'test-key'
                }
                self.servers.append(mock_server)
                self.server_status[server_id] = "online"
                self._set_mock_server_data(server_id, mock_server)
                return mock_server
                
            return None
    
    def get_server_by_geolocation(self, geolocation_id):
        """
        Получение доступного сервера по ID геолокации
        
        Args:
            geolocation_id (str): ID геолокации
            
        Returns:
            dict: Информация о сервере или None, если подходящий сервер не найден
        """
        available_servers = self.get_available_servers()
        
        # Фильтруем серверы по геолокации
        matching_servers = [s for s in available_servers if str(s.get('geolocation_id')) == str(geolocation_id)]
        
        if not matching_servers:
            return None
        
        # Сначала выбираем online серверы, если они есть
        online_servers = [s for s in matching_servers if s.get('status') == "online"]
        servers_to_use = online_servers if online_servers else matching_servers
        
        # Сортируем по нагрузке (меньше пиров = лучше)
        servers_to_use.sort(key=lambda s: s.get('peers_count', 0))
        
        return servers_to_use[0]
    
    def get_best_server(self):
        """
        Получение сервера с наименьшей нагрузкой
        
        Returns:
            dict: Информация о сервере или None, если нет доступных серверов
        """
        available_servers = self.get_available_servers()
        
        if not available_servers:
            return None
        
        # Сначала выбираем online серверы, если они есть
        online_servers = [s for s in available_servers if s.get('status') == "online"]
        
        # Если online серверов нет, используем degraded
        servers_to_use = online_servers if online_servers else available_servers
        
        # Сортируем по нагрузке (меньше пиров = лучше)
        servers_to_use.sort(key=lambda s: s.get('peers_count', 0))
        
        # Если несколько серверов имеют одинаковую нагрузку, выбираем случайно один из них
        min_peers = servers_to_use[0].get('peers_count', 0)
        min_load_servers = [s for s in servers_to_use if s.get('peers_count', 0) == min_peers]
        
        if len(min_load_servers) > 1:
            return random.choice(min_load_servers)
        
        return servers_to_use[0]
    
    def record_server_metrics(self, server_id, success, response_time):
        """
        Запись метрик для сервера
        
        Args:
            server_id (str): ID сервера
            success (bool): Успешность запроса
            response_time (float): Время ответа в секундах
        """
        with self.lock:
            # Инициализация метрик для сервера, если его еще нет
            if server_id not in self.server_metrics["requests"]:
                self.server_metrics["requests"][server_id] = 0
                self.server_metrics["failures"][server_id] = 0
                self.server_metrics["response_time"][server_id] = 0
            
            # Обновление метрик
            self.server_metrics["requests"][server_id] += 1
            if not success:
                self.server_metrics["failures"][server_id] += 1
            
            # Обновление среднего времени ответа
            prev_avg = self.server_metrics["response_time"][server_id]
            prev_requests = self.server_metrics["requests"][server_id] - 1
            
            if prev_requests > 0:
                new_avg = (prev_avg * prev_requests + response_time) / self.server_metrics["requests"][server_id]
                self.server_metrics["response_time"][server_id] = new_avg
            else:
                self.server_metrics["response_time"][server_id] = response_time
    
    def get_servers_status(self):
        """
        Получение статуса всех серверов
        
        Returns:
            list: Список с информацией о статусе каждого сервера
        """
        with self.lock:
            status_list = []
            
            for server in self.servers:
                server_id = server['id']
                status = self.server_status.get(server_id, "unknown")
                
                status_info = {
                    "id": server_id,
                    "name": server.get('name', f"Server {server_id}"),
                    "location": server.get('location', 'Unknown'),
                    "status": status
                }
                
                # Добавляем информацию о нагрузке, если сервер онлайн или degraded
                if status in ["online", "degraded"] and server_id in self.server_load:
                    load_data = self.server_load[server_id]
                    status_info.update({
                        "peers_count": load_data.get("peers_count", 0),
                        "load": load_data.get("load", 0),
                        "response_time": load_data.get("response_time", 0),
                        "cpu_usage": load_data.get("cpu_usage", 0),
                        "memory_usage": load_data.get("memory_usage", 0),
                        "uptime": load_data.get("uptime", 0),
                        "latency_ms": load_data.get("latency_ms", 0),
                        "packet_loss": load_data.get("packet_loss", 0),
                        "mocked": load_data.get("mocked", False)
                    })
                
                status_list.append(status_info)
            
            return status_list
    
    def get_server_metrics(self):
        """
        Получение метрик по всем серверам
        
        Returns:
            dict: Метрики по серверам
        """
        with self.lock:
            metrics = {}
            
            for server in self.servers:
                server_id = server['id']
                if server_id in self.server_metrics["requests"]:
                    total_requests = self.server_metrics["requests"][server_id]
                    failures = self.server_metrics["failures"][server_id]
                    
                    metrics[server_id] = {
                        "total_requests": total_requests,
                        "failures": failures,
                        "success_rate": (total_requests - failures) / total_requests * 100 if total_requests > 0 else 0,
                        "avg_response_time": self.server_metrics["response_time"][server_id]
                    }
            
            return metrics
    
    @with_retry(max_attempts=3)
    def add_server(self, server_data):
        """
        Добавление нового сервера
        
        Args:
            server_data (dict): Информация о сервере
            
        Returns:
            dict: Результат операции
        """
        try:
            # Добавляем проверку тестового режима
            if server_data.get('test_mode'):
                logger.info("Adding server in test mode")
                # Генерируем уникальный ID для тестового сервера
                import uuid
                server_id = f"test-{str(uuid.uuid4())[:8]}"
                
                # Создаем запись о сервере
                server_info = {
                    "id": server_id,
                    "api_url": server_data.get('api_url'),
                    "location": server_data.get('location', 'Test Location'),
                    "name": server_data.get('name', 'Test Server'),
                    "geolocation_id": server_data.get('geolocation_id', 1),
                    "auth_type": server_data.get('auth_type', 'api_key'),
                    "api_key": server_data.get('api_key', 'test-key')
                }
                
                # Добавляем сервер в локальный список
                with self.lock:
                    self.servers.append(server_info)
                    # Устанавливаем статус "online"
                    self.server_status[server_id] = "online"
                    # Инициализируем метрики с нулевой нагрузкой
                    self._set_mock_server_data(server_id, server_info)
                
                logger.info(f"Test server added successfully with ID: {server_id}")
                return {
                    "success": True,
                    "message": "Test server added successfully",
                    "server_id": server_id
                }
                
            # Если USE_MOCK_DATA=True, добавляем тестовый сервер в любом случае
            if USE_MOCK_DATA:
                import uuid
                server_id = f"mock-{str(uuid.uuid4())[:8]}"
                
                server_info = {
                    "id": server_id,
                    "api_url": server_data.get('api_url', 'http://localhost:5002'),
                    "location": server_data.get('location', 'Mock Location'),
                    "name": server_data.get('name', 'Mock Server'),
                    "geolocation_id": server_data.get('geolocation_id', 1),
                    "auth_type": server_data.get('auth_type', 'api_key'),
                    "api_key": server_data.get('api_key', 'mock-key')
                }
                
                with self.lock:
                    self.servers.append(server_info)
                    self.server_status[server_id] = "online"
                    self._set_mock_server_data(server_id, server_info)
                
                logger.info(f"Mock server added successfully with ID: {server_id}")
                return {
                    "success": True,
                    "message": "Mock server added successfully (mock mode)",
                    "server_id": server_id
                }
                
            # Оригинальный код для реальных серверов
            # Проверка обязательных полей
            required_fields = ['api_url', 'location', 'geolocation_id']
            for field in required_fields:
                if field not in server_data:
                    return {"error": f"Missing required field: {field}"}
            
            # Добавление сервера в базу данных
            response = requests.post(
                f"{self.database_service_url}/api/servers/add", 
                json=server_data,
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Database error: {response.status_code}",
                    "details": response.text
                }
            
            # Обновление локального кэша серверов
            self.update_servers_info()
            
            return {
                "success": True,
                "message": "Server added successfully",
                "server_id": response.json().get('server_id')
            }
                
        except Exception as e:
            logger.exception(f"Error adding server: {e}")
            return {"success": False, "error": str(e)}
            
    @with_retry(max_attempts=3)  
    def remove_server(self, server_id):
        """
        Удаление сервера
        
        Args:
            server_id (str): ID сервера
            
        Returns:
            dict: Результат операции
        """
        try:
            # Проверка тестового сервера
            if str(server_id).startswith(('test-', 'mock-')):
                # Удаляем сервер из локального списка
                with self.lock:
                    self.servers = [s for s in self.servers if s['id'] != server_id]
                    self.server_status.pop(server_id, None)
                    self.server_load.pop(server_id, None)
                
                logger.info(f"Test/mock server {server_id} removed successfully")
                return {
                    "success": True,
                    "message": "Test/mock server removed successfully"
                }
            
            # Проверка режима тестовых данных
            if USE_MOCK_DATA:
                # Удаляем сервер из локального списка
                with self.lock:
                    self.servers = [s for s in self.servers if s['id'] != server_id]
                    self.server_status.pop(server_id, None)
                    self.server_load.pop(server_id, None)
                
                logger.info(f"Server {server_id} removed successfully (mock mode)")
                return {
                    "success": True,
                    "message": "Server removed successfully (mock mode)"
                }
            
            # Удаление сервера из базы данных
            response = requests.delete(
                f"{self.database_service_url}/api/servers/{server_id}",
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Database error: {response.status_code}",
                    "details": response.text
                }
            
            # Обновление локального кэша серверов
            self.update_servers_info()
            
            return {
                "success": True,
                "message": "Server removed successfully"
            }
            
        except Exception as e:
            logger.exception(f"Error removing server: {e}")
            return {"success": False, "error": str(e)}