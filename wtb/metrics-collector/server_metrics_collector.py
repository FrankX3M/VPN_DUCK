#!/usr/bin/env python3
import os
import time
import logging
import requests
import subprocess
import json
import socket
import statistics
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics-collector")

# Параметры подключения к API с динамическим определением хостов
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL', 'http://database-service:5002')
WIREGUARD_SERVICE_URL = os.getenv('WIREGUARD_SERVICE_URL', 'http://wireguard-proxy:5001')

logger.info(f"Используем DATABASE_SERVICE_URL: {DATABASE_SERVICE_URL}")
logger.info(f"Используем WIREGUARD_SERVICE_URL: {WIREGUARD_SERVICE_URL}")

# Другие параметры
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', 120))  # Интервал сбора в секундах (2 минуты по умолчанию)
PING_COUNT = int(os.getenv('PING_COUNT', 10))  # Количество пингов для измерения
MAINTENANCE_INTERVAL = int(os.getenv('MAINTENANCE_INTERVAL', 3600))  # Интервал обслуживания в секундах (1 час)

def get_servers():
    """Получает список всех активных серверов из базы данных."""
    try:
        url = f"{DATABASE_SERVICE_URL}/api/servers"
        logger.info(f"Запрашиваем список серверов с: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при запросе к API: {response.status_code}, {response.text}")
            return []
            
        servers = response.json().get("servers", [])
        logger.info(f"Получено {len(servers)} серверов")
        return servers
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для получения серверов: {str(e)}")
    
    return []

def get_wireguard_status():
    """Получает статус WireGuard и информацию о пирах."""
    try:
        # Получаем данные из интерфейса WireGuard
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
    """Подсчитывает количество активных подключений на основе последнего handshake."""
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

def update_server_metrics(server_id, active_connections):
    """
    Обновляет метрики сервера в базе данных.
    
    Args:
        server_id (str): ID сервера
        active_connections (int): Количество активных подключений
    """
    try:
        logger.info(f"Обновление метрик для сервера {server_id}: {active_connections} активных подключений")
        
        # Подготавливаем данные для отправки в API
        metrics_data = {
            "server_id": server_id,
            "peers_count": active_connections,
            "is_available": True,
            "success": True,
            "response_time": 0.1  # Заглушка для времени ответа
        }
        
        # Отправляем данные в API базы данных
        url = f"{DATABASE_SERVICE_URL}/api/server_metrics/add"
        logger.debug(f"Отправка метрик на URL: {url}, данные: {metrics_data}")
        
        response = requests.post(url, json=metrics_data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Метрики успешно обновлены для сервера {server_id}")
            return True
        else:
            logger.error(f"Ошибка при обновлении метрик: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении метрик сервера {server_id}: {str(e)}")
        return False

def main():
    """Основная функция для сбора и обновления метрик."""
    logger.info("Запуск сервиса сбора метрик")
    
    # Ждем, пока другие сервисы запустятся
    startup_delay = int(os.getenv('STARTUP_DELAY', 30))
    logger.info(f"Ожидание {startup_delay} секунд для запуска других сервисов...")
    time.sleep(startup_delay)
    
    while True:
        try:
            # Получаем список серверов
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
            
            # Обновляем метрики для каждого сервера
            for server in servers:
                # Проверяем, что это наш сервер (по публичному ключу)
                server_public_key = server.get("public_key")
                if server_public_key == wg_status.get("interface", {}).get("public_key"):
                    server_id = server.get("id")
                    logger.info(f"Найден наш сервер: {server_id}")
                    
                    # Обновляем метрики сервера
                    update_server_metrics(server_id, active_connections)
                    break
            
            # Ждем до следующего обновления
            logger.info(f"Ожидание {COLLECTION_INTERVAL} секунд до следующего обновления...")
            time.sleep(COLLECTION_INTERVAL)
            
        except Exception as e:
            logger.error(f"Произошла ошибка в основном цикле: {str(e)}")
            logger.exception("Подробный стек вызовов:")
            time.sleep(60)  # Ждем минуту перед следующей попыткой

if __name__ == "__main__":
    main()