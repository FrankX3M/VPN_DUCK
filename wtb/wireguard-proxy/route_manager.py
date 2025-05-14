import os
import sys
import logging
import time
from flask import jsonify, request

# Добавляем текущую директорию в PYTHONPATH
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.errors import NoAvailableServerError, RemoteServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger('wireguard-proxy.route_manager')

class RouteManager:
    """
    Менеджер маршрутизации запросов к удаленным серверам WireGuard
    
    Отвечает за:
    - Выбор подходящего сервера для запроса
    - Передачу запроса через ConnectionManager
    - Обработку ошибок и повторные попытки
    - Ведение статистики запросов
    """
    
    def __init__(self, connection_manager, cache_manager):
        self.connection_manager = connection_manager
        self.cache_manager = cache_manager
        self.request_count = {
            "create": 0,
            "remove": 0,
            "status": 0,
            "other": 0
        }
        self.error_count = {
            "create": 0,
            "remove": 0,
            "status": 0,
            "other": 0
        }
        self.peer_server_mapping = {}  # Кэш для быстрого определения сервера пира
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RemoteServerError),
        reraise=True
    )
    
    def handle_create_request(self):
        """
        Обработка запроса на создание новой конфигурации
        
        Returns:
            Response: объект flask.Response с результатом обработки запроса
        """
        try:
            # Получаем данные из запроса
            data = request.get_json()
            if not data:
                return jsonify({"error": "Не предоставлены данные"}), 400
            
            user_id = data.get("user_id")
            geolocation_id = data.get("geolocation_id")
            
            if not user_id:
                return jsonify({"error": "Не указан user_id"}), 400
            
            try:
                # Пытаемся получить список доступных серверов
                available_servers = list(self.connection_manager.get_available_servers())
                logger.info(f"Получено {len(available_servers)} серверов")
            except Exception as e:
                logger.warning(f"Ошибка при получении списка серверов: {str(e)}")
                logger.info("Создаем тестовый сервер напрямую")
                # Создаем тестовый сервер вручную
                available_servers = [{
                    'id': '1',
                    'name': 'Test Server',
                    'endpoint': 'wireguard-service',
                    'port': 51820,
                    'location': 'Moscow, Russia',
                    'geolocation_id': '1',
                    'geolocation_name': 'Россия',
                    'public_key': 'test_public_key_placeholder',
                    'address': '10.0.0.1/24',
                    'status': 'active',
                    'load': 0
                }]
            
            # Если список серверов пуст, создаем тестовый сервер
            if not available_servers:
                logger.warning("Список серверов пуст, создаем тестовый сервер")
                available_servers = [{
                    'id': '1',
                    'name': 'Test Server',
                    'endpoint': 'wireguard-service',
                    'port': 51820,
                    'location': 'Moscow, Russia',
                    'geolocation_id': '1',
                    'geolocation_name': 'Россия',
                    'public_key': 'test_public_key_placeholder',
                    'address': '10.0.0.1/24',
                    'status': 'active',
                    'load': 0
                }]
            
            # Если указана геолокация, выбираем сервер из этой геолокации или любой, если нет соответствующей геолокации
            if geolocation_id:
                logger.info(f"Выбор сервера для геолокации {geolocation_id}")
                
                # Получаем список доступных серверов для данной геолокации
                geo_servers = list(filter(
                    lambda s: str(s.get("geolocation_id")) == str(geolocation_id) and s.get("status") in ["active", "online"], 
                    available_servers
                ))
                
                if not geo_servers:
                    logger.warning(f"Нет доступных серверов для геолокации {geolocation_id}, используем любой доступный сервер")
                    geo_servers = available_servers
                
                # Сортируем серверы по загрузке (от наименее загруженного к наиболее)
                geo_servers.sort(key=lambda s: s.get("load", 100))
                
                # Выбираем наименее загруженный сервер
                selected_server = geo_servers[0]
                server_id = selected_server.get("id")
                
                logger.info(f"Выбран сервер {server_id} с загрузкой {selected_server.get('load', 'N/A')}%")
            else:
                # Если геолокация не указана, выбираем случайный доступный сервер
                logger.info("Геолокация не указана, выбираем сервер случайным образом")
                
                # Получаем список всех доступных серверов
                active_servers = list(filter(
                    lambda s: s.get("status") in ["active", "online"], 
                    available_servers
                ))
                
                if not active_servers:
                    logger.warning("Нет активных серверов, используем первый сервер")
                    active_servers = available_servers
                
                # Сортируем серверы по загрузке (от наименее загруженного к наиболее)
                active_servers.sort(key=lambda s: s.get("load", 100))
                
                # Выбираем сервер с наименьшей загрузкой
                selected_server = active_servers[0]
                server_id = selected_server.get("id")
                
                logger.info(f"Выбран сервер {server_id} с загрузкой {selected_server.get('load', 'N/A')}%")
            
            # Создаем конфигурацию на выбранном сервере
            logger.info(f"Отправляем запрос на создание конфигурации на сервер {server_id}")
            
            try:
                # Обработка запроса на создание конфигурации
                response = self.connection_manager.send_create_request(server_id, data)
                
                # Логируем информацию о созданной конфигурации
                if "public_key" in response:
                    logger.info(f"Конфигурация успешно создана на сервере {server_id}. Public key: {response.get('public_key')}")
                
                # Добавляем информацию о выбранном сервере
                response["server_id"] = server_id
                if "geolocation_id" not in response:
                    response["geolocation_id"] = selected_server.get("geolocation_id")
                
                # Возвращаем успешный ответ
                return jsonify(response), 201
                
            except Exception as e:
                # Логируем ошибку
                logger.error(f"Ошибка при создании конфигурации: {str(e)}")
                
                # Возвращаем ошибку
                return jsonify({"error": str(e)}), 500
                
        except Exception as e:
            # Если произошла неожиданная ошибка
            logger.error(f"Неожиданная ошибка при обработке запроса: {str(e)}", exc_info=True)
            return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RemoteServerError),
        reraise=True
    )
    def handle_remove_request(self, public_key):
        """
        Обработка запроса на удаление пира
        
        Args:
            public_key (str): Публичный ключ пира
            
        Returns:
            dict: Результат выполнения запроса от удаленного сервера
        """
        self.request_count["remove"] += 1
        
        try:
            # Определение сервера, на котором находится пир
            server_id = self._find_server_for_peer(public_key)
            if not server_id:
                logger.warning(f"Server not found for peer with public key: {public_key}")
                # Если не нашли сервер, пробуем удалить на всех доступных серверах
                return self._remove_from_all_servers(public_key)
            
            logger.info(f"Found server {server_id} for peer {public_key}")
            
            # Выполнение запроса к удаленному серверу
            result = self.connection_manager.send_remove_request(server_id, public_key)
            
            # Удаление маппинга из кэша
            self.peer_server_mapping.pop(public_key, None)
            self.cache_manager.delete(f"peer:{public_key}")
            
            return result
            
        except Exception as e:
            self.error_count["remove"] += 1
            logger.error(f"Error in handle_remove_request: {e}")
            raise
    
    def _find_server_for_peer(self, public_key):
        """
        Определение сервера для пира по публичному ключу
        
        Args:
            public_key (str): Публичный ключ пира
            
        Returns:
            str: ID сервера или None, если не найден
        """
        # Сначала проверяем в локальном кэше
        if public_key in self.peer_server_mapping:
            return self.peer_server_mapping[public_key]
        
        # Затем в глобальном кэше
        server_id = self.cache_manager.get(f"peer:{public_key}")
        if server_id:
            # Обновляем локальный кэш
            self.peer_server_mapping[public_key] = server_id
            return server_id
        
        # Если не нашли в кэше, запрашиваем данные из БД
        try:
            # Этот метод должен обратиться к базе данных для поиска сервера,
            # на котором размещен пир с указанным публичным ключом
            server_id = self.connection_manager.find_server_for_peer(public_key)
            if server_id:
                # Обновляем локальный и глобальный кэш
                self.peer_server_mapping[public_key] = server_id
                self.cache_manager.set(f"peer:{public_key}", server_id)
            return server_id
        except Exception as e:
            logger.error(f"Error finding server for peer {public_key}: {e}")
            return None
    
    def _remove_from_all_servers(self, public_key):
        """
        Попытка удалить пир со всех доступных серверов
        
        Args:
            public_key (str): Публичный ключ пира
            
        Returns:
            dict: Результаты выполнения запросов к удаленным серверам
        """
        results = {}
        servers = self.connection_manager.get_all_servers()
        
        for server in servers:
            try:
                logger.info(f"Attempting to remove peer {public_key} from server {server['id']}")
                result = self.connection_manager.send_remove_request(server['id'], public_key)
                results[server['id']] = {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Failed to remove peer {public_key} from server {server['id']}: {e}")
                results[server['id']] = {"success": False, "error": str(e)}
        
        # Если хотя бы одно удаление прошло успешно, считаем операцию успешной
        success = any(r.get("success", False) for r in results.values())
        
        return {
            "success": success,
            "message": "Attempted to remove peer from all servers",
            "details": results
        }
    
    def get_request_count(self):
        """Получение счетчиков запросов"""
        return self.request_count
    
    def get_error_count(self):
        """Получение счетчиков ошибок"""
        return self.error_count