from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import requests
import json
import os
import logging
from datetime import datetime, timedelta
import time
from functools import wraps
#
app = Flask(__name__)
app.secret_key = os.getenv('ADMIN_SECRET_KEY', 'development_secret_key')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры подключения к API с динамическим определением хостов
# def get_service_url(service_name, default_port, env_var_name):
#     """Определяет URL сервиса с возможностью динамического определения хоста."""
#     # Сначала проверяем переменную окружения
#     env_url = os.getenv(env_var_name)
#     if env_url:
#         return env_url
    
#     # Пытаемся получить IP по имени хоста через DNS
#     try:
#         import socket
#         ip_address = socket.gethostbyname(service_name)
#         return f"http://{ip_address}:{default_port}"
#     except Exception as e:
#         logger.warning(f"Не удалось определить IP для {service_name}: {str(e)}")
    
#     # Если DNS не работает, используем имя хоста Docker
#     return f"http://{service_name}:{default_port}"
# def get_service_url(service_name, default_port, env_var_name):
#     """Определяет URL сервиса с приоритетом на DNS-имя сервиса в Docker сети."""
#     # Сначала проверяем переменную окружения
#     env_url = os.getenv(env_var_name)
#     if env_url:
#         logger.info(f"Используем URL из переменной окружения для {service_name}: {env_url}")
#         return env_url
    
#     # Используем имя сервиса как DNS-имя в Docker сети
#     service_url = f"http://{service_name}:{default_port}"
#     logger.info(f"Используем URL на основе имени сервиса для {service_name}: {service_url}")
#     return service_url
# def get_service_url(service_name, default_port, env_var_name):
#     """Определяет URL сервиса с приоритетом на DNS-имя сервиса в Docker сети."""
#     # Сначала проверяем переменную окружения
#     env_url = os.getenv(env_var_name)
#     if env_url:
#         print(f"Using env URL for {service_name}: {env_url}")
#         return env_url
    
#     # Используем имя сервиса как DNS-имя в Docker сети
#     service_url = f"http://{service_name}:{default_port}"
#     print(f"Using service name URL for {service_name}: {service_url}")
#     return service_url
def get_service_url(service_name, default_port, env_var_name):
    """Определяет URL сервиса с приоритетом на DNS-имя сервиса в Docker сети."""
    # Сначала проверяем переменную окружения
    env_url = os.getenv(env_var_name)
    if env_url:
        logger.info(f"Используем URL из переменной окружения для {service_name}: {env_url}")
        return env_url
    
    # Используем имя сервиса как DNS-имя в Docker сети
    service_url = f"http://{service_name}:{default_port}"
    logger.info(f"Используем URL на основе имени сервиса для {service_name}: {service_url}")
    return service_url
    
# Динамическое определение URL сервисов
DATABASE_SERVICE_URL = get_service_url("database-service", 5002, 'DATABASE_SERVICE_URL')
# WIREGUARD_SERVICE_URL = get_service_url("wireguard-service", 5001, 'WIREGUARD_SERVICE_URL')
WIREGUARD_SERVICE_URL = get_service_url("wireguard-proxy", 5001, 'WIREGUARD_PROXY_URL')

logger.info(f"Используем DATABASE_SERVICE_URL: {DATABASE_SERVICE_URL}")
logger.info(f"Используем WIREGUARD_SERVICE_URL: {WIREGUARD_SERVICE_URL}")

# Параметры доступа администратора
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password')

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Необходимо войти для доступа к этой странице', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Главная страница панели управления."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в панель управления."""
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            error = 'Неверное имя пользователя или пароль'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Выход из панели управления."""
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Страница с панелью мониторинга."""
    return render_template('dashboard.html')

@app.route('/servers')
@login_required
def servers():
    """Страница управления серверами."""
    # return render_template('servers.html')
    return render_template('servers/index.html')

# @app.route('/api/servers', methods=['GET'])
# @login_required
# def api_get_servers():
#     """API для получения списка серверов."""
#     try:
#         response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/all", timeout=10)
        
#         if response.status_code == 200:
#             servers = response.json().get("servers", [])
#             return jsonify({"status": "success", "servers": servers})
#         else:
#             return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка серверов: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500


# @app.route('/api/servers', methods=['POST'])
# @login_required
# def api_add_server():
#     """API для добавления нового сервера."""
#     try:
#         data = request.json
#         logger.info(f"Получены данные для добавления сервера: {data}")
        
#         # Проверяем обязательные поля
#         required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
#         missing_fields = [field for field in required_fields if field not in data]
        
#         if missing_fields:
#             logger.error(f"Отсутствуют обязательные поля: {missing_fields}")
#             return jsonify({"status": "error", "message": f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"}), 400
        
#         # Проверка типов данных
#         try:
#             # Преобразуем строковые представления чисел в числа
#             if isinstance(data['port'], str):
#                 data['port'] = int(data['port'])
#             if isinstance(data['geolocation_id'], str):
#                 data['geolocation_id'] = int(data['geolocation_id'])
#         except ValueError as e:
#             logger.error(f"Ошибка преобразования типов данных: {str(e)}")
#             return jsonify({"status": "error", "message": f"Ошибка в данных: {str(e)}"}), 400
        
#         # Если API ключ не указан, генерируем его автоматически
#         if 'api_key' not in data or not data['api_key']:
#             import secrets
#             data['api_key'] = secrets.token_hex(16)
#             logger.info(f"Автоматически сгенерирован API ключ для сервера")
        
