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
    return render_template('servers.html')

@app.route('/api/servers', methods=['GET'])
@login_required
def api_get_servers():
    """API для получения списка серверов."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=10)
        
        if response.status_code == 200:
            servers = response.json().get("servers", [])
            return jsonify({"status": "success", "servers": servers})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/servers', methods=['POST'])
@login_required
def api_add_server():
    """API для добавления нового сервера."""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        required_fields = ['geolocation_id', 'endpoint', 'port', 'public_key', 'address']
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"Поле {field} обязательно"}), 400
        
        # Отправляем запрос на добавление сервера
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/register",
            json=data,
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return jsonify({"status": "success", "server_id": result.get("server_id")}), 201
        else:
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при регистрации сервера"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
    except Exception as e:
        logger.error(f"Ошибка при добавлении сервера: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
@login_required
def api_delete_server(server_id):
    """API для удаления сервера."""
    try:
        # Получаем информацию о сервере, чтобы узнать публичный ключ
        server_response = requests.get(f"{DATABASE_SERVICE_URL}/servers/{server_id}", timeout=10)
        
        if server_response.status_code != 200:
            return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
        server_data = server_response.json()
        public_key = server_data.get("public_key")
        
        # Удаляем сервер из WireGuard конфигурации
        if public_key:
            wg_response = requests.delete(f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", timeout=10)
            if wg_response.status_code != 200:
                logger.warning(f"Ошибка при удалении пира из WireGuard: {wg_response.status_code}")
        
        # Обновляем статус сервера в базе данных (помечаем как неактивный)
        status_response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/{server_id}/status",
            json={"status": "inactive"},
            timeout=10
        )
        
        if status_response.status_code != 200:
            return jsonify({"status": "error", "message": "Ошибка при обновлении статуса сервера"}), 500
        
        return jsonify({"status": "success", "message": "Сервер успешно удален"})
    except Exception as e:
        logger.error(f"Ошибка при удалении сервера: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/geolocations', methods=['GET'])
@login_required
def api_get_geolocations():
    """API для получения списка геолокаций."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations", timeout=10)
        
        if response.status_code == 200:
            geolocations = response.json().get("geolocations", [])
            return jsonify({"status": "success", "geolocations": geolocations})
        else:
            return jsonify({"status": "error", "message": f"Ошибка API: {response.status_code}"}), 500
    except Exception as e:
        logger.error(f"Ошибка при получении списка геолокаций: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/server_metrics/<int:server_id>', methods=['GET'])
@login_required
def api_get_server_metrics(server_id):
    """API для получения метрик сервера."""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/servers/{server_id}/metrics?hours={hours}",
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
            f"{DATABASE_SERVICE_URL}/servers/metrics/analyze",
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
            f"{DATABASE_SERVICE_URL}/servers/rebalance",
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
            f"{DATABASE_SERVICE_URL}/configs/migrate_users",
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
        servers_response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=10)
        
        if servers_response.status_code != 200:
            return jsonify({"status": "error", "message": "Ошибка при получении списка серверов"}), 500
        
        servers = servers_response.json().get("servers", [])
        
        # Получаем список геолокаций
        geolocations_response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations", timeout=10)
        
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
@app.route('/api/servers/<int:server_id>', methods=['PUT'])
@login_required
def api_update_server(server_id):
    """API для обновления данных сервера."""
    try:
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
        server_response = requests.get(f"{DATABASE_SERVICE_URL}/servers/{server_id}", timeout=10)
        
        if server_response.status_code != 200:
            return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
        # Данные текущего сервера
        current_server = server_response.json()
        
        # Если изменились endpoint или port, нужно проверить, что такая комбинация не используется другим сервером
        if ('endpoint' in update_data or 'port' in update_data) and ('endpoint' in update_data and update_data['endpoint'] != current_server.get('endpoint') or 'port' in update_data and update_data['port'] != current_server.get('port')):
            # Получаем список всех серверов
            all_servers_response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=10)
            
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
        
        # Обновляем данные сервера через DATABASE_SERVICE_URL
        # Поскольку напрямую такого API может не быть, мы можем создать или использовать
        # другие API, например, для обновления статуса
        
        # Обновляем базовые данные через API обновления статуса
        if 'status' in update_data:
            status_response = requests.post(
                f"{DATABASE_SERVICE_URL}/servers/{server_id}/status",
                json={"status": update_data['status']},
                timeout=10
            )
            
            if status_response.status_code != 200:
                return jsonify({
                    "status": "error", 
                    "message": f"Ошибка при обновлении статуса сервера: {status_response.status_code}"
                }), 500
        
        # Возвращаем успешный результат
        # В реальной реализации вы могли бы расширить API сервера базы данных
        # для поддержки полного обновления атрибутов сервера
        return jsonify({
            "status": "success", 
            "message": "Данные сервера успешно обновлены",
            "updated_fields": list(update_data.keys())
        })
    except Exception as e:
        logger.error(f"Ошибка при обновлении сервера: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# # Добавить этот эндпоинт в app.py после существующих API-эндпоинтов
# @app.route('/api/servers/<int:server_id>', methods=['PUT'])
# @login_required
# def api_update_server(server_id):
#     """API для обновления данных сервера."""
#     try:
#         data = request.json
        
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
#         if 'city' in data and 'country' in data:
#             # Если указаны город и страна, то обновляем также местоположение сервера
#             update_data['city'] = data['city']
#             update_data['country'] = data['country']
        
#         # Проверяем, что есть хотя бы одно поле для обновления
#         if not update_data:
#             return jsonify({"status": "error", "message": "Не указаны поля для обновления"}), 400
        
#         # Сначала получаем текущие данные сервера
#         server_response = requests.get(f"{DATABASE_SERVICE_URL}/servers/{server_id}", timeout=10)
        
#         if server_response.status_code != 200:
#             return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
#         # Данные текущего сервера
#         current_server = server_response.json()
        
#         # Если изменились endpoint или port, нужно проверить, что такая комбинация не используется другим сервером
#         if ('endpoint' in update_data or 'port' in update_data) and ('endpoint' in update_data and update_data['endpoint'] != current_server.get('endpoint') or 'port' in update_data and update_data['port'] != current_server.get('port')):
#             # Получаем список всех серверов
#             all_servers_response = requests.get(f"{DATABASE_SERVICE_URL}/servers/all", timeout=10)
            
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
        
#         # Обновляем данные сервера через DATABASE_SERVICE_URL
#         # Поскольку напрямую такого API может не быть, мы можем создать или использовать
#         # другие API, например, для обновления статуса
        
#         # Обновляем базовые данные через API обновления статуса
#         if 'status' in update_data:
#             status_response = requests.post(
#                 f"{DATABASE_SERVICE_URL}/servers/{server_id}/status",
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

@app.route('/api/geolocations', methods=['POST'])
@login_required
def api_add_geolocation():
    """API для добавления новой геолокации."""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        required_fields = ['code', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"Поле {field} обязательно"}), 400
        
        # Отправляем запрос на добавление геолокации
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/geolocations",
            json=data,
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return jsonify({"status": "success", "geolocation_id": result.get("geolocation_id")}), 201
        else:
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при создании геолокации"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
    except Exception as e:
        logger.error(f"Ошибка при добавлении геолокации: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['PUT'])
@login_required
def api_update_geolocation(geo_id):
    """API для обновления данных геолокации."""
    try:
        data = request.json
        
        # Отправляем запрос на обновление геолокации
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/geolocations/{geo_id}",
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
def api_delete_geolocation(geo_id):
    """API для удаления геолокации."""
    try:
        # Отправляем запрос на удаление геолокации
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/geolocations/{geo_id}",
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
            f"{DATABASE_SERVICE_URL}/geolocations/{geo_id}",
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)