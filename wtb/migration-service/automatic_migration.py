#!/usr/bin/env python3
import os
import time
import logging
import requests
import subprocess
import json
import socket
import statistics
from datetime import datetime, timedelta
import threading

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto-migration")

# Параметры подключения к API с динамическим определением хостов
def get_service_url(service_name, default_port, env_var_name):
    """Определяет URL сервиса с возможностью динамического определения хоста."""
    # Сначала проверяем переменную окружения
    env_url = os.getenv(env_var_name)
    if env_url:
        return env_url
    
    # Пытаемся получить IP по имени хоста через DNS
    try:
        import socket
        ip_address = socket.gethostbyname(service_name)
        return f"http://{ip_address}:{default_port}"
    except Exception as e:
        logger.warning(f"Не удалось определить IP для {service_name}: {str(e)}")
    
    # Если DNS не работает, используем имя хоста Docker
    return f"http://{service_name}:{default_port}"

# Динамическое определение URL сервисов
DATABASE_SERVICE_URL = get_service_url("database-service", 5002, 'DATABASE_SERVICE_URL')
WIREGUARD_SERVICE_URL = get_service_url("wireguard-service", 5001, 'WIREGUARD_SERVICE_URL')

logger.info(f"Используем DATABASE_SERVICE_URL: {DATABASE_SERVICE_URL}")
logger.info(f"Используем WIREGUARD_SERVICE_URL: {WIREGUARD_SERVICE_URL}")

# Другие параметры
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # Интервал проверки серверов в секундах (5 минут)
MIGRATION_THRESHOLD = int(os.getenv('MIGRATION_THRESHOLD', 3))  # Количество последовательных ошибок до миграции
PING_COUNT = int(os.getenv('PING_COUNT', 5))  # Количество пингов для проверки доступности
PING_TIMEOUT = int(os.getenv('PING_TIMEOUT', 3))  # Таймаут пинга в секундах
PACKET_LOSS_THRESHOLD = float(os.getenv('PACKET_LOSS_THRESHOLD', 50.0))  # Порог потери пакетов для миграции
LATENCY_THRESHOLD = float(os.getenv('LATENCY_THRESHOLD', 300.0))  # Порог задержки для миграции (мс)

# Глобальный словарь для отслеживания состояния серверов
server_status = {}

def check_server_availability(server):
    """Проверяет доступность сервера через ping."""
    server_id = server.get("id")
    endpoint = server.get("endpoint")
    port = server.get("port")
    
    if not endpoint:
        logger.warning(f"Ошибка: для сервера {server_id} не указан endpoint")
        return False, None
    
    logger.info(f"Проверка доступности сервера {server_id} ({endpoint})")
    
    # Проверка доступности через ping
    try:
        ping_command = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), endpoint]
        ping_result = subprocess.run(
            ping_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=PING_TIMEOUT * (PING_COUNT + 1)  # Добавляем дополнительное время
        )
        
        # Получаем строки с временем и анализируем результаты
        times = []
        packet_loss = 100.0  # По умолчанию считаем, что все пакеты потеряны
        
        if ping_result.returncode == 0:
            ping_lines = ping_result.stdout.split('\n')
            
            # Извлекаем времена отклика
            for line in ping_lines:
                if "time=" in line:
                    time_part = line.split("time=")[1].split(" ")[0]
                    try:
                        times.append(float(time_part))
                    except ValueError:
                        pass
            
            # Извлекаем процент потери пакетов
            for line in ping_lines:
                if "packet loss" in line:
                    try:
                        packet_loss = float(line.split("%")[0].split(" ")[-1])
                    except ValueError:
                        pass
        
        # Рассчитываем метрики
        available = packet_loss < PACKET_LOSS_THRESHOLD
        avg_latency = statistics.mean(times) if times else 999
        
        # Проверяем если задержка превышает порог
        if avg_latency > LATENCY_THRESHOLD:
            available = False
        
        metrics = {
            "available": available,
            "packet_loss": packet_loss,
            "latency": avg_latency if times else None,
            "checked_at": datetime.now().isoformat()
        }
        
        logger.info(f"Сервер {server_id} доступен: {available}, "
                   f"потеря пакетов: {packet_loss}%, "
                   f"задержка: {avg_latency if times else 'N/A'} мс")
        
        return available, metrics
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности сервера {server_id}: {str(e)}")
        return False, None

def get_all_servers():
    """Получает список всех активных серверов из базы данных."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/all", timeout=10)
        
        if response.status_code == 200:
            all_servers = response.json().get("servers", [])
            # Фильтруем только активные серверы
            active_servers = [s for s in all_servers if s.get("status") == "active"]
            logger.info(f"Получено {len(active_servers)} активных серверов из {len(all_servers)} общих")
            return active_servers
        else:
            logger.error(f"Ошибка при получении списка серверов: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для получения серверов: {str(e)}")
        return []

def get_active_connections(server_id):
    """Получает список активных подключений к серверу."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/connections", timeout=10)
        
        if response.status_code == 200:
            connections = response.json().get("connections", [])
            logger.info(f"Получено {len(connections)} активных подключений к серверу {server_id}")
            return connections
        else:
            logger.error(f"Ошибка при получении списка подключений: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для получения подключений: {str(e)}")
        return []

