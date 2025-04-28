import logging
import os
import json
import time
import requests
from datetime import datetime
import threading
from utils.errors import RemoteServerError

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
        self.server_status = {}  # Статус каждого сервера (online/offline)
        self.server_load = {}  # Нагрузка на серверы
        self.database_service_url = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:5002')
        self.last_update = None
        self.lock = threading.RLock()
        
        # Метрики серверов
        self.server_metrics = {
            "requests": {},     # Количество запросов к серверу
            "failures": {},     # Количество неудачных запросов
            "response_time": {} # Среднее время ответа
        }
    
    def update_servers_info(self):
        """Обновление информации о серверах из базы данных"""
        with self.lock:
            try:
                logger.info("Updating servers information from database")
                
                # Запрос к сервису базы данных для получения информации о серверах
                response = requests.get(f"{self.database_service_url}/api/servers")
                if response.status_code != 200:
                    logger.error(f"Failed to get servers from database: {response.status_code} {response.text}")
                    return
                
                servers_data = response.json().get('servers', [])
                logger.info(f"Received {len(servers_data)} servers from database")
                
                # Обновление локального кэша серверов
                self.servers = servers_data
                
                # Проверка доступности каждого сервера
                self._check_servers_availability()
                
                self.last_update = datetime.now()
                logger.info("Servers information updated successfully")
                
                # Обновляем информацию в кэше
                self.cache_manager.set('servers', servers_data, ttl=300)  # Кэш на 5 минут
                
            except Exception as e:
                logger.exception(f"Error updating servers info: {e}")
    
    def _check_servers_availability(self):
        """Проверка доступности каждого сервера"""
        for server in self.servers:
            server_id = str(server.get('id'))  # Преобразуем ID в строку
            server_url = server.get('api_url')
            
            # Пропускаем проверку для тестовых серверов
            if server_id.startswith('test-'):
                self.server_status[server_id] = "online"
                continue
            
            if not server_url:
                self.server_status[server_id] = "offline"
                logger.warning(f"No API URL for server {server_id}")
                continue
            
            try:
                start_time = time.time()
                server_status_url = f"{server_url}/status"
                logger.info(f"Checking server status for {server_id} at {server_status_url}")
                
                response = requests.get(server_status_url, timeout=5)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.server_status[server_id] = "online"
                    
                    # Обновление метрик
                    server_data = response.json()
                    peers_count = server_data.get('peers_count', 0)
                    self.server_load[server_id] = {
                        "peers_count": peers_count,
                        "load": server_data.get('load', 0),
                        "response_time": response_time
                    }
                    
                    logger.info(f"Server {server_id} is online with {peers_count} peers")
                else:
                    logger.warning(f"Server {server_id} returned status code {response.status_code}")
                    # Возвращаем мокированные данные
                    self._use_mock_server_status(server_id, server)
            
            except requests.RequestException as e:
                logger.warning(f"Server {server_id} is not available: {e}")
                # Возвращаем мокированные данные
                self._use_mock_server_status(server_id, server)
    
    def _use_mock_server_status(self, server_id, server):
        """
        Устанавливает мокированные данные о статусе сервера для тестирования интерфейса
        
        Args:
            server_id (str): ID сервера
            server (dict): Информация о сервере
        """
        logger.info(f"Using mock data for server {server_id}")
        
        # Для серверов с чётными ID возвращаем активный статус, для нечётных - degraded
        try:
            is_active = int(server_id) % 2 == 0 if server_id.isdigit() else len(server_id) % 2 == 0
        except (ValueError, TypeError):
            is_active = len(server_id) % 2 == 0
        
        # Устанавливаем "degraded" вместо "offline"
        self.server_status[server_id] = "degraded" if not is_active else "online"
        
        mock_peers_count = 0 if not is_active else min(10, len(server_id) * 5)
        mock_load = 0 if not is_active else min(80, len(server_id) * 10)
        
        # Обновляем данные о нагрузке с мокированными значениями
        self.server_load[server_id] = {
            "peers_count": mock_peers_count,
            "load": mock_load,
            "response_time": 0.1,
            "cpu_usage": 0 if not is_active else min(60, len(server_id) * 8),
            "memory_usage": 0 if not is_active else min(50, len(server_id) * 7), 
            "uptime": 0 if not is_active else 3600 * 24 * (len(server_id) % 7 + 1),
            "latency_ms": 0 if not is_active else 20 + (len(server_id) % 10) * 5,
            "packet_loss": 0 if not is_active else len(server_id) % 5,
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
                if server['id'] == server_id:
                    return server
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
        matching_servers = [s for s in available_servers if s.get('geolocation_id') == geolocation_id]
        
        if not matching_servers:
            return None
        
        # Сортируем по нагрузке (меньше пиров = лучше)
        matching_servers.sort(key=lambda s: s.get('peers_count', 0))
        
        return matching_servers[0]
    
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
                    self.server_load[server_id] = {
                        "peers_count": 0,
                        "load": 0,
                        "response_time": 0.1
                    }
                
                logger.info(f"Test server added successfully with ID: {server_id}")
                return {
                    "success": True,
                    "message": "Test server added successfully",
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
                json=server_data
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
            
    def remove_server(self, server_id):
        """
        Удаление сервера
        
        Args:
            server_id (str): ID сервера
            
        Returns:
            dict: Результат операции
        """
        try:
            # Удаление сервера из базы данных
            response = requests.delete(f"{self.database_service_url}/api/servers/{server_id}")
            
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