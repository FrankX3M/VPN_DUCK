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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics-collector")

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
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', 900))  # Интервал сбора в секундах (15 минут по умолчанию)
PING_COUNT = int(os.getenv('PING_COUNT', 10))  # Количество пингов для измерения
MAINTENANCE_INTERVAL = int(os.getenv('MAINTENANCE_INTERVAL', 3600))  # Интервал обслуживания в секундах (1 час)
GEO_SERVICE_URL = os.getenv('GEO_SERVICE_URL', 'https://ipapi.co')

def get_server_ip():
    """Получает IP-адрес сервера."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Подключаемся к несуществующему IP (не делает реального подключения)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"Ошибка при определении IP сервера: {str(e)}")
        # Используем localhost в случае ошибки
        return "127.0.0.1"

def get_server_location(ip_address):
    """Получает географические координаты сервера по IP."""
    try:
        response = requests.get(f"{GEO_SERVICE_URL}/{ip_address}/json/", timeout=10)
        
        if response.status_code == 200:
            location_data = response.json()
            return {
                'latitude': location_data.get('latitude'),
                'longitude': location_data.get('longitude'),
                'city': location_data.get('city'),
                'country': location_data.get('country_name')
            }
    except Exception as e:
        logger.error(f"Ошибка при определении геолокации: {str(e)}")
    
    return None

def get_servers():
    """Получает список всех активных серверов из базы данных."""
    try:
        response = make_api_request('get', f"{DATABASE_SERVICE_URL}/servers/all", timeout=10)
        return response.json().get("servers", [])
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для получения серверов: {str(e)}")
    
    return []

def measure_server_metrics(server):
    """Измеряет метрики сервера."""
    server_id = server.get("id")
    endpoint = server.get("endpoint")
    port = server.get("port")
    
    if not endpoint:
        logger.warning(f"Ошибка: для сервера {server_id} не указан endpoint")
        return None
    
    logger.info(f"Измерение метрик для сервера {server_id} ({endpoint})")
    
    metrics = {
        "server_id": server_id,
        "latency": None,
        "jitter": None,
        "packet_loss": None,
        "bandwidth": None,
        "measured_at": datetime.now().isoformat()
    }
    
    # Измерение задержки и джиттера с помощью ping
    try:
        ping_command = ["ping", "-c", str(PING_COUNT), endpoint]
        ping_result = subprocess.run(
            ping_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if ping_result.returncode == 0:
            # Получаем строки с временем
            ping_lines = ping_result.stdout.split('\n')
            times = []
            
            for line in ping_lines:
                if "time=" in line:
                    time_part = line.split("time=")[1].split(" ")[0]
                    try:
                        times.append(float(time_part))
                    except ValueError:
                        pass
            
            if times:
                # Рассчитываем среднее время и джиттер
                metrics["latency"] = statistics.mean(times)
                metrics["jitter"] = statistics.stdev(times) if len(times) > 1 else 0
            
            # Извлекаем процент потери пакетов
            for line in ping_lines:
                if "packet loss" in line:
                    try:
                        packet_loss = float(line.split("%")[0].split(" ")[-1])
                        metrics["packet_loss"] = packet_loss
                    except ValueError:
                        pass
        else:
            logger.warning(f"Ошибка ping для сервера {server_id} ({endpoint}): {ping_result.stderr}")
            metrics["packet_loss"] = 100  # Если ping не прошел, считаем 100% потерю пакетов
    except Exception as e:
        logger.error(f"Ошибка при измерении пинга для сервера {server_id}: {str(e)}")
    
    # Измерение пропускной способности (симуляция)
    # В реальном случае здесь может быть использован iperf3 или другой инструмент
    try:
        # На данный момент используем случайное значение
        metrics["bandwidth"] = 100.0  # Mbps
    except Exception as e:
        logger.error(f"Ошибка при измерении скорости для сервера {server_id}: {str(e)}")
    
    return metrics

def update_server_metrics(metrics):
    """Отправляет собранные метрики в базу данных."""
    try:
        response = make_api_request('post', f"{DATABASE_SERVICE_URL}/servers/metrics/add", json=metrics)
        logger.info(f"Метрики для сервера {metrics['server_id']} успешно обновлены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке метрик в API: {str(e)}")
    
    return False

def analyze_servers_metrics():
    """Анализирует метрики серверов и обновляет их рейтинги."""
    try:
        response = make_api_request('post', f"{DATABASE_SERVICE_URL}/servers/metrics/analyze")
        result = response.json()
        updated_servers = result.get("updated_servers", 0)
        logger.info(f"Анализ метрик серверов выполнен успешно, обновлено {updated_servers} серверов")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для анализа метрик: {str(e)}")
    
    return False

def migrate_users_from_inactive_servers():
    """Мигрирует пользователей с неактивных серверов на активные."""
    try:
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/configs/migrate_users",
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            migrated = result.get("migrated", 0)
            logger.info(f"Миграция пользователей выполнена успешно, перемещено {migrated} пользователей")
            return True
        elif response.status_code == 404:
            # Нет пользователей для миграции - это нормально
            logger.info("Нет пользователей для миграции")
            return True
        else:
            logger.error(f"Ошибка при миграции пользователей: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для миграции пользователей: {str(e)}")
    
    return False

def rebalance_server_load():
    """Перебалансирует нагрузку серверов."""
    try:
        # Получаем список геолокаций
        response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations/available", timeout=5)
        
        if response.status_code == 200:
            geolocations = response.json().get("geolocations", [])
            
            for geolocation in geolocations:
                geo_id = geolocation.get("id")
                
                # Запускаем перебалансировку для каждой доступной геолокации
                rebalance_response = requests.post(
                    f"{DATABASE_SERVICE_URL}/servers/rebalance",
                    json={"geolocation_id": geo_id, "threshold": 70},
                    timeout=10
                )
                
                if rebalance_response.status_code == 200:
                    result = rebalance_response.json()
                    migrated_users = result.get("migrated_users", 0)
                    logger.info(f"Перебалансировка для геолокации {geo_id} выполнена успешно, перемещено {migrated_users} пользователей")
                else:
                    logger.error(f"Ошибка при перебалансировке для геолокации {geo_id}: {rebalance_response.status_code}, {rebalance_response.text}")
            
            return True
        else:
            logger.error(f"Ошибка при получении списка геолокаций: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для перебалансировки: {str(e)}")
    
    return False

def check_geolocations_availability():
    """Проверяет доступность геолокаций и обновляет их статус."""
    try:
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/geolocations/check",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            updated_geolocations = result.get("updated_geolocations", 0)
            logger.info(f"Проверка доступности геолокаций выполнена успешно, обновлено {updated_geolocations} геолокаций")
            return True
        else:
            logger.error(f"Ошибка при проверке доступности геолокаций: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для проверки геолокаций: {str(e)}")
    
    return False

def cleanup_expired_configs():
    """Очищает истекшие конфигурации."""
    try:
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/cleanup_expired",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            cleaned = result.get("cleaned", 0)
            logger.info(f"Очистка истекших конфигураций выполнена успешно, удалено {cleaned} конфигураций")
            return True
        else:
            logger.error(f"Ошибка при очистке истекших конфигураций: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе к API для очистки конфигураций: {str(e)}")
    
    return False

def register_own_server():
    """Регистрирует собственный сервер в базе данных, если его там еще нет."""
    try:
        # Получаем IP сервера
        server_ip = get_server_ip()
        logger.info(f"Определен IP сервера: {server_ip}")
        
        # Получаем текущие серверы
        servers = get_servers()
        
        # Проверяем, есть ли уже наш сервер в списке
        for server in servers:
            if server.get("endpoint") == server_ip:
                logger.info(f"Сервер с IP {server_ip} уже зарегистрирован в базе данных")
                return True
        
        # Получаем геолокацию сервера
        location = get_server_location(server_ip)
        
        # Если не удалось получить геолокацию, устанавливаем значения по умолчанию
        if not location or location.get('latitude') is None or location.get('longitude') is None:
            logger.warning("Не удалось определить геолокацию сервера, устанавливаем значения по умолчанию")
            location = {
                'latitude': 55.7558,  # Москва (или другие значения по умолчанию)
                'longitude': 37.6173,
                'city': 'Unknown City',
                'country': 'Unknown Country'
            }
        
        # Получаем список геолокаций
        try:
            response = make_api_request('get', f"{DATABASE_SERVICE_URL}/geolocations")
            geolocations = response.json().get("geolocations", [])
        except Exception as e:
            logger.error(f"Ошибка при получении списка геолокаций: {str(e)}")
            return False
        
        # Выбираем геолокацию на основе страны сервера
        geolocation_id = None
        for geo in geolocations:
            # Здесь можно расширить логику выбора геолокации
            if geo.get("code") == "ru" and location.get("country") == "Russia":
                geolocation_id = geo.get("id")
                break
            elif geo.get("code") == "eu" and location.get("country") in ["Germany", "France", "Netherlands", "Italy", "Spain"]:
                geolocation_id = geo.get("id")
                break
            elif geo.get("code") == "us" and location.get("country") in ["United States", "Canada"]:
                geolocation_id = geo.get("id")
                break
            elif geo.get("code") == "asia" and location.get("country") in ["China", "Japan", "Singapore", "India"]:
                geolocation_id = geo.get("id")
                break
        
        # Если не нашли подходящую геолокацию, используем первую в списке
        if not geolocation_id and geolocations:
            geolocation_id = geolocations[0].get("id")
        
        if not geolocation_id:
            logger.error("Не удалось определить подходящую геолокацию для сервера")
            return False
        
        # Получаем данные WireGuard
        try:
            wg_response = make_api_request('get', f"{WIREGUARD_SERVICE_URL}/status")
            wg_status = wg_response.json()
            
            if wg_status.get("status") != "running":
                logger.error("WireGuard не запущен")
                return False
            
            interface = wg_status.get("interface", {})
            public_key = interface.get("public key")
            listen_port = interface.get("listening port")
            
            if not public_key:
                logger.error("Не удалось получить публичный ключ WireGuard")
                return False
        except Exception as e:
            logger.error(f"Ошибка при получении статуса WireGuard: {str(e)}")
            return False
        
        # Создаем запрос на регистрацию сервера
        server_data = {
            "geolocation_id": geolocation_id,
            "endpoint": server_ip,
            "port": int(listen_port) if listen_port else 51820,
            "public_key": public_key,
            "private_key": "private_key_placeholder",  # В реальном приложении можно не отправлять приватный ключ
            "address": "10.0.0.1/24",
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "city": location.get("city"),
            "country": location.get("country")
        }
        
        # Отправляем запрос на регистрацию сервера
        try:
            register_response = make_api_request(
                'post', 
                f"{DATABASE_SERVICE_URL}/servers/register",
                json=server_data,
                max_retries=3
            )
            
            result = register_response.json()
            server_id = result.get("server_id")
            logger.info(f"Сервер успешно зарегистрирован в базе данных с IP {server_ip}, ID: {server_id}")
            return True
        except Exception as e:
            # Проверяем, не возникла ли ошибка из-за того, что сервер уже существует
            if "409" in str(e) or "уже существует" in str(e):
                logger.info(f"Сервер с IP {server_ip} уже существует в базе данных")
                return True
            logger.error(f"Ошибка при регистрации сервера: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при регистрации собственного сервера: {str(e)}")
        return False

def perform_maintenance():
    """Выполняет обслуживание системы."""
    logger.info("Начало процедуры обслуживания")
    
    # Анализируем метрики серверов
    analyze_servers_metrics()
    
    # Проверяем доступность геолокаций
    check_geolocations_availability()
    
    # Мигрируем пользователей с неактивных серверов
    migrate_users_from_inactive_servers()
    
    # Перебалансируем нагрузку серверов
    rebalance_server_load()
    
    # Очищаем истекшие конфигурации
    cleanup_expired_configs()
    
    logger.info("Обслуживание системы завершено")

def make_api_request(method, url, json=None, timeout=10, max_retries=3, retry_delay=5):
    """Выполняет запрос к API с повторными попытками."""
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            if method.lower() == 'get':
                response = requests.get(url, timeout=timeout)
            elif method.lower() == 'post':
                response = requests.post(url, json=json, timeout=timeout)
            elif method.lower() == 'delete':
                response = requests.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Неподдерживаемый метод HTTP: {method}")
            
            # Проверяем код ответа
            if response.status_code >= 200 and response.status_code < 300:
                return response
            else:
                error_msg = f"API вернул ошибку {response.status_code}: {response.text}"
                logger.warning(error_msg)
                last_error = Exception(error_msg)
        except requests.RequestException as e:
            logger.warning(f"Ошибка запроса к {url} (попытка {retry_count+1}/{max_retries}): {str(e)}")
            last_error = e
        
        # Увеличиваем задержку с каждой попыткой (экспоненциальная выдержка)
        actual_delay = retry_delay * (2 ** retry_count)
        logger.info(f"Повторная попытка через {actual_delay} секунд...")
        time.sleep(actual_delay)
        retry_count += 1
    
    # Если дошли сюда, значит все попытки неудачны
    raise last_error or Exception(f"Не удалось выполнить запрос к {url} после {max_retries} попыток")

def main():
    """Основная функция сбора метрик."""
    logger.info("Запуск сервиса сбора метрик серверов")
    
    # Ждем, пока другие сервисы станут доступны
    startup_delay = int(os.getenv('STARTUP_DELAY', 30))
    logger.info(f"Ожидание {startup_delay} секунд для запуска других сервисов...")
    time.sleep(startup_delay)
    
    # Проверяем и регистрируем собственный сервер при первом запуске
    try:
        register_own_server()
    except Exception as e:
        logger.error(f"Ошибка при регистрации сервера: {str(e)}")
        logger.info("Продолжаем работу без регистрации сервера")
    
    last_maintenance_time = time.time()
    
    while True:
        try:
            # Получаем список серверов
            servers = get_servers()
            
            if not servers:
                logger.warning("Не удалось получить список серверов или список пуст")
            else:
                logger.info(f"Получено {len(servers)} серверов для мониторинга")
                
                # Измеряем метрики для каждого сервера
                for server in servers:
                    try:
                        metrics = measure_server_metrics(server)
                        if metrics:
                            update_server_metrics(metrics)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке сервера {server.get('id')}: {str(e)}")
            
            # Проверяем, нужно ли выполнить обслуживание
            current_time = time.time()
            if current_time - last_maintenance_time >= MAINTENANCE_INTERVAL:
                try:
                    perform_maintenance()
                    last_maintenance_time = current_time
                except Exception as e:
                    logger.error(f"Ошибка при выполнении обслуживания: {str(e)}")
            
            # Ждем до следующего цикла сбора метрик
            logger.info(f"Сбор метрик завершен, следующий запуск через {COLLECTION_INTERVAL} секунд")
            time.sleep(COLLECTION_INTERVAL)
        
        except Exception as e:
            logger.error(f"Неожиданная ошибка в основном цикле: {str(e)}")
            # Ждем немного перед повторной попыткой
            time.sleep(60)

if __name__ == "__main__":
    main()