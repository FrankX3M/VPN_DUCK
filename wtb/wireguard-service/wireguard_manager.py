import os
import uuid
import subprocess
import logging
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Каталог конфигурации WireGuard
WIREGUARD_DIR = "/etc/wireguard"
SERVER_CONFIG = os.path.join(WIREGUARD_DIR, "wg0.conf")
BACKUP_CONFIG = os.path.join(WIREGUARD_DIR, "wg0.conf.backup")
SERVER_PRIVATE_KEY = os.path.join(WIREGUARD_DIR, "private.key")
SERVER_PUBLIC_KEY = os.path.join(WIREGUARD_DIR, "public.key")
SERVER_ENDPOINT = os.getenv("SERVER_ENDPOINT", "your-server-endpoint.com")
SERVER_PORT = os.getenv("SERVER_PORT", "51820")
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "10.0.0.1/24")

def init_wireguard():
    """Инициализирует WireGuard, если он еще не настроен."""
    # Создаем каталог WireGuard, если он не существует
    if not os.path.exists(WIREGUARD_DIR):
        os.makedirs(WIREGUARD_DIR)
    
    # Проверяем наличие резервной копии
    if os.path.exists(BACKUP_CONFIG) and not os.path.exists(SERVER_CONFIG):
        logger.info("Используем резервную копию wg0.conf")
        shutil.copy(BACKUP_CONFIG, SERVER_CONFIG)
        
        # Извлекаем ключи из конфигурационного файла, если они есть
        try:
            with open(SERVER_CONFIG, 'r') as f:
                config_content = f.read()
                
            for line in config_content.split('\n'):
                if line.startswith('PrivateKey'):
                    private_key = line.split('=')[1].strip()
                    with open(SERVER_PRIVATE_KEY, 'w') as f:
                        f.write(private_key)
                    
                    # Генерируем публичный ключ из приватного
                    result = subprocess.run(
                        ["wg", "pubkey"], 
                        input=private_key.encode(), 
                        stdout=subprocess.PIPE
                    )
                    
                    with open(SERVER_PUBLIC_KEY, 'w') as f:
                        f.write(result.stdout.decode().strip())
                    
                    break
        except Exception as e:
            logger.error(f"Ошибка при чтении ключей из резервной копии: {str(e)}")
    
    # Генерируем ключи сервера, если их нет
    if not os.path.exists(SERVER_PRIVATE_KEY):
        logger.info("Генерация нового приватного ключа")
        subprocess.run(["wg", "genkey"], stdout=open(SERVER_PRIVATE_KEY, "w"))
    
    if not os.path.exists(SERVER_PUBLIC_KEY):
        logger.info("Генерация нового публичного ключа")
        with open(SERVER_PRIVATE_KEY, "r") as f:
            private_key = f.read().strip()
        
        result = subprocess.run(
            ["wg", "pubkey"], 
            input=private_key.encode(), 
            stdout=subprocess.PIPE
        )
        
        with open(SERVER_PUBLIC_KEY, "w") as f:
            f.write(result.stdout.decode().strip())
    
    # Создаем конфигурацию сервера, если её нет
    if not os.path.exists(SERVER_CONFIG):
        logger.info("Создание новой конфигурации сервера")
        with open(SERVER_PRIVATE_KEY, "r") as f:
            private_key = f.read().strip()
        
        server_config = (
            f"[Interface]\n"
            f"PrivateKey = {private_key}\n"
            f"Address = {SERVER_ADDRESS}\n"
            f"ListenPort = {SERVER_PORT}\n"
            f"SaveConfig = true\n"
        )
        
        with open(SERVER_CONFIG, "w") as f:
            f.write(server_config)
    
    # Запускаем интерфейс WireGuard, если он еще не запущен
    try:
        # Проверяем, запущен ли интерфейс
        wg_show = subprocess.run(["wg", "show"], capture_output=True)
        
        if wg_show.returncode != 0 or "wg0" not in wg_show.stdout.decode():
            logger.info("Запуск WireGuard интерфейса")
            subprocess.run(["wg-quick", "up", "wg0"])
        else:
            logger.info("WireGuard интерфейс уже запущен")
    except Exception as e:
        logger.error(f"Ошибка при запуске WireGuard: {str(e)}")
        # Попробуем запустить в любом случае
        try:
            subprocess.run(["wg-quick", "up", "wg0"])
        except Exception as e2:
            logger.error(f"Повторная ошибка при запуске WireGuard: {str(e2)}")

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