#         # Добавляем дополнительные поля для database-service
#         server_data = {
#             "name": data.get('name', f"Server {data['endpoint']}"),
#             "location": data.get('location', f"{data['endpoint']}:{data['port']}"),
#             "api_url": f"http://{data['endpoint']}:{data['port']}/api",
#             "geolocation_id": data['geolocation_id'],
#             "endpoint": data['endpoint'],
#             "port": data['port'],
#             "public_key": data['public_key'],
#             "address": data['address'],
#             "auth_type": data.get('auth_type', 'api_key'),
#             "api_key": data['api_key'],
#             "status": "active"  # Устанавливаем активный статус по умолчанию
#         }
        
#         logger.info(f"Подготовленные данные для добавления сервера: {server_data}")
        
#         # Отправляем запрос на добавление сервера
#         response = requests.post(
#             f"{DATABASE_SERVICE_URL}/api/servers/add",
#             json=server_data,
#             timeout=15
#         )
        
#         logger.info(f"Статус ответа от DATABASE_SERVICE: {response.status_code}")
#         logger.info(f"Тело ответа: {response.text}")
        
#         if response.status_code in [200, 201]:
#             try:
#                 result = response.json()
#                 logger.info(f"Сервер успешно добавлен: {result}")
#                 return jsonify({
#                     "status": "success", 
#                     "server_id": result.get("server_id"),
#                     "api_key": server_data['api_key']
#                 }), 201
#             except ValueError as e:
#                 logger.error(f"Ошибка при разборе JSON-ответа: {str(e)}")
#                 return jsonify({
#                     "status": "success", 
#                     "message": "Сервер добавлен, но произошла ошибка при разборе ответа"
#                 }), 201
#         else:
#             error_message = f"Ошибка при регистрации сервера: HTTP {response.status_code}"
#             try:
#                 error_data = response.json()
#                 if isinstance(error_data, dict) and "error" in error_data:
#                     error_message = error_data.get("error")
#             except:
#                 if response.text:
#                     error_message += f" - {response.text[:100]}"
            
#             logger.error(error_message)
#             return jsonify({"status": "error", "message": error_message}), response.status_code
#     except Exception as e:
#         logger.exception(f"Непредвиденная ошибка при добавлении сервера: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500
        
# @app.route('/api/servers/<int:server_id>/delete', methods=['POST'])
# @login_required
# def api_delete_server(server_id):
#     """API для полного удаления сервера."""
#     try:
#         # Получаем информацию о сервере, чтобы узнать публичный ключ
#         logger.info(f"Запрос на удаление сервера ID: {server_id}")
#         server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        
#         if server_response.status_code != 200:
#             logger.error(f"Сервер с ID {server_id} не найден в базе данных")
#             return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
#         server_data = server_response.json()
#         public_key = server_data.get("public_key")
        
#         # Добавляем диагностику WireGuard сервиса
#         try:
#             test_url = f"{WIREGUARD_SERVICE_URL}/status"
#             logger.info(f"Проверка доступности WireGuard сервиса: {test_url}")
#             test_response = requests.get(test_url, timeout=5)
#             logger.info(f"WireGuard статус: {test_response.status_code}")
#         except Exception as e:
#             logger.warning(f"Невозможно подключиться к WireGuard сервису: {str(e)}")
        
#         # Удаляем сервер из WireGuard конфигурации (если есть public_key)
#        # Удаляем сервер из WireGuard конфигурации (если есть public_key)
#         if public_key:
#             logger.info(f"Удаление пира из WireGuard с ключом: {public_key}")
#             try:
#                 remove_url = f"{WIREGUARD_SERVICE_URL}/remove"
#                 logger.info(f"Вызов URL для удаления: {remove_url}")
#                 wg_response = requests.delete(remove_url, json={"public_key": public_key}, timeout=10)
                
#                 logger.info(f"Ответ WireGuard: {wg_response.status_code}, {wg_response.text}")
                
#                 if wg_response.status_code == 200:
#                     logger.info("Пир успешно удален из WireGuard")
#                 elif wg_response.status_code == 404:
#                     logger.warning(f"Пир с ключом {public_key} не найден в WireGuard (404), продолжаем удаление из БД")
#                 else:
#                     logger.warning(f"Ошибка при удалении пира из WireGuard: {wg_response.status_code}, {wg_response.text}")
#             except Exception as e:
#                 logger.warning(f"Ошибка при обращении к WireGuard-сервису: {str(e)}")
#                 logger.info("Продолжаем удаление из базы данных")
#         else:
#             logger.warning(f"Сервер с ID {server_id} не имеет публичного ключа, пропускаем удаление из WireGuard")
        
#         # Полностью удаляем сервер из базы данных
#         logger.info(f"Полное удаление сервера {server_id} из базы данных")
#         delete_response = requests.delete(
#             f"{DATABASE_SERVICE_URL}/api/servers/{server_id}",
#             timeout=10
#         )
        
#         if delete_response.status_code != 200:
#             logger.error(f"Ошибка при удалении сервера: {delete_response.status_code}, {delete_response.text}")
#             return jsonify({"status": "error", "message": "Ошибка при удалении сервера из базы данных"}), 500
        
#         logger.info(f"Сервер {server_id} успешно удален")
#         return jsonify({"status": "success", "message": "Сервер успешно удален"})
#     except Exception as e:
#         logger.error(f"Ошибка при удалении сервера: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500

# эндпоинты для работы с геолокациями

@app.route('/geolocations', methods=['GET'])
@login_required
def geolocations_page():  # Переименовано из geolocations
    """Страница управления геолокациями."""
    return render_template('geolocations.html')

