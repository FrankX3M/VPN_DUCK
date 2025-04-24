import os
import uuid
import subprocess
import logging
import shutil
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Каталог конфигурации для хранения данных удаленных серверов
WIREGUARD_DIR = "/app/configs"
REMOTE_ONLY = os.getenv("REMOTE_ONLY", "false").lower() == "true"
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:5002")

# Инициализируем структуру для отслеживания удаленных серверов
remote_servers = {}

def init_remote_servers():
    """Инициализирует структуру удаленных серверов."""
    global remote_servers
    
    # Создаем каталог для конфигураций, если он не существует
    if not os.path.exists(WIREGUARD_DIR):
        os.makedirs(WIREGUARD_DIR)
    
    logger.info("Инициализация в режиме удаленных серверов")
    
    # Загружаем информацию об удаленных серверах из БД
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=10)
        if response.status_code == 200:
            servers_data = response.json()
            servers = servers_data.get("servers", [])
            
            for server in servers:
                server_id = server.get("id")
                if server_id:
                    remote_servers[server_id] = {
                        "endpoint": server.get("endpoint"),
                        "port": server.get("port"),
                        "public_key": server.get("public_key"),
                        "address": server.get("address"),
                        "geolocation_id": server.get("geolocation_id"),
                        "active": server.get("status") == "active"
                    }
            
            logger.info(f"Загружено {len(remote_servers)} удаленных серверов")
        else:
            logger.warning(f"Не удалось загрузить информацию о серверах: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка при загрузке информации о серверах: {str(e)}")

def generate_client_keys():
    """Генерирует приватный и публичный ключи для клиента."""
    private_key_result = subprocess.run(["wg", "genkey"], stdout=subprocess.PIPE)
    private_key = private_key_result.stdout.decode().strip()
    
    public_key_result = subprocess.run(
        ["wg", "pubkey"], 
        input=private_key.encode(), 
        stdout=subprocess.PIPE
    )
    public_key = public_key_result.stdout.decode().strip()
    
    return private_key, public_key

def get_server_for_geolocation(geolocation_id):
    """
    Возвращает детали сервера для указанной геолокации через API базы данных.
    """
    if not geolocation_id:
        logger.warning("Геолокация не указана, выбираем первый доступный сервер")
        return get_first_available_server()
    
    try:
        # Запрос к API базы данных
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/servers/geolocation/{geolocation_id}", 
            timeout=5
        )
        
        if response.status_code == 200:
            servers_data = response.json()
            servers = servers_data.get("servers", [])
            
            # Фильтруем только активные серверы
            active_servers = [s for s in servers if s.get("status") == "active"]
            
            if active_servers:
                # Выбираем сервер с наименьшей нагрузкой
                server = min(active_servers, key=lambda s: s.get("load_factor", 100))
                
                return {
                    "public_key": server.get("public_key"),
                    "endpoint": server.get("endpoint"),
                    "port": server.get("port"),
                    "server_id": server.get("id"),
                    "address": server.get("address", "10.0.0.1/24")
                }
        
        # Если не удалось получить сервер, используем первый доступный
        logger.warning(f"Не удалось получить сервер для геолокации {geolocation_id}")
        return get_first_available_server()
    
    except Exception as e:
        logger.error(f"Ошибка при получении сервера для геолокации {geolocation_id}: {str(e)}")
        return get_first_available_server()

def get_first_available_server():
    """
    Возвращает первый доступный сервер из списка удаленных серверов.
    
    :return: Словарь с параметрами сервера или пустой словарь, если нет доступных серверов
    """
    try:
        # Запрос к API базы данных для получения всех серверов
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=5)
        
        if response.status_code == 200:
            servers_data = response.json()
            servers = servers_data.get("servers", [])
            
            # Фильтруем только активные серверы
            active_servers = [s for s in servers if s.get("status") == "active"]
            
            if active_servers:
                # Выбираем сервер с наименьшей нагрузкой
                server = min(active_servers, key=lambda s: s.get("load_factor", 100))
                
                return {
                    "public_key": server.get("public_key"),
                    "endpoint": server.get("endpoint"),
                    "port": server.get("port"),
                    "server_id": server.get("id"),
                    "address": server.get("address", "10.0.0.1/24")
                }
        
        # Если серверов нет или запрос не удался
        logger.error("Нет доступных серверов")
        return {}
    
    except Exception as e:
        logger.error(f"Ошибка при получении доступных серверов: {str(e)}")
        return {}

def generate_client_config(user_id, server_details):
    """
    Генерирует конфигурацию клиента для удаленного сервера WireGuard
    
    :param user_id: ID пользователя
    :param server_details: Детали удаленного сервера
    :return: Кортеж (конфигурация клиента, публичный ключ клиента)
    """
    if not server_details:
        raise Exception("Нет доступных серверов для создания конфигурации")
    
    # Генерируем ключи клиента
    client_private_key, client_public_key = generate_client_keys()
    
    # Получаем параметры сервера
    server_public_key = server_details.get('public_key')
    server_endpoint = server_details.get('endpoint')
    server_port = server_details.get('port')
    server_address = server_details.get('address', '10.0.0.1/24')
    
    if not (server_public_key and server_endpoint and server_port):
        raise Exception("Недостаточно данных о сервере для создания конфигурации")
    
    # Генерируем IP-адрес клиента на основе адреса сервера
    client_ip = generate_client_ip(user_id, server_address)
    
    logger.info(f"Создание конфигурации для пользователя {user_id}, сервер: {server_endpoint}:{server_port}")
    
    # Создаем конфигурацию клиента
    client_config = (
        f"[Interface]\n"
        f"PrivateKey = {client_private_key}\n"
        f"Address = {client_ip}\n"
        f"DNS = 1.1.1.1, 8.8.8.8\n\n"
        f"[Peer]\n"
        f"PublicKey = {server_public_key}\n"
        f"Endpoint = {server_endpoint}:{server_port}\n"
        f"AllowedIPs = 0.0.0.0/0\n"
        f"PersistentKeepalive = 25\n"
    )
    
    # Для удаленных серверов не нужно добавлять пир в локальную конфигурацию
    # Отправка запроса на добавление пира должна происходить на удаленном сервере
    # через отдельный API или механизм
    
    return client_config, client_public_key