def generate_client_config(user_id):
    """Генерирует конфигурацию клиента WireGuard."""
    # Генерируем ключи клиента
    client_private_key, client_public_key = generate_client_keys()
    
    # Читаем публичный ключ сервера
    with open(SERVER_PUBLIC_KEY, "r") as f:
        server_public_key = f.read().strip()
    
    # Генерируем уникальный IP-адрес для клиента
    # Это простой пример - в продакшне может потребоваться более сложное распределение IP
    client_ip = f"10.0.0.{(user_id % 250) + 2}/24"
    
    # Создаем конфигурацию клиента
    client_config = (
        f"[Interface]\n"
        f"PrivateKey = {client_private_key}\n"
        f"Address = {client_ip}\n"
        f"DNS = 1.1.1.1, 8.8.8.8\n\n"
        f"[Peer]\n"
        f"PublicKey = {server_public_key}\n"
        f"Endpoint = {SERVER_ENDPOINT}:{SERVER_PORT}\n"
        f"AllowedIPs = 0.0.0.0/0\n"
        f"PersistentKeepalive = 25\n"
    )
    
    # Добавляем клиента в конфигурацию сервера
    add_peer_command = [
        "wg", "set", "wg0", 
        "peer", client_public_key,
        "allowed-ips", client_ip.split('/')[0] + "/32"
    ]
    
    try:
        subprocess.run(add_peer_command, check=True)
        
        # Сохраняем конфигурацию сервера
        subprocess.run(["wg-quick", "save", "wg0"], check=True)
        
        logger.info(f"Конфигурация клиента создана успешно для пользователя {user_id}")
        return client_config, client_public_key
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при добавлении пира: {e}")
        raise Exception(f"Ошибка при добавлении пира: {e}")

@app.route('/create', methods=['POST'])
def create_config():
    """Создает новую конфигурацию WireGuard для пользователя."""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    try:
        client_config, client_public_key = generate_client_config(user_id)
        
        return jsonify({
            "config": client_config,
            "public_key": client_public_key
        }), 201
    except Exception as e:
        logger.error(f"Error creating configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

# @app.route('/remove/<public_key>', methods=['DELETE'])
# def remove_config(public_key):
#     """Удаляет конфигурацию WireGuard по публичному ключу."""
#     try:
#         # Удаляем клиента из конфигурации сервера
#         remove_peer_command = [
#             "wg", "set", "wg0", 
#             "peer", public_key,
#             "remove"
#         ]
        
#         subprocess.run(remove_peer_command, check=True)
        
#         # Сохраняем конфигурацию сервера
#         subprocess.run(["wg-quick", "save", "wg0"], check=True)
        
#         return jsonify({"status": "success"}), 200
#     except Exception as e:
#         logger.error(f"Error removing configuration: {str(e)}")
#         return jsonify({"error": str(e)}), 500

@app.route('/remove', methods=['DELETE'])
def remove_config():
    """Удаляет конфигурацию WireGuard по публичному ключу."""
    try:
        data = request.get_json()
        public_key = data.get("public_key")

        if not public_key:
            return jsonify({"error": "Public key is required"}), 400

        # Удаление клиента из конфигурации WireGuard
        remove_peer_command = [
            "wg", "set", "wg0",
            "peer", public_key,
            "remove"
            ]
        subprocess.run(remove_peer_command, check=True)

        # Сохранение конфигурации
        subprocess.run(["wg-quick", "save", "wg0"], check=True)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Ошибка при удалении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():
    """Получает текущий статус WireGuard сервера."""
    try:
        # Выполняем команду wg show
        result = subprocess.run(["wg", "show"], capture_output=True, text=True, check=True)
        
        # Обрабатываем вывод
        output = result.stdout
        
        # Разбиваем вывод на информацию об интерфейсе и пирах
        parts = output.split("\n\n")
        
        response = {
            "status": "running",
            "interface": {},
            "peers": []
        }
        
        # Обрабатываем информацию об интерфейсе
        if parts and parts[0]:
            interface_lines = parts[0].strip().split("\n")
            for line in interface_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    response["interface"][key.strip()] = value.strip()
        
        # Обрабатываем информацию о пирах
        for i in range(1, len(parts)):
            if parts[i]:
                peer_info = {}
                peer_lines = parts[i].strip().split("\n")
                for line in peer_lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        peer_info[key.strip()] = value.strip()
                response["peers"].append(peer_info)
        
        return jsonify(response), 200
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            return jsonify({"status": "not running", "error": "WireGuard interface is not active"}), 200
        else:
            return jsonify({"status": "error", "error": str(e)}), 500
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    # Инициализируем WireGuard
    init_wireguard()
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=5001)