# @app.route('/api/geolocations', methods=['POST'])
# @login_required
# def api_create_geolocation():  # Переименовано из api_add_geolocation
#     """API для добавления новой геолокации."""
#     try:
#         data = request.json
        
#         # Проверяем обязательные поля
#         required_fields = ['code', 'name']
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({"status": "error", "message": f"Поле {field} обязательно"}), 400
        
#         # Отправляем запрос на добавление геолокации
#         response = requests.post(
#             f"{DATABASE_SERVICE_URL}/api/geolocations",
#             json=data,
#             timeout=15
#         )
        
#         if response.status_code in [200, 201]:
#             result = response.json()
#             return jsonify({"status": "success", "geolocation_id": result.get("geolocation_id")}), 201
#         else:
#             # Проверяем, есть ли информация об ошибке в ответе
#             error_message = "Ошибка при создании геолокации"
#             try:
#                 error_data = response.json()
#                 if "error" in error_data:
#                     error_message = error_data.get("error")
#             except:
#                 pass
            
#             return jsonify({"status": "error", "message": error_message}), response.status_code
#     except Exception as e:
#         logger.error(f"Ошибка при добавлении геолокации: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/geolocations', methods=['POST'])
@login_required
def api_create_geolocation():
    try:
        data = request.json
        logger.info(f"Получены данные для добавления геолокации: {data}")
        
        # Проверка наличия данных
        if not data:
            logger.error("Получены пустые данные")
            return jsonify({"status": "error", "message": "Пустые данные запроса"}), 400
        
        # Проверяем обязательные поля
        required_fields = ['code', 'name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Отсутствуют обязательные поля: {missing_fields}. Полученные данные: {data}")
            return jsonify({"status": "error", "message": f"Отсутствуют поля: {', '.join(missing_fields)}"}), 400
        
        # Добавляем поле available, если оно отсутствует
        if 'available' not in data:
            data['available'] = True
        
        # Отправляем запрос на добавление геолокации
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/geolocations",
            json=data,
            timeout=15
        )
        
        logger.info(f"Статус ответа от DATABASE_SERVICE: {response.status_code}")
        logger.info(f"Тело ответа: {response.text}")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                return jsonify({"status": "success", "geolocation_id": result.get("geolocation_id")}), 201
            except ValueError as e:
                logger.error(f"Ошибка при разборе JSON-ответа: {str(e)}")
                return jsonify({
                    "status": "success", 
                    "message": "Геолокация добавлена, но произошла ошибка при разборе ответа"
                }), 201
        else:
            error_message = f"Ошибка при создании геолокации: HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                if response.text:
                    error_message += f" - {response.text[:100]}"
            
            logger.error(error_message)
            return jsonify({"status": "error", "message": error_message}), response.status_code
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при добавлении геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500




@app.route('/api/geolocations/<int:geo_id>', methods=['PUT'])
@login_required
def api_edit_geolocation(geo_id):  # Переименовано из api_update_geolocation
    """API для обновления данных геолокации."""
    try:
        data = request.json
        
        # Отправляем запрос на обновление геолокации
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            json=data,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({"status": "success", "geolocation_id": result.get("geolocation_id")}), 200
        else:
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при обновлении геолокации"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
    except Exception as e:
        logger.error(f"Ошибка при обновлении геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['DELETE'])
@login_required
def api_remove_geolocation(geo_id):  # Переименовано из api_delete_geolocation
    """API для удаления геолокации."""
    try:
        # Отправляем запрос на удаление геолокации
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            timeout=15
        )
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "Геолокация успешно удалена"}), 200
        else:
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при удалении геолокации"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
    except Exception as e:
        logger.error(f"Ошибка при удалении геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['GET'])
@login_required
def api_fetch_geolocation(geo_id):  # Переименовано из api_get_geolocation
    """API для получения детальной информации о геолокации."""
    try:
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            geolocation = response.json()
            return jsonify({"status": "success", "geolocation": geolocation})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при получении информации о геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/server_metrics/<int:server_id>', methods=['GET'])
@login_required
def api_get_server_metrics(server_id):
    """API для получения метрик сервера."""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/metrics?hours={hours}",
            timeout=15
        )
        
        if response.status_code == 200:
            metrics_data = response.json()
            return jsonify({"status": "success", "metrics": metrics_data})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при получении метрик сервера: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/metrics/analyze', methods=['POST'])