def find_optimal_server(user_id, current_geo_id):
    """Находит оптимальный сервер для миграции пользователя."""
    try:
        # Запрашиваем оптимальный сервер через API
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/servers/select_optimal",
            json={"user_id": user_id, "geolocation_id": current_geo_id},
            timeout=15
        )
        
        if response.status_code == 200:
            server = response.json().get("server")
            if server:
                logger.info(f"Найден оптимальный сервер {server.get('id')} для пользователя {user_id}")
                return server
        
        # Если API не вернул оптимальный сервер, выполняем ручной поиск
        all_servers = get_all_servers()
        available_servers = []
        
        # Фильтруем серверы той же геолокации
        same_geo_servers = [s for s in all_servers if s.get("geolocation_id") == current_geo_id]
        
        # Проверяем доступность каждого сервера
        for server in same_geo_servers:
            server_id = server.get("id")
            
            # Пропускаем проверку если статус уже известен
            if server_id in server_status and server_status[server_id].get("consecutive_failures", 0) == 0:
                available_servers.append(server)
                continue
            
            available, _ = check_server_availability(server)
            if available:
                available_servers.append(server)
        
        if available_servers:
            # Сортируем по нагрузке и рейтингу
            available_servers.sort(key=lambda s: (s.get("load_factor", 100), -s.get("metrics_rating", 0)))
            best_server = available_servers[0]
            logger.info(f"Выбран сервер {best_server.get('id')} для миграции пользователя {user_id}")
            return best_server
        
        # Если нет доступных серверов в этой геолокации, ищем в других
        all_available_servers = [s for s in all_servers if s.get("status") == "active"]
        if all_available_servers:
            # Сортируем по рейтингу метрик
            all_available_servers.sort(key=lambda s: -s.get("metrics_rating", 0))
            fallback_server = all_available_servers[0]
            logger.info(f"Выбран запасной сервер {fallback_server.get('id')} для миграции пользователя {user_id}")
            return fallback_server
        
        logger.error(f"Не удалось найти доступный сервер для миграции пользователя {user_id}")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при поиске оптимального сервера: {str(e)}")
        return None

def migrate_user(user_id, from_server_id, to_server_id, reason="server_down"):
    """Выполняет миграцию пользователя с одного сервера на другой."""
    try:
        logger.info(f"Миграция пользователя {user_id} с сервера {from_server_id} на сервер {to_server_id}. Причина: {reason}")
        
        # Запрашиваем данные о сервере назначения
        new_server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{to_server_id}", timeout=10)
        if new_server_response.status_code != 200:
            logger.error(f"Не удалось получить данные сервера {to_server_id}")
            return False
        
        new_server = new_server_response.json()
        geolocation_id = new_server.get("geolocation_id")
        
        # Выполняем миграцию через API изменения геолокации
        migration_data = {
            "user_id": user_id,
            "geolocation_id": geolocation_id,
            "server_id": to_server_id,
            "migration_reason": reason
        }
        
        migration_response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/configs/change_geolocation",
            json=migration_data,
            timeout=20
        )
        
        if migration_response.status_code == 200:
            # Регистрируем миграцию в журнале
            log_migration_data = {
                "user_id": user_id,
                "from_server_id": from_server_id,
                "to_server_id": to_server_id,
                "migration_reason": reason
            }
            
            try:
                requests.post(
                    f"{DATABASE_SERVICE_URL}/api/server_migrations/log",
                    json=log_migration_data,
                    timeout=10
                )
            except Exception as e:
                logger.warning(f"Не удалось зарегистрировать миграцию: {str(e)}")
            
            logger.info(f"Миграция пользователя {user_id} выполнена успешно")
            return True
        else:
            logger.error(f"Ошибка при миграции пользователя {user_id}: {migration_response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при миграции пользователя {user_id}: {str(e)}")
        return False

