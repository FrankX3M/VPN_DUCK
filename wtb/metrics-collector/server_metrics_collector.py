#!/usr/bin/env python3
# metrics-collector/server_metrics_collector.py
import os
import time
import logging
import requests
import subprocess
import json
import socket
import statistics
try:
    import PyJWT as jwt
except ImportError:
    import jwt
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics-collector")

# Конфигурация подключения к API Gateway
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', 'http://kong:8000')
ADMIN_SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'fvcfq9d3ycefnvmftiaso')

# Параметры сбора данных
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', 120))  # Интервал сбора в секундах (2 минуты по умолчанию)
PING_COUNT = int(os.getenv('PING_COUNT', 10))  # Количество пингов для измерения
MAINTENANCE_INTERVAL = int(os.getenv('MAINTENANCE_INTERVAL', 3600))  # Интервал обслуживания в секундах (1 час)
STARTUP_DELAY = int(os.getenv('STARTUP_DELAY', 30))  # Задержка запуска в секундах

# Логирование начальной конфигурации
logger.info(f"Используем API_GATEWAY_URL: {API_GATEWAY_URL}")
logger.info(f"Интервал сбора данных: {COLLECTION_INTERVAL} секунд")

def get_auth_headers():
    """
    Создает и возвращает заголовки аутентификации для API запросов
    
    Returns:
        tuple: (simple_headers, jwt_headers) - два типа заголовков для разных типов аутентификации
    """
    # API Key для простой аутентификации
    simple_headers = {
        "apikey": ADMIN_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    # JWT токен для более сложной аутентификации
    payload = {
        "iss": "metrics-collector",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time())
    }
    
    token = jwt.encode(payload, ADMIN_SECRET_KEY, algorithm="HS256")
    
    # Если jwt.encode вернул bytes в PyJWT <2.0.0, преобразуем в строку
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    jwt_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    return simple_headers, jwt_headers