@login_required
def api_analyze_metrics():
    """API для запуска анализа метрик всех серверов."""
    try:
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/servers/metrics/analyze",
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({"status": "success", "updated_servers": result.get("updated_servers", 0)})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при анализе метрик: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/servers/rebalance', methods=['POST'])
@login_required
def api_rebalance_servers():
    """API для перебалансировки нагрузки серверов."""
    try:
        data = request.json
        geolocation_id = data.get('geolocation_id')
        threshold = data.get('threshold', 70)
        
        if not geolocation_id:
            return jsonify({"status": "error", "message": "Отсутствует обязательное поле geolocation_id"}), 400
        
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/servers/rebalance",
            json={"geolocation_id": geolocation_id, "threshold": threshold},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "status": "success", 
                "updated_servers": result.get("updated_servers", 0),
                "migrated_users": result.get("migrated_users", 0)
            })
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при перебалансировке серверов: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/servers/migrate_users', methods=['POST'])
@login_required
def api_migrate_users():
    """API для миграции пользователей с неактивных серверов."""
    try:
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/configs/migrate_users",
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({"status": "success", "migrated": result.get("migrated", 0)})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при миграции пользователей: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/dashboard/summary', methods=['GET'])
@login_required
def api_dashboard_summary():
    """API для получения сводной информации для дашборда."""
    try:
        # Получаем список серверов
        servers_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/all", timeout=10)
        
        if servers_response.status_code != 200:
            return jsonify({"status": "error", "message": "Ошибка при получении списка серверов"}), 500
        
        servers = servers_response.json().get("servers", [])
        
        # Получаем список геолокаций
        geolocations_response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations", timeout=10)
        
        if geolocations_response.status_code != 200:
            return jsonify({"status": "error", "message": "Ошибка при получении списка геолокаций"}), 500
        
        geolocations = geolocations_response.json().get("geolocations", [])
        
        # Получаем статус WireGuard
        try:
            wireguard_response = requests.get(f"{WIREGUARD_SERVICE_URL}/status", timeout=5)
            wireguard_status = "running" if wireguard_response.status_code == 200 else "unknown"
            if wireguard_response.status_code == 200:
                wireguard_data = wireguard_response.json()
                peers_count = len(wireguard_data.get("peers", []))
            else:
                peers_count = 0
        except:
            wireguard_status = "error"
            peers_count = 0
        
        # Формируем статистику
        active_servers = sum(1 for s in servers if s.get("status") == "active")
        total_servers = len(servers)
        
        active_geolocations = sum(1 for g in geolocations if g.get("available", False))
        total_geolocations = len(geolocations)
        
        # Вычисляем средние показатели серверов
        avg_latency = 0
        avg_packet_loss = 0
        servers_with_metrics = 0
        
        for server in servers:
            if server.get("avg_latency") is not None:
                avg_latency += server.get("avg_latency", 0)
                avg_packet_loss += server.get("avg_packet_loss", 0)
                servers_with_metrics += 1
        
        if servers_with_metrics > 0:
            avg_latency /= servers_with_metrics
            avg_packet_loss /= servers_with_metrics
        
        summary = {
            "active_servers": active_servers,
            "total_servers": total_servers,
            "active_geolocations": active_geolocations,
            "total_geolocations": total_geolocations,
            "wireguard_status": wireguard_status,
            "peers_count": peers_count,
            "avg_latency": round(avg_latency, 2),
            "avg_packet_loss": round(avg_packet_loss, 2)
        }
        
        return jsonify({"status": "success", "summary": summary})
    except Exception as e:
        logger.error(f"Ошибка при получении сводной информации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# редактирование серверов
# @app.route('/api/servers/<int:server_id>', methods=['PUT'])
# @login_required
# def api_update_server(server_id):
#     """API для обновления данных сервера."""
#     try:
#         data = request.json
#         logger.info(f"Получен запрос на обновление сервера {server_id} с данными: {data}")
        
#         # Формируем данные для запроса
#         update_data = {}
        
#         # Добавляем поля, которые разрешено обновлять
#         if 'endpoint' in data:
#             update_data['endpoint'] = data['endpoint']
#         if 'port' in data:
#             update_data['port'] = int(data['port'])
#         if 'address' in data:
#             update_data['address'] = data['address']
#         if 'geolocation_id' in data:
#             update_data['geolocation_id'] = int(data['geolocation_id'])
#         if 'status' in data:
#             update_data['status'] = data['status']
#         if 'city' in data:
#             update_data['city'] = data['city']
#         if 'country' in data:
#             update_data['country'] = data['country']
        
#         # Проверяем, что есть хотя бы одно поле для обновления
#         if not update_data:
#             return jsonify({"status": "error", "message": "Не указаны поля для обновления"}), 400
        
#         # Сначала получаем текущие данные сервера
#         server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        
#         if server_response.status_code != 200:
#             return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
#         # Данные текущего сервера
#         current_server = server_response.json()
        
#         # Если изменились endpoint или port, нужно проверить, что такая комбинация не используется другим сервером
#         if ('endpoint' in update_data or 'port' in update_data) and ('endpoint' in update_data and update_data['endpoint'] != current_server.get('endpoint') or 'port' in update_data and update_data['port'] != current_server.get('port')):
#             # Получаем список всех серверов
#             all_servers_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/all", timeout=10)
            
#             if all_servers_response.status_code == 200:
#                 all_servers = all_servers_response.json().get("servers", [])
                
#                 # Проверяем, что нет конфликтов
#                 endpoint = update_data.get('endpoint', current_server.get('endpoint'))
#                 port = update_data.get('port', current_server.get('port'))
                
#                 for server in all_servers:
#                     if server.get('id') != server_id and server.get('endpoint') == endpoint and server.get('port') == port:
#                         return jsonify({
#                             "status": "error", 
#                             "message": f"Сервер с endpoint {endpoint} и портом {port} уже существует"
#                         }), 409
        
#         # Отправляем запрос на обновление сервера в DATABASE_SERVICE_URL
#         logger.info(f"Отправка запроса на обновление сервера {server_id} с данными: {update_data}")
#         update_response = requests.put(
#             f"{DATABASE_SERVICE_URL}/api/servers/{server_id}",
#             json=update_data,
#             timeout=15
#         )
        
#         if update_response.status_code != 200:
#             logger.error(f"Ошибка при обновлении сервера: {update_response.status_code}, {update_response.text}")
#             return jsonify({
#                 "status": "error", 
#                 "message": f"Ошибка при обновлении сервера: {update_response.status_code}"
#             }), 500
        
#         # Возвращаем успешный результат
#         logger.info(f"Сервер {server_id} успешно обновлен с полями: {list(update_data.keys())}")
#         return jsonify({
#             "status": "success", 
#             "message": "Данные сервера успешно обновлены",
#             "updated_fields": list(update_data.keys())
#         })
#     except Exception as e:
#         logger.error(f"Ошибка при обновлении сервера: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500
        
#         # Обновляем данные сервера через DATABASE_SERVICE_URL
#         # Поскольку напрямую такого API может не быть, мы можем создать или использовать
#         # другие API, например, для обновления статуса
        
#         # Обновляем базовые данные через API обновления статуса
#         if 'status' in update_data:
#             status_response = requests.post(
#                 f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/status",
#                 json={"status": update_data['status']},
#                 timeout=10
#             )
            
#             if status_response.status_code != 200:
#                 return jsonify({
#                     "status": "error", 
#                     "message": f"Ошибка при обновлении статуса сервера: {status_response.status_code}"
#                 }), 500
        
#         # Возвращаем успешный результат
#         # В реальной реализации вы могли бы расширить API сервера базы данных
#         # для поддержки полного обновления атрибутов сервера
#         return jsonify({
#             "status": "success", 
#             "message": "Данные сервера успешно обновлены",
#             "updated_fields": list(update_data.keys())
#         })
#     except Exception as e:
#         logger.error(f"Ошибка при обновлении сервера: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servers/add', methods=['GET'])
@login_required
def add_server():
    """Страница добавления нового сервера."""
    try:
        # Получаем список геолокаций для формы
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations", timeout=10)
        geolocations = []
        
        if response.status_code == 200:
            geolocations = response.json().get("geolocations", [])
        
        return render_template('servers/add.html', geolocations=geolocations)
    except Exception as e:
        logger.error(f"Ошибка при загрузке страницы добавления сервера: {str(e)}")
        flash(f"Ошибка при загрузке страницы: {str(e)}", 'danger')
        return redirect(url_for('servers'))

@app.route('/servers/edit/<int:server_id>', methods=['GET'])
@login_required
def edit_server(server_id):
    """Страница редактирования сервера."""
    try:
        # Получаем информацию о сервере
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        
        if response.status_code != 200:
            flash(f"Сервер с ID {server_id} не найден", 'danger')
            return redirect(url_for('servers'))
        
        server_data = response.json()
        
        # Получаем список геолокаций для формы
        geo_response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations", timeout=10)
        geolocations = []
        
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get("geolocations", [])
        
        return render_template(
            'servers/edit.html', 
            server=server_data, 
            geolocations=geolocations
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке страницы редактирования сервера {server_id}: {str(e)}")
        flash(f"Ошибка при загрузке страницы: {str(e)}", 'danger')
        return redirect(url_for('servers'))


@app.route('/servers/<int:server_id>', methods=['GET'])
@login_required
def server_details(server_id):
    """Страница с детальной информацией о сервере."""
    try:
        # Получаем информацию о сервере
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        
        if response.status_code != 200:
            flash(f"Сервер с ID {server_id} не найден", 'danger')
            return redirect(url_for('servers'))
        
        server_data = response.json()
        
        # Получаем список геолокаций для формы редактирования
        geo_response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations", timeout=10)
        geolocations = []
        
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get("geolocations", [])
        
        # Получаем метрики сервера
        metrics_response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/metrics?hours=24", 
            timeout=10
        )
        
        server_metrics = {}
        if metrics_response.status_code == 200:
            server_metrics = metrics_response.json()
        
        return render_template(
            'servers/details.html', 
            server=server_data, 
            geolocations=geolocations,
            metrics=server_metrics
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о сервере {server_id}: {str(e)}")
        flash(f"Ошибка при загрузке данных сервера: {str(e)}", 'danger')
        return redirect(url_for('servers'))

@app.route('/api/servers/<int:server_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_server_operations(server_id):
    """API для операций с сервером: получение, обновление, удаление."""
    if request.method == 'GET':
        try:
            response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
            if response.status_code == 200:
                server = response.json()
                return jsonify(server), 200
            else:
                return jsonify({"error": f"Сервер с ID {server_id} не найден"}), 404
        except Exception as e:
            logger.error(f"Ошибка при получении информации о сервере: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'PUT':
        data = request.json
        
        # Формируем данные для запроса
        update_data = {}
        
        # Добавляем поля, которые разрешено обновлять
        if 'endpoint' in data:
            update_data['endpoint'] = data['endpoint']
        if 'port' in data:
            update_data['port'] = int(data['port'])
        if 'address' in data:
            update_data['address'] = data['address']
        if 'geolocation_id' in data:
            update_data['geolocation_id'] = int(data['geolocation_id'])
        if 'status' in data:
            update_data['status'] = data['status']
        if 'city' in data and 'country' in data:
            # Если указаны город и страна, то обновляем также местоположение сервера
            update_data['city'] = data['city']
            update_data['country'] = data['country']
        
        # Проверяем, что есть хотя бы одно поле для обновления
        if not update_data:
            return jsonify({"status": "error", "message": "Не указаны поля для обновления"}), 400
        
        # Сначала получаем текущие данные сервера
        server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        
        if server_response.status_code != 200:
            return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
        # Данные текущего сервера
        current_server = server_response.json()
        
        # Если изменились endpoint или port, нужно проверить, что такая комбинация не используется другим сервером
        if ('endpoint' in update_data or 'port' in update_data) and ('endpoint' in update_data and update_data['endpoint'] != current_server.get('endpoint') or 'port' in update_data and update_data['port'] != current_server.get('port')):
            # Получаем список всех серверов
            all_servers_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/all", timeout=10)
            
            if all_servers_response.status_code == 200:
                all_servers = all_servers_response.json().get("servers", [])
                
                # Проверяем, что нет конфликтов
                endpoint = update_data.get('endpoint', current_server.get('endpoint'))
                port = update_data.get('port', current_server.get('port'))
                
                for server in all_servers:
                    if server.get('id') != server_id and server.get('endpoint') == endpoint and server.get('port') == port:
                        return jsonify({
                            "status": "error", 
                            "message": f"Сервер с endpoint {endpoint} и портом {port} уже существует"
                        }), 409
        
        # Обновляем базовые данные через API обновления статуса
        if 'status' in update_data:
            status_response = requests.post(
                f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/status",
                json={"status": update_data['status']},
                timeout=10
            )
            
            if status_response.status_code != 200:
                return jsonify({
                    "status": "error", 
                    "message": f"Ошибка при обновлении статуса сервера: {status_response.status_code}"
                }), 500
        
        # Возвращаем успешный результат
        return jsonify({
            "status": "success", 
            "message": "Данные сервера успешно обновлены",
            "updated_fields": list(update_data.keys())
        })

    elif request.method == 'DELETE':
        try:
            # Получаем информацию о сервере, чтобы узнать публичный ключ
            server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
            
            if server_response.status_code != 200:
                return jsonify({"status": "error", "message": "Сервер не найден"}), 404
            
            server_data = server_response.json()
            public_key = server_data.get("public_key")
            
            # Удаляем сервер из WireGuard конфигурации
            if public_key:
                # wg_response = requests.delete(f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", timeout=10)
                wg_response = requests.delete(f"{WIREGUARD_SERVICE_URL}/remove/", timeout=10)
                if wg_response.status_code != 200:
                    logger.warning(f"Ошибка при удалении пира из WireGuard: {wg_response.status_code}")
            
            # Обновляем статус сервера в базе данных (помечаем как неактивный)
            status_response = requests.post(
                f"{DATABASE_SERVICE_URL}/api/servers/{server_id}/status",
                json={"status": "inactive"},
                timeout=10
            )
            
            if status_response.status_code != 200:
                return jsonify({"status": "error", "message": "Ошибка при обновлении статуса сервера"}), 500
            
            return jsonify({"status": "success", "message": "Сервер успешно удален"})
        except Exception as e:
            logger.error(f"Ошибка при удалении сервера: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

# @app.route('/api/geolocations', methods=['GET'])
# @login_required
# def api_get_geolocations():
#     """API для получения списка геолокаций."""
#     try:
#         response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations", timeout=10)
        
#         if response.status_code == 200:
#             geolocations = response.json().get("geolocations", [])
#             return jsonify({"status": "success", "geolocations": geolocations})
#         else:
#             return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка геолокаций: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500
# @app.route('/api/geolocations', methods=['GET'])
# @login_required
# def api_get_geolocations():
#     """API для получения списка геолокаций."""
#     try:
#         logger.info("Запрос на получение списка геолокаций")
#         response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations", timeout=10)
        
#         if response.status_code == 200:
#             geolocations = response.json().get("geolocations", [])
#             logger.info(f"Получено {len(geolocations)} геолокаций")
#             return jsonify({"status": "success", "geolocations": geolocations})
#         else:
#             logger.error(f"Ошибка API при получении геолокаций: {response.status_code}, {response.text}")
#             return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка геолокаций: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/geolocations/<int:geo_id>', methods=['DELETE'])
@login_required
def api_delete_geolocation(geo_id):
    """API для удаления геолокации."""
    try:
        # Отправляем запрос на удаление геолокации
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            timeout=15
        )
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "Геолокация успешно удалена"}), 200
        else:
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при удалении геолокации"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
    except Exception as e:
        logger.error(f"Ошибка при удалении геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['GET'])
@login_required
def api_get_geolocation(geo_id):
    """API для получения детальной информации о геолокации."""
    try:
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            geolocation = response.json()
            return jsonify({"status": "success", "geolocation": geolocation})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при получении информации о геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Добавьте эти обработчики в ваш API файл для панели администратора

@app.route('/api/servers', methods=['GET'])
def api_get_servers():
    """API-эндпоинт для получения списка серверов"""
    try:
        # Запрос к database-service для получения серверов
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers")
        
        if response.status_code != 200:
            app.logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "error": "Не удалось получить список серверов",
                "details": response.text
            }), 500
        
        return response.json()
    except Exception as e:
        app.logger.exception(f"Error getting servers: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

@app.route('/api/servers/<int:server_id>', methods=['GET'])
def api_get_server(server_id):
    """API-эндпоинт для получения информации о сервере"""
    try:
        # Запрос к database-service для получения информации о сервере
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}")
        
        if response.status_code == 404:
            return jsonify({"error": "Сервер не найден"}), 404
        
        if response.status_code != 200:
            app.logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "error": "Не удалось получить информацию о сервере",
                "details": response.text
            }), 500
        
        return response.json()
    except Exception as e:
        app.logger.exception(f"Error getting server details: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

# @app.route('/api/servers', methods=['POST'])
# def api_add_server():
#     """API-эндпоинт для добавления нового сервера"""
#     try:
#         # Получение данных из запроса
#         data = request.json
#         if not data:
#             return jsonify({"error": "Отсутствуют данные запроса"}), 400
        
#         # Проверка обязательных полей
#         required_fields = ['name', 'location', 'api_url', 'geolocation_id']
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({"error": f"Отсутствует обязательное поле: {field}"}), 400
        
#         # Преобразуем geolocation_id в int, если это строка
#         if 'geolocation_id' in data and isinstance(data['geolocation_id'], str) and data['geolocation_id'].isdigit():
#             data['geolocation_id'] = int(data['geolocation_id'])
        
#         # Используем тестовый режим, если указан
#         if data.get('test_mode'):
#             # Отправляем запрос напрямую в wireguard-proxy для создания тестового сервера
#             response = requests.post(f"{WIREGUARD_PROXY_URL}/admin/servers", json=data)
#         else:
#             # Отправляем запрос в database-service для добавления сервера
#             response = requests.post(f"{DATABASE_SERVICE_URL}/api/servers/add", json=data)
        
#         if response.status_code != 200:
#             app.logger.error(f"Error from service: {response.status_code} {response.text}")
#             return jsonify({
#                 "error": "Не удалось добавить сервер",
#                 "details": response.text
#             }), response.status_code
        
#         # Логируем успешное добавление сервера
#         response_data = response.json()
#         app.logger.info(f"Server added successfully: {response_data}")
        
#         return response.json()
#     except Exception as e:
#         app.logger.exception(f"Error adding server: {e}")
#         return jsonify({
#             "error": "Внутренняя ошибка сервера",
#             "details": str(e)
#         }), 500

@app.route('/api/servers', methods=['POST'])
@login_required
def api_add_server():
    try:
        data = request.json
        logger.info(f"Получены данные для добавления сервера: {data}")
        
        # Проверяем обязательные поля
        required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Отсутствуют обязательные поля: {missing_fields}")
            return jsonify({"status": "error", "message": f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"}), 400
        
        # Добавляем имя, если оно не указано
        if 'name' not in data or not data['name']:
            data['name'] = f"Сервер {data['endpoint']}:{data['port']}"
            logger.info(f"Автоматически сгенерировано имя сервера: {data['name']}")
        
        # Генерируем API ключ, если не указан
        if 'api_key' not in data or not data['api_key']:
            import secrets
            data['api_key'] = secrets.token_hex(16)
            logger.info(f"Автоматически сгенерирован API ключ для сервера")
        
        
        # Проверка обязательных полей и дополнительная отладка
        if not data:
            logger.error("Получены пустые данные")
            return jsonify({"status": "error", "message": "Пустые данные запроса"}), 400
            
        required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Отсутствуют обязательные поля: {missing_fields}. Полученные данные: {data}")
            return jsonify({"status": "error", "message": f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"}), 400
        
        # Проверка типов данных с более подробной диагностикой
        try:
            # Приводим полученные данные к ожидаемым типам
            data['port'] = int(data['port']) if isinstance(data['port'], str) else data['port']
            data['geolocation_id'] = int(data['geolocation_id']) if isinstance(data['geolocation_id'], str) else data['geolocation_id']
            
            # Проверяем соответствие типов после конвертации
            if not isinstance(data['port'], int):
                return jsonify({"status": "error", "message": f"Поле 'port' должно быть целым числом. Получено: {type(data['port']).__name__}"}), 400
            if not isinstance(data['geolocation_id'], int):
                return jsonify({"status": "error", "message": f"Поле 'geolocation_id' должно быть целым числом. Получено: {type(data['geolocation_id']).__name__}"}), 400
                
        except ValueError as e:
            logger.error(f"Ошибка преобразования типов данных: {str(e)}, данные: {data}")
            return jsonify({"status": "error", "message": f"Ошибка в данных: {str(e)}"}), 400
        
        # Остальной код без изменений...
        
        # Преобразуем geolocation_id в int, если это строка
        if 'geolocation_id' in data and isinstance(data['geolocation_id'], str) and data['geolocation_id'].isdigit():
            data['geolocation_id'] = int(data['geolocation_id'])
        
        # Используем тестовый режим, если указан
        if data.get('test_mode'):
            # Отправляем запрос напрямую в wireguard-proxy для создания тестового сервера
            response = requests.post(f"{WIREGUARD_PROXY_URL}/admin/servers", json=data)
        else:
            # Отправляем запрос в database-service для добавления сервера
            response = requests.post(f"{DATABASE_SERVICE_URL}/api/servers/add", json=data)
        
        if response.status_code != 200:
            app.logger.error(f"Error from service: {response.status_code} {response.text}")
            return jsonify({
                "error": "Не удалось добавить сервер",
                "details": response.text
            }), response.status_code
        
        # Логируем успешное добавление сервера
        response_data = response.json()
        app.logger.info(f"Server added successfully: {response_data}")
        
        return response.json()
    except Exception as e:
        app.logger.exception(f"Error adding server: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

@app.route('/api/servers/<int:server_id>', methods=['PUT'])
def api_update_server(server_id):
    """API-эндпоинт для обновления информации о сервере"""
    try:
        # Получение данных из запроса
        data = request.json
        if not data:
            return jsonify({"error": "Отсутствуют данные запроса"}), 400
        
        # Преобразуем geolocation_id в int, если это строка
        if 'geolocation_id' in data and isinstance(data['geolocation_id'], str) and data['geolocation_id'].isdigit():
            data['geolocation_id'] = int(data['geolocation_id'])
        
        # Преобразуем is_active в bool, если это строка
        if 'is_active' in data and isinstance(data['is_active'], str):
            data['is_active'] = data['is_active'].lower() == 'true'
        
        # Преобразуем max_peers в int, если это строка
        if 'max_peers' in data and isinstance(data['max_peers'], str) and data['max_peers'].isdigit():
            data['max_peers'] = int(data['max_peers'])
        
        # Отправляем запрос в database-service для обновления сервера
        response = requests.put(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", json=data)
        
        if response.status_code == 404:
            return jsonify({"error": "Сервер не найден"}), 404
        
        if response.status_code != 200:
            app.logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "error": "Не удалось обновить сервер",
                "details": response.text
            }), response.status_code
        
        # Обновляем статус сервера в WireGuard Proxy, если это поле изменилось
        if 'is_active' in data:
            try:
                status = "active" if data['is_active'] else "inactive"
                proxy_response = requests.post(
                    f"{WIREGUARD_PROXY_URL}/admin/servers/{server_id}/status",
                    json={"status": status}
                )
                
                if proxy_response.status_code != 200:
                    app.logger.warning(
                        f"Failed to update server status in WireGuard Proxy: {proxy_response.status_code} {proxy_response.text}"
                    )
            except Exception as e:
                app.logger.warning(f"Error updating server status in WireGuard Proxy: {e}")
        
        return response.json()
    except Exception as e:
        app.logger.exception(f"Error updating server: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def api_delete_server(server_id):
    """API-эндпоинт для удаления сервера"""
    try:
        # Отправляем запрос в database-service для удаления сервера
        response = requests.delete(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}")
        
        if response.status_code == 404:
            return jsonify({"error": "Сервер не найден"}), 404
        
        if response.status_code != 200:
            app.logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "error": "Не удалось удалить сервер",
                "details": response.text
            }), response.status_code
        
        return response.json()
    except Exception as e:
        app.logger.exception(f"Error deleting server: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

@app.route('/api/geolocations', methods=['GET'])
def api_get_geolocations():
    """API-эндпоинт для получения списка геолокаций"""
    try:
        # Запрос к database-service для получения геолокаций
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations")
        
        if response.status_code != 200:
            app.logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "geolocations": [],  # Возвращаем пустой список вместо ошибки
                "error_details": {
                    "message": "Не удалось получить список геолокаций",
                    "status_code": response.status_code,
                    "response": response.text
                }
            })
        
        return response.json()
    except Exception as e:
        app.logger.exception(f"Error getting geolocations: {e}")
        return jsonify({
            "geolocations": [],  # Возвращаем пустой список вместо ошибки
            "error_details": {
                "message": "Внутренняя ошибка сервера",
                "exception": str(e)
            }
        })

@app.route('/api/servers/<int:server_id>/ping', methods=['GET'])
def api_ping_server(server_id):
    """API-эндпоинт для проверки соединения с сервером"""
    try:
        # Получаем информацию о сервере
        server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}")
        
        if server_response.status_code != 200:
            return jsonify({"error": "Сервер не найден"}), 404
        
        server_data = server_response.json().get('server', {})
        api_url = server_data.get('api_url')
        
        if not api_url:
            return jsonify({"error": "У сервера отсутствует API URL"}), 400
        
        # Проверяем соединение с сервером
        import time
        start_time = time.time()
        
        try:
            # Отправляем запрос к API сервера
            ping_response = requests.get(f"{api_url}/status", timeout=5)
            latency_ms = (time.time() - start_time) * 1000  # в миллисекундах
            
            if ping_response.status_code == 200:
                return jsonify({
                    "success": True,
                    "message": "Соединение с сервером установлено",
                    "latency_ms": round(latency_ms, 2),
                    "status": "online"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"Сервер вернул код ошибки: {ping_response.status_code}",
                    "latency_ms": round(latency_ms, 2),
                    "status": "error"
                })
        except requests.exceptions.Timeout:
            return jsonify({
                "success": False,
                "message": "Превышено время ожидания ответа от сервера",
                "latency_ms": 5000,  # 5 секунд тайм-аут
                "status": "timeout"
            })
        except requests.exceptions.ConnectionError:
            return jsonify({
                "success": False,
                "message": "Не удалось установить соединение с сервером",
                "status": "offline"
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Ошибка при проверке соединения: {str(e)}",
                "status": "error"
            })
    except Exception as e:
        app.logger.exception(f"Error pinging server: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

@app.route('/api/servers/<int:server_id>/restart', methods=['POST'])
def api_restart_server(server_id):
    """API-эндпоинт для перезапуска сервера"""
    try:
        # Получаем информацию о сервере
        server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}")
        
        if server_response.status_code != 200:
            return jsonify({"error": "Сервер не найден"}), 404
        
        server_data = server_response.json().get('server', {})
        api_url = server_data.get('api_url')
        
        if not api_url:
            return jsonify({"error": "У сервера отсутствует API URL"}), 400
        
        # Отправляем запрос на перезапуск сервера
        try:
            restart_response = requests.post(f"{api_url}/restart", timeout=10)
            
            if restart_response.status_code == 200:
                return jsonify({
                    "success": True,
                    "message": "Сервер успешно перезапущен"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"Ошибка при перезапуске сервера: {restart_response.status_code}",
                    "details": restart_response.text
                })
        except requests.exceptions.Timeout:
            return jsonify({
                "success": False,
                "message": "Превышено время ожидания ответа от сервера"
            })
        except requests.exceptions.ConnectionError:
            return jsonify({
                "success": False,
                "message": "Не удалось установить соединение с сервером"
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Ошибка при перезапуске сервера: {str(e)}"
            })
    except Exception as e:
        app.logger.exception(f"Error restarting server: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)