def generate_client_ip(user_id, server_address):
    """
    Генерирует IP-адрес клиента на основе адреса сервера и ID пользователя
    
    :param user_id: ID пользователя
    :param server_address: Адрес сервера (формат: X.X.X.X/Y)
    :return: IP-адрес клиента
    """
    try:
        # Разбираем адрес сервера
        server_ip, netmask = server_address.split('/')
        base_parts = server_ip.split('.')
        
        if len(base_parts) != 4:
            # Если формат адреса некорректный, используем запасной вариант
            return f"10.0.0.{(user_id % 250) + 2}/24"
        
        # Выбираем последний октет на основе user_id
        # Используем модуль по 250, чтобы избежать конфликтов
        client_last_octet = (user_id % 250) + 2
        
        # Формируем IP-адрес клиента, меняя последний октет
        client_ip = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{client_last_octet}/{netmask}"
        return client_ip
    
    except Exception as e:
        logger.error(f"Ошибка при генерации IP клиента: {str(e)}")
        # Возвращаем запасной вариант
        return f"10.0.0.{(user_id % 250) + 2}/24"

@app.route('/create', methods=['POST'])
def create_config():
    """API для создания новой конфигурации WireGuard."""
    data = request.json
    user_id = data.get('user_id')
    geolocation_id = data.get('geolocation_id')
    
    if not user_id:
        return jsonify({"error": "Требуется ID пользователя"}), 400
    
    try:
        # Получаем информацию о сервере для указанной геолокации
        server_details = get_server_for_geolocation(geolocation_id)
        
        if not server_details:
            return jsonify({"error": "Нет доступных серверов"}), 503
        
        # Создаем конфигурацию клиента
        client_config, client_public_key = generate_client_config(user_id, server_details)
        
        # Возвращаем результат
        return jsonify({
            "config": client_config,
            "public_key": client_public_key,
            "server_id": server_details.get("server_id"),
            "geolocation_id": geolocation_id
        }), 201
    
    except Exception as e:
        logger.error(f"Ошибка при создании конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/remove/<public_key>', methods=['DELETE'])
def remove_peer(public_key):
    """API для удаления пира с удаленного сервера."""
    if not public_key:
        return jsonify({"error": "Требуется публичный ключ"}), 400
    
    try:
        # Для удаленных серверов это может быть API-запрос к серверу
        # Здесь мы просто логируем, что запрос на удаление был получен
        logger.info(f"Получен запрос на удаление пира с ключом {public_key}")
        
        # В реальной реализации здесь был бы запрос к удаленному серверу
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        logger.error(f"Ошибка при удалении пира: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers', methods=['GET'])
def get_servers():
    """API для получения списка доступных серверов."""
    try:
        # Получаем список серверов из базы данных
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=5)
        
        if response.status_code == 200:
            servers_data = response.json()
            
            # Фильтруем только активные серверы
            servers = servers_data.get("servers", [])
            active_servers = [s for s in servers if s.get("status") == "active"]
            
            return jsonify({"servers": active_servers, "active": len(active_servers)}), 200
        else:
            return jsonify({"error": f"Ошибка при получении серверов: HTTP {response.status_code}"}), 500
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers', methods=['POST'])
def add_remote_server():
    """API для добавления нового удаленного сервера."""
    data = request.json
    
    required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Отправляем запрос на регистрацию сервера в базе данных
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/register",
            json=data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            server_id = result.get("server_id")
            
            # Обновляем локальную структуру серверов
            remote_servers[server_id] = {
                "endpoint": data.get("endpoint"),
                "port": data.get("port"),
                "public_key": data.get("public_key"),
                "address": data.get("address"),
                "geolocation_id": data.get("geolocation_id"),
                "active": True
            }
            
            return jsonify({"status": "success", "server_id": server_id}), 201
        else:
            return jsonify({"error": f"Ошибка при регистрации сервера: HTTP {response.status_code}"}), 500
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении удаленного сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/<server_id>', methods=['DELETE'])
def remove_remote_server(server_id):
    """API для удаления удаленного сервера."""
    if not server_id:
        return jsonify({"error": "Требуется ID сервера"}), 400
    
    try:
        # Отправляем запрос на удаление сервера из базы данных
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            # Удаляем сервер из локальной структуры
            if server_id in remote_servers:
                del remote_servers[server_id]
            
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"error": f"Ошибка при удалении сервера: HTTP {response.status_code}"}), 500
    
    except Exception as e:
        logger.error(f"Ошибка при удалении удаленного сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """API для получения статуса сервиса управления WireGuard."""
    try:
        # Подсчитываем количество активных серверов
        active_count = sum(1 for server in remote_servers.values() if server.get("active", False))
        
        return jsonify({
            "status": "running",
            "mode": "remote_only" if REMOTE_ONLY else "local",
            "remote_servers": len(remote_servers),
            "active_servers": active_count
        }), 200
    
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    # Инициализируем сервис в зависимости от режима работы
    init_remote_servers()
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=5001)