def get_servers():
    """
    Получает список всех активных серверов через API Gateway.
    
    Пробует использовать разные эндпоинты, если первый не сработал.
    
    Returns:
        list: Список серверов или пустой список в случае ошибки
    """
    simple_headers, jwt_headers = get_auth_headers()
    
    # Список возможных эндпоинтов для получения серверов
    endpoint_configs = [
        {"url": f"{API_GATEWAY_URL}/api/servers/all", "headers": simple_headers},
        {"url": f"{API_GATEWAY_URL}/api/servers", "headers": simple_headers},
        {"url": f"{API_GATEWAY_URL}/api/servers/active", "headers": simple_headers},
        {"url": f"{API_GATEWAY_URL}/vpn/servers", "headers": simple_headers},
        # Добавим варианты с JWT аутентификацией
        {"url": f"{API_GATEWAY_URL}/api/servers/all", "headers": jwt_headers},
        {"url": f"{API_GATEWAY_URL}/api/servers", "headers": jwt_headers},
        {"url": f"{API_GATEWAY_URL}/api/servers/active", "headers": jwt_headers},
        {"url": f"{API_GATEWAY_URL}/vpn/servers", "headers": jwt_headers}
    ]
    
    for config in endpoint_configs:
        full_url = config["url"]
        headers = config["headers"]
        logger.info(f"Пробуем получить серверы с: {full_url}")
        
        try:
            response = requests.get(
                full_url,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Обработка разных форматов ответа
                    if isinstance(data, dict) and "servers" in data:
                        servers = data["servers"]
                    elif isinstance(data, list):
                        servers = data
                    else:
                        logger.warning(f"Неожиданный формат данных: {data}")
                        continue
                    
                    if servers:
                        logger.info(f"Получено {len(servers)} серверов с {full_url}")
                        return servers
                    else:
                        logger.warning(f"Получен пустой список серверов с {full_url}")
                        
                except ValueError as e:
                    logger.warning(f"Ошибка парсинга JSON с {full_url}: {str(e)}")
            else:
                logger.warning(f"Неудачный запрос к {full_url}: код {response.status_code}, ответ: {response.text}")
                
        except requests.RequestException as e:
            logger.warning(f"Ошибка запроса к {full_url}: {str(e)}")
            
    # Если все запросы неудачны, возвращаем тестовый сервер
    logger.warning("Не удалось получить список серверов, использую тестовый сервер")
    return [{
        'id': 1,
        'name': 'Тестовый сервер',
        'endpoint': 'localhost',
        'port': 51820,
        'location': 'Тестовое расположение',
        'geolocation_id': 1,
        'public_key': get_wireguard_public_key(),
        'status': 'active'
    }]

def get_wireguard_public_key():
    """
    Получает публичный ключ WireGuard интерфейса.
    
    Returns:
        str: Публичный ключ или строка "unknown_key" в случае ошибки
    """
    try:
        wg_result = subprocess.run(
            ["wg", "show", "all", "dump"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        if wg_result.returncode != 0:
            logger.error(f"Ошибка при выполнении команды wg show: {wg_result.stderr}")
            return "unknown_key"
        
        # Парсим вывод команды wg (первая строка, второе поле)
        lines = wg_result.stdout.strip().split('\n')
        if lines and '\t' in lines[0]:
            parts = lines[0].split('\t')
            if len(parts) > 1:
                return parts[1]
        
        return "unknown_key"
    except Exception as e:
        logger.error(f"Ошибка при получении публичного ключа WireGuard: {str(e)}")
        return "unknown_key"

def get_wireguard_status():
    """
    Получает статус WireGuard и информацию о пирах.
    
    Returns:
        dict: Словарь с информацией об интерфейсе и пирах или None в случае ошибки
    """
    try:
        wg_result = subprocess.run(
            ["wg", "show", "all", "dump"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if wg_result.returncode != 0:
            logger.error(f"Ошибка при выполнении команды wg show: {wg_result.stderr}")
            return None
        
        # Парсим вывод команды wg
        lines = wg_result.stdout.strip().split('\n')
        
        # Получаем информацию об интерфейсе (из первой строки)
        interface_data = {}
        if lines and '\t' in lines[0]:
            interface_parts = lines[0].split('\t')
            interface_data = {
                "name": interface_parts[0] if len(interface_parts) > 0 else "",
                "public_key": interface_parts[1] if len(interface_parts) > 1 else "",
                "private_key": "hidden",  # Не отображаем приватный ключ
                "listen_port": interface_parts[2] if len(interface_parts) > 2 else ""
            }
        
        # Получаем информацию о пирах (из остальных строк)
        peers = []
        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) >= 5:
                peer = {
                    "public_key": parts[0],
                    "preshared_key": "hidden",  # Не отображаем preshared ключ
                    "endpoint": parts[1],
                    "allowed_ips": parts[2],
                    "latest_handshake": int(parts[3]) if parts[3] else 0,
                    "transfer_rx": int(parts[4]) if parts[4] and parts[4].isdigit() else 0,
                    "transfer_tx": int(parts[5]) if len(parts) > 5 and parts[5] and parts[5].isdigit() else 0
                }
                peers.append(peer)
        
        logger.info(f"Получено {len(peers)} пиров WireGuard")
        return {
            "interface": interface_data,
            "peers": peers
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статуса WireGuard: {str(e)}")
        return None

def count_active_connections(peers):
    """
    Подсчитывает количество активных подключений на основе последнего handshake.
    
    Args:
        peers (list): Список пиров WireGuard
        
    Returns:
        int: Количество активных подключений
    """
    if not peers:
        return 0
        
    try:
        active_count = 0
        current_time = int(time.time())
        
        for peer in peers:
            # Проверяем, был ли handshake в последние 3 минуты
            last_handshake = peer.get("latest_handshake", 0)
            if last_handshake and (current_time - last_handshake) < 180:  # 3 минуты
                active_count += 1
        
        logger.info(f"Активных подключений: {active_count} из {len(peers)} пиров")
        return active_count
    except Exception as e:
        logger.error(f"Ошибка при подсчете активных подключений: {str(e)}")
        return 0

def update_server_metrics(server_id, active_connections, latency=None, packet_loss=None):
    """
    Обновляет метрики сервера в базе данных.
    
    Args:
        server_id (str): ID сервера
        active_connections (int): Количество активных подключений
        latency (float, optional): Задержка в мс
        packet_loss (float, optional): Потеря пакетов в %
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        logger.info(f"Обновление метрик для сервера {server_id}: {active_connections} активных подключений")
        
        # Подготавливаем данные для отправки в API
        metrics_data = {
            "server_id": server_id,
            "timestamp": datetime.now().isoformat(),
            "peers_count": active_connections,
            "is_available": True,
            "success": True
        }
        
        # Добавляем дополнительные метрики, если они предоставлены
        if latency is not None:
            metrics_data["latency"] = latency
        
        if packet_loss is not None:
            metrics_data["packet_loss"] = packet_loss
        
        # Получаем заголовки аутентификации для API Gateway
        simple_headers, jwt_headers = get_auth_headers()
        
        # Пробуем разные эндпоинты для отправки метрик
        endpoints = [
            "/api/server_metrics/add",
            "/api/metrics/add",
            "/api/servers/update_metrics"
        ]
        
        for endpoint in endpoints:
            url = f"{API_GATEWAY_URL}{endpoint}"
            logger.debug(f"Отправка метрик на URL: {url}")
            
            try:
                response = requests.post(
                    url,
                    json=metrics_data,
                    headers=simple_headers,  # Используем простую аутентификацию
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Метрики успешно обновлены для сервера {server_id}")
                    return True
                else:
                    logger.warning(f"Ошибка при отправке метрик на {url}: {response.status_code}")
                    
                    # Попробуем с JWT аутентификацией, если API Key не сработал
                    response = requests.post(
                        url,
                        json=metrics_data,
                        headers=jwt_headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Метрики успешно обновлены для сервера {server_id} с JWT")
                        return True
                    else:
                        logger.warning(f"Ошибка при отправке метрик с JWT на {url}: {response.status_code}")
                        
            except requests.RequestException as e:
                logger.warning(f"Ошибка запроса к {url}: {str(e)}")
        
        logger.error(f"Не удалось обновить метрики сервера {server_id} через все доступные эндпоинты")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении метрик сервера {server_id}: {str(e)}")
        return False

def measure_latency(server_endpoint, count=10):
    """
    Измеряет задержку до сервера с помощью ping.
    
    Args:
        server_endpoint (str): IP-адрес или домен сервера
        count (int): Количество ping-запросов
        
    Returns:
        tuple: (средняя задержка в мс, процент потери пакетов)
    """
    try:
        # Определяем команду ping в зависимости от ОС
        if os.name == 'posix':  # Linux или macOS
            cmd = ["ping", "-c", str(count), server_endpoint]
        else:  # Windows
            cmd = ["ping", "-n", str(count), server_endpoint]
            
        logger.debug(f"Выполнение команды: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.warning(f"Ping к {server_endpoint} не удался: {result.stderr}")
            return None, 100.0  # 100% потери пакетов
            
        # Парсим результаты ping для Linux/macOS
        if os.name == 'posix':
            # Извлекаем строку потери пакетов
            packet_loss_line = [line for line in result.stdout.split('\n') if "packet loss" in line]
            if packet_loss_line:
                # Обычный формат: "4 packets transmitted, 4 received, 0% packet loss"
                parts = packet_loss_line[0].split(',')
                for part in parts:
                    if "packet loss" in part:
                        packet_loss = float(part.strip().split('%')[0])
                        break
                else:
                    packet_loss = 0
            else:
                packet_loss = 0
                
            # Извлекаем строку со статистикой времени
            rtt_line = [line for line in result.stdout.split('\n') if "min/avg/max" in line]
            if rtt_line:
                # Обычный формат: "rtt min/avg/max/mdev = 0.055/0.132/0.223/0.062 ms"
                rtt_values = rtt_line[0].split('=')[1].strip().split('/')
                avg_latency = float(rtt_values[1])
            else:
                avg_latency = None
        else:
            # Парсинг для Windows
            lines = result.stdout.split('\n')
            packet_loss_line = [line for line in lines if "Lost" in line or "loss" in line]
            if packet_loss_line:
                parts = packet_loss_line[0].split(',')
                for part in parts:
                    if "Lost" in part or "loss" in part:
                        try:
                            # Формат типа: "Lost = 0 (0% loss)"
                            packet_loss = float(part.strip().split('%')[0].split('(')[1])
                        except:
                            packet_loss = 0
                        break
                else:
                    packet_loss = 0
            else:
                packet_loss = 0
                
            # Извлекаем строку со средним временем
            avg_line = [line for line in lines if "Average" in line]
            if avg_line:
                # Формат типа: "Average = 10ms"
                try:
                    avg_latency = float(avg_line[0].split('=')[1].strip().replace('ms', ''))
                except:
                    avg_latency = None
            else:
                avg_latency = None
        
        return avg_latency, packet_loss
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout при выполнении ping к {server_endpoint}")
        return None, 100.0
    except Exception as e:
        logger.error(f"Ошибка при измерении задержки: {str(e)}")
        return None, 100.0

def main():
    """
    Основная функция для сбора и обновления метрик.
    """
    logger.info("Запуск сервиса сбора метрик")
    
    # Ждем, пока другие сервисы запустятся
    logger.info(f"Ожидание {STARTUP_DELAY} секунд для запуска других сервисов...")
    time.sleep(STARTUP_DELAY)
    
    while True:
        try:
            # Получаем список серверов через API Gateway
            servers = get_servers()
            
            if not servers:
                logger.warning("Не удалось получить список серверов или список пуст")
                time.sleep(60)  # Ждем минуту перед следующей попыткой
                continue
            
            # Получаем статус WireGuard
            wg_status = get_wireguard_status()
            
            if not wg_status:
                logger.warning("Не удалось получить статус WireGuard")
                time.sleep(60)
                continue
            
            # Подсчитываем активные подключения
            active_connections = count_active_connections(wg_status.get("peers", []))
            
            # Находим наш сервер и обновляем его метрики
            found_server = False
            for server in servers:
                # Проверяем, что это наш сервер (по публичному ключу)
                server_public_key = server.get("public_key")
                interface_public_key = wg_status.get("interface", {}).get("public_key")
                
                if server_public_key == interface_public_key:
                    server_id = server.get("id")
                    logger.info(f"Найден наш сервер: {server_id}")
                    found_server = True
                    
                    # Измеряем задержку если это возможно
                    server_endpoint = server.get("endpoint")
                    latency, packet_loss = None, None
                    
                    if server_endpoint and server_endpoint != "localhost":
                        latency, packet_loss = measure_latency(server_endpoint, PING_COUNT)
                        logger.info(f"Измеренная задержка до {server_endpoint}: {latency}ms, потеря пакетов: {packet_loss}%")
                    
                    # Обновляем метрики сервера через API Gateway
                    update_server_metrics(server_id, active_connections, latency, packet_loss)
                    break
            
            if not found_server:
                logger.warning("Не найден соответствующий сервер в списке. Проверьте публичные ключи.")
            
            # Ждем до следующего обновления
            logger.info(f"Ожидание {COLLECTION_INTERVAL} секунд до следующего обновления...")
            time.sleep(COLLECTION_INTERVAL)
            
        except Exception as e:
            logger.error(f"Произошла ошибка в основном цикле: {str(e)}")
            logger.exception("Подробный стек вызовов:")
            time.sleep(60)  # Ждем минуту перед следующей попыткой

if __name__ == "__main__":
    main()