def check_and_migrate():
    """Проверяет доступность серверов и мигрирует пользователей при необходимости."""
    logger.info("Запуск проверки доступности серверов и миграции")
    
    # Получаем список всех серверов
    servers = get_all_servers()
    if not servers:
        logger.warning("Не удалось получить список серверов, пропускаем проверку")
        return
    
    # Проверяем каждый сервер
    for server in servers:
        server_id = server.get("id")
        
        # Инициализируем статус сервера, если это первая проверка
        if server_id not in server_status:
            server_status[server_id] = {
                "consecutive_failures": 0,
                "last_check": None,
                "metrics": None
            }
        
        # Проверяем доступность сервера
        available, metrics = check_server_availability(server)
        
        # Обновляем метрики и статус
        server_status[server_id]["last_check"] = datetime.now()
        server_status[server_id]["metrics"] = metrics
        
        if not available:
            # Увеличиваем счетчик последовательных сбоев
            server_status[server_id]["consecutive_failures"] += 1
            failures = server_status[server_id]["consecutive_failures"]
            
            logger.warning(f"Сервер {server_id} недоступен (сбой #{failures})")
            
            # Если превышен порог сбоев, выполняем миграцию пользователей
            if failures >= MIGRATION_THRESHOLD:
                logger.warning(f"Запуск миграции пользователей с сервера {server_id} (превышен порог сбоев)")
                
                # Получаем список активных подключений
                active_connections = get_active_connections(server_id)
                
                # Если нет активных подключений, обновляем статус сервера в БД
                if not active_connections:
                    try:
                        requests.post(
                            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/status",
                            json={"status": "inactive"},
                            timeout=10
                        )
                        logger.info(f"Статус сервера {server_id} изменен на 'inactive'")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении статуса сервера {server_id}: {str(e)}")
                
                # Мигрируем каждого пользователя
                for connection in active_connections:
                    user_id = connection.get("user_id")
                    geo_id = server.get("geolocation_id")
                    
                    # Находим оптимальный сервер для миграции
                    new_server = find_optimal_server(user_id, geo_id)
                    
                    if new_server and new_server.get("id") != server_id:
                        # Выполняем миграцию
                        migrate_user(user_id, server_id, new_server.get("id"))
                    else:
                        logger.warning(f"Не удалось найти подходящий сервер для миграции пользователя {user_id}")
                
                # После миграции всех пользователей, сбрасываем счетчик сбоев
                # чтобы не выполнять миграцию слишком часто
                server_status[server_id]["consecutive_failures"] = 0
        else:
            # Если сервер доступен, сбрасываем счетчик сбоев
            if server_status[server_id]["consecutive_failures"] > 0:
                logger.info(f"Сервер {server_id} снова доступен, сбрасываем счетчик сбоев")
                server_status[server_id]["consecutive_failures"] = 0
            
            # Обновляем метрики сервера в БД
            try:
                if metrics:
                    requests.post(
                        f"{DATABASE_SERVICE_URL}/api/servers/metrics/add",
                        json={
                            "server_id": server_id, 
                            "latency": metrics.get("latency"),
                            "packet_loss": metrics.get("packet_loss")
                        },
                        timeout=10
                    )
            except Exception as e:
                logger.warning(f"Не удалось обновить метрики сервера {server_id}: {str(e)}")

def update_server_status_in_db():
    """Обновляет статус серверов в базе данных на основе проверок."""
    logger.info("Обновление статуса серверов в базе данных")
    
    # Создаем список серверов для обновления
    servers_to_update = []
    
    for server_id, status in server_status.items():
        if status["consecutive_failures"] >= MIGRATION_THRESHOLD:
            servers_to_update.append({
                "id": server_id,
                "status": "inactive",
                "last_check": datetime.now().isoformat()
            })
        elif status["consecutive_failures"] == 0 and status["metrics"] and status["metrics"]["available"]:
            servers_to_update.append({
                "id": server_id,
                "status": "active",
                "last_check": datetime.now().isoformat()
            })
    
    # Обновляем статус в БД
    if servers_to_update:
        try:
            requests.post(
                f"{DATABASE_SERVICE_URL}/api/servers/update_status_batch",
                json={"servers": servers_to_update},
                timeout=15
            )
            logger.info(f"Обновлен статус для {len(servers_to_update)} серверов")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса серверов: {str(e)}")
            
def scheduled_check():
    """Выполняет периодическую проверку и миграцию по расписанию."""
    while True:
        try:
            check_and_migrate()
            # Обновляем статус в БД
            update_server_status_in_db()
        except Exception as e:
            logger.error(f"Ошибка в процессе проверки и миграции: {str(e)}")
            
        # Ждем до следующей проверки
        logger.info(f"Следующая проверка через {CHECK_INTERVAL} секунд")
        time.sleep(CHECK_INTERVAL)

def start_migration_service():
    """Запускает сервис миграции в отдельном потоке."""
    thread = threading.Thread(target=scheduled_check, daemon=True)
    thread.start()
    logger.info("Сервис автоматической миграции запущен")
    return thread

if __name__ == "__main__":
    logger.info("Запуск сервиса автоматической миграции")
    
    # Ждем, пока другие сервисы станут доступны
    startup_delay = int(os.getenv('STARTUP_DELAY', 30))
    logger.info(f"Ожидание {startup_delay} секунд для запуска других сервисов...")
    time.sleep(startup_delay)
    
    # Запускаем сервис миграции
    migration_thread = start_migration_service()
    
    try:
        # Бесконечный цикл для сохранения потока главного процесса
        while True:
            time.sleep(60)
            
            # Проверяем работоспособность потока миграции
            if not migration_thread.is_alive():
                logger.error("Поток миграции завершен неожиданно, перезапускаем")
                migration_thread = start_migration_service()
                
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения, останавливаем сервис")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")