import logging
import time
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
    def handle_create_request(self, data):
        """
        Обработка запроса на создание новой конфигурации
        
        Args:
            data (dict): Данные для создания конфигурации
            
        Returns:
            dict: Результат выполнения запроса от удаленного сервера
        """
        self.request_count["create"] += 1
        
        try:
            # Проверка наличия обязательных параметров
            user_id = data.get('user_id')
            if not user_id:
                raise ValueError("user_id is required")
            
            # Получение параметра геолокации, если указан
            geolocation_id = data.get('geolocation_id')
            
            # Выбор сервера на основе критериев
            server = self.connection_manager.get_suitable_server(geolocation_id)
            if not server:
                raise NoAvailableServerError(f"No available server for geolocation_id: {geolocation_id}")
            
            logger.info(f"Selected server for create request: {server['id']} ({server['location']})")
            
            # Выполнение запроса к удаленному серверу
            result = self.connection_manager.send_create_request(server['id'], data)
            
            # Сохранение маппинга публичный ключ -> сервер
            if result and 'public_key' in result:
                self.peer_server_mapping[result['public_key']] = server['id']
                # Сохраняем в кэш
                self.cache_manager.set(f"peer:{result['public_key']}", server['id'])
            
            return result
            
        except Exception as e:
            self.error_count["create"] += 1
            logger.error(f"Error in handle_create_request: {e}")
            raise
    
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