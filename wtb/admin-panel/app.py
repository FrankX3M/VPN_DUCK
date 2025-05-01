import os
import logging
import secrets
from datetime import datetime

# Импорты Flask и его компонентов
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session, send_from_directory
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

# Импорты вашего приложения
from forms import FilterForm, ServerForm, GeolocationForm, LoginForm
from utils.chart_generator import ChartGenerator
from utils.db_client import DatabaseClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import mock data for development mode
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'
if USE_MOCK_DATA:
    from utils.mock_data import (MOCK_SERVERS, MOCK_GEOLOCATIONS, 
                               generate_mock_metrics, find_server, 
                               find_geolocation, filter_servers,
                               authenticate_user, MOCK_USERS)

# Инициализация Flask-приложения
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['WTF_CSRF_ENABLED'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files
app.config['DEBUG'] = os.environ.get('FLASK_ENV') == 'development'

# Required for CSRF protection in WTF-Forms
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database client
db_client = DatabaseClient(
    base_url=os.environ.get('API_BASE_URL', 'http://localhost:5000'),
    api_key=os.environ.get('API_KEY', 'dev_key')
)

# Import models and user loader
from models import User

# Ensure static directories exist 
for static_dir in ['css', 'js', 'img']:
    os.makedirs(os.path.join('static', static_dir), exist_ok=True)

# Функции для создания шаблонов ошибок и favicon
def create_error_templates():
    """Создает шаблоны страниц ошибок, если они не существуют"""
    # Проверяем существование директории и создаем её при необходимости
    templates_dir = 'templates'
    errors_dir = os.path.join(templates_dir, 'errors')
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    if not os.path.exists(errors_dir):
        os.makedirs(errors_dir)
    
    # Создаем шаблон 404.html
    error_404_path = os.path.join(errors_dir, '404.html')
    if not os.path.exists(error_404_path):
        with open(error_404_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            padding-top: 50px; 
            padding-bottom: 50px; 
            background-color: #f8f9fa;
            text-align: center;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error-code {
            font-size: 120px;
            color: #dc3545;
            margin-bottom: 0;
        }
        .error-message {
            font-size: 24px;
            margin-bottom: 20px;
            color: #343a40;
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }
        .btn:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">404</h1>
        <p class="error-message">Page Not Found</p>
        <p>The page you are looking for does not exist or has been moved.</p>
        <a href="/" class="btn">Return to Home</a>
    </div>
</body>
</html>
''')
    
    # Создаем шаблон 500.html
    error_500_path = os.path.join(errors_dir, '500.html')
    if not os.path.exists(error_500_path):
        with open(error_500_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>500 - Server Error</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            padding-top: 50px; 
            padding-bottom: 50px; 
            background-color: #f8f9fa;
            text-align: center;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error-code {
            font-size: 120px;
            color: #dc3545;
            margin-bottom: 0;
        }
        .error-message {
            font-size: 24px;
            margin-bottom: 20px;
            color: #343a40;
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }
        .btn:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">500</h1>
        <p class="error-message">Server Error</p>
        <p>Sorry, something went wrong on our end. Please try again later.</p>
        <a href="/" class="btn">Return to Home</a>
    </div>
</body>
</html>
''')

def create_favicon():
    """Создает простой favicon.ico, если он не существует"""
    favicon_dir = os.path.join('static', 'img')
    os.makedirs(favicon_dir, exist_ok=True)
    
    favicon_path = os.path.join(favicon_dir, 'favicon.ico')
    if not os.path.exists(favicon_path):
        try:
            # Создаем минимальный ico-файл
            with open(favicon_path, 'wb') as f:
                # Минимальная структура ICO-файла
                f.write(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        except Exception as e:
            logger.error(f"Error creating favicon: {str(e)}")

# Создаем шаблоны ошибок и favicon сразу при загрузке модуля
create_error_templates()
create_favicon()

# Обработчик для source map файлов, которые часто запрашиваются браузерами
@app.route('/static/<path:filename>.map')
def serve_sourcemap(filename):
    try:
        path_parts = filename.split('/')
        if len(path_parts) > 1:
            # Если путь содержит поддиректории
            basedir = os.path.join('static', *path_parts[:-1])
            basename = path_parts[-1] + '.map'
            return send_from_directory(basedir, basename)
        else:
            # Если файл находится прямо в static
            return send_from_directory('static', filename + '.map')
    except:
        return '', 404

@app.route('/api/servers', methods=['POST'])
@login_required
def api_add_server():
    try:
        data = request.json
        logger.info(f"Получены данные для добавления сервера: {data}")
        
        # Проверка наличия данных
        if not data:
            logger.error("Получены пустые данные")
            return jsonify({"status": "error", "message": "Пустые данные запроса"}), 400
            
        # Проверяем обязательные поля
        required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Отсутствуют обязательные поля: {missing_fields}. Полученные данные: {data}")
            return jsonify({"status": "error", "message": f"Отсутствуют поля: {', '.join(missing_fields)}"}), 400
        
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
        
        # Добавляем имя, если оно не указано
        if 'name' not in data or not data['name']:
            data['name'] = f"Сервер {data['endpoint']}:{data['port']}"
            logger.info(f"Автоматически сгенерировано имя сервера: {data['name']}")
        
        # Генерируем API ключ, если не указан
        if 'api_key' not in data or not data['api_key']:
            import secrets
            data['api_key'] = secrets.token_hex(16)
            logger.info(f"Автоматически сгенерирован API ключ для сервера")
        
        # Добавляем API URL, если не указан
        if 'api_url' not in data or not data['api_url']:
            data['api_url'] = f"http://{data['endpoint']}:{data['port']}/api"
            logger.info(f"Автоматически сгенерирован API URL для сервера: {data['api_url']}")
        
        # Добавляем статус, если не указан
        if 'status' not in data or not data['status']:
            data['status'] = 'active'
            logger.info(f"Задан статус сервера по умолчанию: {data['status']}")
        
        # Отправляем запрос в database-service для добавления сервера
        response = requests.post(f"{DATABASE_SERVICE_URL}/api/servers/add", json=data)
        
        if response.status_code != 200:
            logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "status": "error",
                "message": "Не удалось добавить сервер",
                "details": response.text
            }), response.status_code
        
        # Логируем успешное добавление сервера
        response_data = response.json()
        logger.info(f"Сервер успешно добавлен: {response_data}")
        
        return jsonify({
            "status": "success",
            "message": "Сервер успешно добавлен",
            "server": response_data
        }), 201
    except Exception as e:
        logger.exception(f"Ошибка при добавлении сервера: {e}")
        return jsonify({
            "status": "error",
            "message": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500
    try:
        data = request.json
        logger.info(f"Получены данные для добавления сервера: {data}")
        
        # Проверка наличия данных
        if not data:
            logger.error("Получены пустые данные")
            return jsonify({"status": "error", "message": "Пустые данные запроса"}), 400
            
        # Проверяем обязательные поля
        required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Отсутствуют обязательные поля: {missing_fields}. Полученные данные: {data}")
            return jsonify({"status": "error", "message": f"Отсутствуют поля: {', '.join(missing_fields)}"}), 400
        
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
        
        # Добавляем имя, если оно не указано
        if 'name' not in data or not data['name']:
            data['name'] = f"Сервер {data['endpoint']}:{data['port']}"
            logger.info(f"Автоматически сгенерировано имя сервера: {data['name']}")
        
        # Генерируем API ключ, если не указан
        if 'api_key' not in data or not data['api_key']:
            import secrets
            data['api_key'] = secrets.token_hex(16)
            logger.info(f"Автоматически сгенерирован API ключ для сервера")
        
        # Отправляем запрос в database-service для добавления сервера
        response = requests.post(f"{DATABASE_SERVICE_URL}/api/servers/add", json=data)
        
        if response.status_code != 200:
            logger.error(f"Error from database service: {response.status_code} {response.text}")
            return jsonify({
                "error": "Не удалось добавить сервер",
                "details": response.text
            }), response.status_code
        
        # Логируем успешное добавление сервера
        response_data = response.json()
        logger.info(f"Server added successfully: {response_data}")
        
        return response.json()
    except Exception as e:
        logger.exception(f"Error adding server: {e}")
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500


@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
@login_required
def api_delete_server(server_id):
    try:
        # Логирование запроса на удаление
        logger.info(f"Получен запрос на удаление сервера {server_id}")
        
        # Получаем информацию о сервере, чтобы узнать публичный ключ
        server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        
        if server_response.status_code != 200:
            logger.error(f"Сервер с ID {server_id} не найден в базе данных")
            return jsonify({"status": "error", "message": "Сервер не найден"}), 404
        
        server_data = server_response.json()
        public_key = server_data.get("public_key")
        
        # Удаляем пир с WireGuard сервера, если есть публичный ключ
        if public_key:
            try:
                # Исправлено: правильный URL для удаления пира
                wg_response = requests.delete(
                    f"{WIREGUARD_SERVICE_URL}/api/remove",
                    json={"public_key": public_key},
                    timeout=10
                )
                
                if wg_response.status_code != 200:
                    logger.warning(f"Ошибка при удалении пира из WireGuard: {wg_response.status_code}, {wg_response.text}")
                else:
                    logger.info(f"Пир с публичным ключом {public_key} успешно удален из WireGuard")
            except Exception as e:
                logger.warning(f"Ошибка при обращении к WireGuard-сервису: {str(e)}")
        
        # Удаляем сервер из базы данных
        delete_response = requests.delete(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=15)
        
        if delete_response.status_code != 200:
            logger.error(f"Ошибка при удалении сервера: {delete_response.status_code}, {delete_response.text}")
            
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Не удалось удалить сервер"
            try:
                error_data = delete_response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
                
            return jsonify({"status": "error", "message": error_message}), delete_response.status_code
        
        logger.info(f"Сервер {server_id} успешно удален")
        return jsonify({"status": "success", "message": "Сервер успешно удален"})
        
    except Exception as e:
        logger.exception(f"Ошибка при удалении сервера: {e}")
        return jsonify({
            "status": "error",
            "message": "Внутренняя ошибка сервера",
            "details": str(e)
        }), 500


@app.route('/api/servers/<int:server_id>', methods=['PUT'])
@login_required
def api_update_server(server_id):
    try:
        data = request.json
        logger.info(f"Получен запрос на обновление сервера {server_id} с данными: {data}")
        
        # Проверка наличия данных
        if not data:
            logger.error("Получены пустые данные")
            return jsonify({"status": "error", "message": "Пустые данные запроса"}), 400
        
        # Получаем текущие данные сервера
        current_server_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", timeout=10)
        if current_server_response.status_code != 200:
            logger.error(f"Сервер с ID {server_id} не найден в базе данных")
            return jsonify({"status": "error", "message": "Сервер не найден"}), 404
            
        current_server = current_server_response.json()
        
        # Формируем данные для запроса к базе данных
        update_data = {}
        
        # Добавляем поля, которые разрешено обновлять
        allowed_fields = ['endpoint', 'port', 'address', 'geolocation_id', 'status', 'name', 'city', 'country', 'api_key', 'public_key', 'api_url']
        for field in allowed_fields:
            if field in data:
                # Преобразование числовых полей из строк в числа
                if field in ['port', 'geolocation_id'] and isinstance(data[field], str):
                    try:
                        update_data[field] = int(data[field])
                    except ValueError:
                        return jsonify({"status": "error", "message": f"Поле '{field}' должно быть числом"}), 400
                else:
                    update_data[field] = data[field]
        
        # Проверяем, что есть данные для обновления
        if not update_data:
            return jsonify({"status": "error", "message": "Не указаны поля для обновления"}), 400
        
        # Если обновляются endpoint или port, но нет api_url, генерируем его
        if ('endpoint' in update_data or 'port' in update_data) and 'api_url' not in update_data:
            # Используем новые значения, если они есть, иначе берем текущие
            endpoint = update_data.get('endpoint', current_server.get('endpoint'))
            port = update_data.get('port', current_server.get('port'))
            
            if endpoint and port:
                update_data['api_url'] = f"http://{endpoint}:{port}/api"
                logger.info(f"Автоматически обновлен API URL для сервера: {update_data['api_url']}")
        
        # Отправляем запрос в базу данных
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}",
            json=update_data,
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Ошибка при обновлении сервера: {response.status_code}, {response.text}")
            
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при обновлении сервера"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
                
            return jsonify({
                "status": "error", 
                "message": error_message,
                "details": response.text
            }), response.status_code
        
        # Логируем успешное обновление
        logger.info(f"Сервер {server_id} успешно обновлен")
        return jsonify({
            "status": "success", 
            "message": "Данные сервера успешно обновлены",
            "server_id": server_id
        })
        
    except Exception as e:
        logger.exception(f"Ошибка при обновлении сервера: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['DELETE'])
@login_required
def api_delete_geolocation(geo_id):
    try:
        logger.info(f"Получен запрос на удаление геолокации {geo_id}")
        
        # Проверка, используется ли геолокация серверами
        servers_response = requests.get(f"{DATABASE_SERVICE_URL}/api/servers", timeout=10)
        if servers_response.status_code == 200:
            servers = servers_response.json().get("servers", [])
            used_by_servers = [s for s in servers if s.get('geolocation_id') == geo_id]
            
            if used_by_servers:
                logger.warning(f"Геолокация {geo_id} используется {len(used_by_servers)} серверами. Нельзя удалить.")
                server_names = ", ".join([s.get('name', f"Сервер {s.get('id')}") for s in used_by_servers[:5]])
                
                # Если серверов больше 5, добавляем многоточие
                if len(used_by_servers) > 5:
                    server_names += " и др."
                    
                return jsonify({
                    "status": "error", 
                    "message": f"Геолокация используется {len(used_by_servers)} серверами: {server_names}. Необходимо сначала изменить геолокацию этих серверов."
                }), 400
        else:
            logger.warning(f"Не удалось получить список серверов: {servers_response.status_code}. Продолжаем удаление геолокации.")
        
        # Отправляем запрос на удаление геолокации
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Ошибка при удалении геолокации: {response.status_code}, {response.text}")
            
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при удалении геолокации"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
                elif "message" in error_data:
                    error_message = error_data.get("message")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
        
        logger.info(f"Геолокация {geo_id} успешно удалена")
        return jsonify({"status": "success", "message": "Геолокация успешно удалена"})
        
    except Exception as e:
        logger.exception(f"Ошибка при удалении геолокации: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['PUT'])
@login_required
def api_update_geolocation(geo_id):
    try:
        data = request.json
        logger.info(f"Получен запрос на обновление геолокации {geo_id} с данными: {data}")
        
        # Проверка наличия данных
        if not data:
            logger.error("Получены пустые данные")
            return jsonify({"status": "error", "message": "Пустые данные запроса"}), 400
        
        # Проверяем, существует ли геолокация
        check_response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}", timeout=10)
        if check_response.status_code != 200:
            logger.error(f"Геолокация с ID {geo_id} не найдена")
            return jsonify({"status": "error", "message": "Геолокация не найдена"}), 404
        
        # Формируем данные для запроса
        update_data = {}
        
        # Добавляем поля, которые разрешено обновлять
        allowed_fields = ['code', 'name', 'available', 'description']
        for field in allowed_fields:
            if field in data:
                # Особая обработка для поля available - преобразование в булево значение
                if field == 'available':
                    if isinstance(data[field], str):
                        update_data[field] = data[field].lower() in ['true', '1', 'yes', 'y']
                    else:
                        update_data[field] = bool(data[field])
                elif field == 'code' and isinstance(data[field], str):
                    # Преобразуем код в верхний регистр
                    update_data[field] = data[field].upper()
                else:
                    update_data[field] = data[field]
        
        # Проверяем, что есть данные для обновления
        if not update_data:
            return jsonify({"status": "error", "message": "Не указаны поля для обновления"}), 400
        
        # Отправляем запрос на обновление геолокации
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            json=update_data,
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Ошибка при обновлении геолокации: {response.status_code}, {response.text}")
            
            # Проверяем, есть ли информация об ошибке в ответе
            error_message = "Ошибка при обновлении геолокации"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
                elif "message" in error_data:
                    error_message = error_data.get("message")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
        
        logger.info(f"Геолокация {geo_id} успешно обновлена")
        return jsonify({
            "status": "success", 
            "message": "Геолокация успешно обновлена",
            "geolocation_id": geo_id
        })
        
    except Exception as e:
        logger.exception(f"Ошибка при обновлении геолокации: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/download-bootstrap', methods=['GET'])
@login_required
def admin_download_bootstrap():
    """
    Скачивает локальные копии Bootstrap, jQuery и других библиотек
    для обеспечения автономной работы панели администратора.
    """
    try:
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('index'))
            
        # Создаем папки, если их нет
        static_dir = os.path.join(app.root_path, 'static')
        css_dir = os.path.join(static_dir, 'css')
        js_dir = os.path.join(static_dir, 'js')
        
        for directory in [css_dir, js_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Список URL для скачивания
        resources = [
            {
                'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
                'path': os.path.join(css_dir, 'bootstrap.min.css')
            },
            {
                'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
                'path': os.path.join(js_dir, 'bootstrap.bundle.min.js')
            },
            {
                'url': 'https://code.jquery.com/jquery-3.6.0.min.js',
                'path': os.path.join(js_dir, 'jquery.min.js')
            },
            {
                'url': 'https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js',
                'path': os.path.join(js_dir, 'chart.min.js')
            }
        ]
        
        downloaded_files = []
        failed_files = []
        
        # Скачиваем каждый ресурс
        for resource in resources:
            try:
                logger.info(f"Скачивание {resource['url']}")
                response = requests.get(resource['url'], timeout=30)
                
                if response.status_code == 200:
                    with open(resource['path'], 'wb') as f:
                        f.write(response.content)
                    downloaded_files.append(os.path.basename(resource['path']))
                else:
                    logger.error(f"Ошибка при скачивании {resource['url']}: {response.status_code}")
                    failed_files.append(os.path.basename(resource['path']))
            except Exception as e:
                logger.exception(f"Ошибка при скачивании {resource['url']}: {str(e)}")
                failed_files.append(os.path.basename(resource['path']))
        
        # Проверяем результаты
        if failed_files:
            flash(f"Не удалось скачать некоторые файлы: {', '.join(failed_files)}", 'warning')
        
        if downloaded_files:
            flash(f"Успешно скачаны: {', '.join(downloaded_files)}", 'success')
            
        # Создаем файл конфигурации для использования локальных ресурсов
        config_path = os.path.join(app.root_path, 'config', 'local_resources.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump({
                'use_local_resources': True,
                'bootstrap_css': '/static/css/bootstrap.min.css',
                'bootstrap_js': '/static/js/bootstrap.bundle.min.js',
                'jquery_js': '/static/js/jquery.min.js',
                'chart_js': '/static/js/chart.min.js',
                'downloaded_at': datetime.now().isoformat()
            }, f, indent=4)
        
        logger.info("Локальные копии библиотек успешно скачаны")
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.exception(f"Ошибка при скачивании библиотек: {e}")
        flash(f"Произошла ошибка: {str(e)}", 'danger')
        return redirect(url_for('index'))     

# Custom static file handling to prevent sendfile issues
@app.route('/static/<path:filename>')
def custom_static(filename):
    try:
        cache_timeout = app.get_send_file_max_age(filename)
        return send_from_directory('static', filename, cache_timeout=cache_timeout)
    except Exception as e:
        logger.warning(f"Static file not found: {filename}, Error: {str(e)}")
        return '', 404

# Add favicon handler to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(os.path.join('static', 'img'), 'favicon.ico', 
                                  mimetype='image/vnd.microsoft.icon')
    except:
        logger.warning("Favicon.ico not found")
        return '', 404

@login_manager.user_loader
def load_user(user_id):
    # Fetch user from API or mock data
    try:
        if USE_MOCK_DATA:
            # Find user in mock data
            for user in MOCK_USERS:
                if str(user.get('id')) == str(user_id):
                    return User(
                        id=user.get('id'),
                        username=user.get('username'),
                        email=user.get('email'),
                        role=user.get('role', 'user')
                    )
            return None
        else:
            response = db_client.get(f'/api/users/{user_id}')
            if response and response.status_code == 200:
                user_data = response.json()
                return User(
                    id=user_data.get('id'),
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    role=user_data.get('role', 'user')
                )
    except Exception as e:
        logger.exception(f"Error loading user: {str(e)}")
    
    return None

# Custom error handlers with fallbacks
@app.errorhandler(404)
def page_not_found(e):
    try:
        return render_template('errors/404.html', now=datetime.now()), 404
    except Exception as error:
        logger.error(f"Error rendering 404 template: {str(error)}")
        error_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Page Not Found</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                h1 { color: #333; }
                .error-container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .back-link { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
                .back-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>404 - Page Not Found</h1>
                <p>The page you are looking for does not exist or has been moved.</p>
                <a href="/" class="back-link">Return to Home</a>
            </div>
        </body>
        </html>
        '''
        return error_html, 404

@app.errorhandler(500)
def server_error(e):
    try:
        return render_template('errors/500.html', now=datetime.now()), 500
    except Exception as error:
        logger.error(f"Error rendering 500 template: {str(error)}")
        error_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>500 - Server Error</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                h1 { color: #333; }
                .error-container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .back-link { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
                .back-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>500 - Server Error</h1>
                <p>Sorry, something went wrong on our end. Please try again later.</p>
                <a href="/" class="back-link">Return to Home</a>
            </div>
        </body>
        </html>
        '''
        return error_html, 500

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    error = None
    
    if form.validate_on_submit():
        try:
            # Use mock data in development mode
            if USE_MOCK_DATA:
                user_data = authenticate_user(form.username.data, form.password.data)
                if user_data:
                    user = User(
                        id=user_data.get('id'),
                        username=user_data.get('username'),
                        email=user_data.get('email'),
                        role=user_data.get('role', 'user')
                    )
                    login_user(user, remember=form.remember.data)
                    session['logged_in'] = True
                    session['username'] = user.username
                    
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))
                else:
                    error = 'Invalid username or password'
                    flash('Invalid username or password', 'danger')
            else:
                # For development/testing environment, allow a hardcoded admin account
                # In production, this should be removed and authenticate against a proper backend
                if os.environ.get('FLASK_ENV', 'production') != 'production' and \
                   form.username.data == 'admin' and form.password.data == 'admin':
                    user = User(
                        id=1,
                        username='admin',
                        email='admin@example.com',
                        role='admin'
                    )
                    login_user(user, remember=form.remember.data)
                    session['logged_in'] = True
                    session['username'] = user.username
                    
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))
                
                # Normal authentication with API
                try:
                    response = db_client.post('/api/auth/login', json={
                        'username': form.username.data,
                        'password': form.password.data
                    })
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        user = User(
                            id=user_data.get('id'),
                            username=user_data.get('username'),
                            email=user_data.get('email'),
                            role=user_data.get('role', 'user')
                        )
                        login_user(user, remember=form.remember.data)
                        session['logged_in'] = True
                        session['username'] = user.username
                        
                        # Redirect to the page they were trying to access or home
                        next_page = request.args.get('next')
                        return redirect(next_page or url_for('index'))
                    else:
                        error = 'Invalid username or password'
                        flash('Invalid username or password', 'danger')
                except Exception as e:
                    logger.exception(f"API communication error: {str(e)}")
                    error = 'Service unavailable. Please try again later.'
                    flash('Service unavailable. Please try again later.', 'danger')
        except Exception as e:
            logger.exception(f"Login error: {str(e)}")
            error = 'Service unavailable. Please try again later.'
            flash('Service unavailable. Please try again later.', 'danger')
    
    return render_template('login.html', form=form, error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', now=datetime.now())

@app.route('/dashboard')
@login_required
def dashboard():
    hours = request.args.get('hours', 24, type=int)
    
    if USE_MOCK_DATA:
        # Use mock data for development
        servers = MOCK_SERVERS
        geolocations = MOCK_GEOLOCATIONS
        
        # Get metrics for each server
        all_metrics = []
        geolocation_charts = {}
        
        for server in servers:
            server_id = server.get('id')
            metrics_data = generate_mock_metrics(server_id, hours)
            
            all_metrics.append({
                'server': server,
                'metrics': metrics_data
            })
            
            # Generate charts for geolocation if not already done
            geo_id = server.get('geolocation_id')
            if geo_id and geo_id not in geolocation_charts:
                geo_name = next((g['name'] for g in geolocations if g['id'] == geo_id), f"Location {geo_id}")
                
                # Count servers in this geolocation
                servers_count = sum(1 for s in servers if s.get('geolocation_id') == geo_id)
                
                # Generate charts
                chart_generator = ChartGenerator()
                latency_chart = chart_generator.generate_metrics_image(
                    metrics_data, 'latency', hours)
                packet_loss_chart = chart_generator.generate_metrics_image(
                    metrics_data, 'packet_loss', hours)
                    
                geolocation_charts[geo_id] = {
                    'geo_name': geo_name,
                    'servers_count': servers_count,
                    'latency_chart': latency_chart,
                    'packet_loss_chart': packet_loss_chart
                }
    else:
        # Get all servers from API
        try:
            response = db_client.get('/api/servers')
            if response.status_code == 200:
                servers = response.json()
            else:
                servers = []
                flash('Failed to fetch server list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching servers: {str(e)}")
            servers = []
            flash('Service unavailable', 'danger')
        
        # Get geolocations from API
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                geolocations = response.json()
            else:
                geolocations = []
                flash('Failed to fetch geolocation list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching geolocations: {str(e)}")
            geolocations = []
        
        # Get metrics for each server
        all_metrics = []
        geolocation_charts = {}
        
        for server in servers:
            try:
                metrics_response = db_client.get(f'/api/servers/{server["id"]}/metrics', 
                                                params={'hours': hours})
                
                if metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    all_metrics.append({
                        'server': server,
                        'metrics': metrics_data
                    })
                    
                    # Generate charts for geolocation if not already done
                    geo_id = server.get('geolocation_id')
                    if geo_id and geo_id not in geolocation_charts:
                        geo_name = next((g['name'] for g in geolocations if g['id'] == geo_id), f"Location {geo_id}")
                        
                        # Count servers in this geolocation
                        servers_count = sum(1 for s in servers if s.get('geolocation_id') == geo_id)
                        
                        # Generate charts
                        chart_generator = ChartGenerator()
                        latency_chart = chart_generator.generate_metrics_image(
                            metrics_data, 'latency', hours)
                        packet_loss_chart = chart_generator.generate_metrics_image(
                            metrics_data, 'packet_loss', hours)
                            
                        geolocation_charts[geo_id] = {
                            'geo_name': geo_name,
                            'servers_count': servers_count,
                            'latency_chart': latency_chart,
                            'packet_loss_chart': packet_loss_chart
                        }
                        
            except Exception as e:
                logger.exception(f"Error fetching metrics for server {server.get('id')}: {str(e)}")
    
    return render_template(
        'dashboard.html',
        servers=servers,
        geolocations=geolocations,
        all_metrics=all_metrics,
        geolocation_charts=geolocation_charts,
        current_hours=hours,
        now=datetime.now()
    )

# Server management routes
@app.route('/servers')
@login_required
def servers():
    # Initialize filter form
    filter_form = FilterForm()
    
    # Get query parameters for filtering
    search = request.args.get('search', '')
    geolocation = request.args.get('geolocation', 'all')
    status = request.args.get('status', 'all')
    view_mode = request.args.get('view', 'table')
    
    if USE_MOCK_DATA:
        # Use mock data for development
        geolocations = MOCK_GEOLOCATIONS
        
        # Update filter form choices
        filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
            (str(geo['id']), geo['name']) for geo in geolocations
        ]
        
        # Prepare filter params
        filters = {}
        if search:
            filters['search'] = search
        if geolocation != 'all':
            filters['geolocation_id'] = int(geolocation)
        if status != 'all':
            filters['status'] = status
            
        # Filter servers
        servers = filter_servers(filters)
    else:
        # Load geolocations for the filter dropdown from API
        try:
            geo_response = db_client.get('/api/geolocations')
            if geo_response.status_code == 200:
                geolocations = geo_response.json()
                filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
                    (str(geo['id']), geo['name']) for geo in geolocations
                ]
            else:
                filter_form.geolocation.choices = [('all', 'All Geolocations')]
                flash('Failed to load geolocation filter options', 'warning')
        except Exception as e:
            logger.exception(f"Error loading geolocations: {str(e)}")
            filter_form.geolocation.choices = [('all', 'All Geolocations')]
        
        # Prepare filter params for API request
        filter_params = {}
        if search:
            filter_params['search'] = search
        if geolocation != 'all':
            filter_params['geolocation_id'] = geolocation
        if status != 'all':
            filter_params['status'] = status

        # Fetch servers from API
        try:
            response = db_client.get('/api/servers', params=filter_params)
            if response.status_code == 200:
                servers = response.json()
            else:
                servers = []
                flash('Failed to fetch server list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching servers: {str(e)}")
            servers = []
            flash('Service unavailable', 'danger')
    
    # Calculate server stats
    stats = {
        'total': len(servers),
        'active': sum(1 for s in servers if s.get('status') == 'active'),
        'inactive': sum(1 for s in servers if s.get('status') == 'inactive'),
        'degraded': sum(1 for s in servers if s.get('status') == 'degraded')
    }
    
    return render_template(
        'servers/index.html',
        servers=servers,
        filter_form=filter_form,
        view_mode=view_mode,
        stats=stats,
        now=datetime.now()
    )

# Здесь должны быть другие маршруты вашего приложения...

# Добавьте другие маршруты и функции из вашего приложения...

# Точка входа для запуска приложения
if __name__ == '__main__':
    # Настраиваем режим отладки
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Запускаем приложение
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
@app.route('/servers/add', methods=['GET', 'POST'])
@login_required
def add_server():
    form = ServerForm()
    
    if USE_MOCK_DATA:
        # Use mock data for development
        form.geolocation_id.choices = [(g['id'], g['name']) for g in MOCK_GEOLOCATIONS if g.get('available', True)]
        
        if form.validate_on_submit():
            try:
                # Generate a new server ID (max ID + 1)
                new_id = max(s['id'] for s in MOCK_SERVERS) + 1
                
                # Create new server
                server = {
                    'id': new_id,
                    'name': form.name.data or f"Server {new_id}",
                    'endpoint': form.endpoint.data,
                    'port': form.port.data,
                    'address': form.address.data,
                    'public_key': form.public_key.data,
                    'geolocation_id': form.geolocation_id.data,
                    'geolocation_name': next((g['name'] for g in MOCK_GEOLOCATIONS if g['id'] == form.geolocation_id.data), "Unknown"),
                    'max_peers': form.max_peers.data,
                    'status': form.status.data,
                    'api_key': form.api_key.data or secrets.token_hex(16),
                    'api_url': form.api_url.data or f"http://{form.endpoint.data}:{form.port.data}/api"
                }
                
                # Add to the global mock data
                MOCK_SERVERS.append(server)
                
                flash(f"Server '{server.get('name')}' created successfully", 'success')
                return redirect(url_for('server_details', server_id=server.get('id')))
            except Exception as e:
                logger.exception(f"Error creating mock server: {str(e)}")
                flash('Error creating server', 'danger')
    else:
        # Load geolocation choices from API
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                geolocations = response.json()
                form.geolocation_id.choices = [(g['id'], g['name']) for g in geolocations if g.get('available', True)]
            else:
                flash('Failed to load geolocation options', 'warning')
                form.geolocation_id.choices = []
        except Exception as e:
            logger.exception(f"Error loading geolocations: {str(e)}")
            flash('Service unavailable', 'danger')
            form.geolocation_id.choices = []
        
        if form.validate_on_submit():
            try:
                # Prepare server data
                server_data = {
                    'name': form.name.data,
                    'endpoint': form.endpoint.data,
                    'port': form.port.data,
                    'address': form.address.data,
                    'public_key': form.public_key.data,
                    'geolocation_id': form.geolocation_id.data,
                    'max_peers': form.max_peers.data,
                    'status': form.status.data,
                    'api_key': form.api_key.data or secrets.token_hex(16),
                    'api_url': form.api_url.data or f"http://{form.endpoint.data}:{form.port.data}/api"
                }
                
                # Create server via API
                response = db_client.post('/api/servers', json=server_data)
                
                if response.status_code == 201:
                    server = response.json()
                    flash(f"Server '{server.get('name')}' created successfully", 'success')
                    return redirect(url_for('server_details', server_id=server.get('id')))
                else:
                    flash('Failed to create server', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error creating server: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template('servers/add.html', form=form, now=datetime.now())

@app.route('/servers/<int:server_id>')
@login_required
def server_details(server_id):
    hours = request.args.get('hours', 24, type=int)
    
    if USE_MOCK_DATA:
        # Use mock data for development
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers'))
            
        # Generate mock metrics
        metrics = generate_mock_metrics(server_id, hours)
        
        # Generate charts
        charts = {}
        if metrics and 'history' in metrics and metrics['history']:
            chart_generator = ChartGenerator()
            charts['latency'] = chart_generator.generate_metrics_image(metrics, 'latency', hours)
            charts['packet_loss'] = chart_generator.generate_metrics_image(metrics, 'packet_loss', hours)
            charts['resources'] = chart_generator.generate_metrics_image(metrics, 'resources', hours)
            
            # Generate interactive chart if plotly is available
            interactive_chart = chart_generator.generate_plotly_chart(metrics, 'server_detail')
        else:
            interactive_chart = None
    else:
        # Fetch server details from API
        try:
            response = db_client.get(f'/api/servers/{server_id}')
            if response.status_code == 200:
                server = response.json()
            else:
                flash('Server not found', 'danger')
                return redirect(url_for('servers'))
        except Exception as e:
            logger.exception(f"Error fetching server details: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('servers'))
        
        # Fetch metrics from API
        try:
            metrics_response = db_client.get(f'/api/servers/{server_id}/metrics', 
                                            params={'hours': hours})
            
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
            else:
                metrics = None
        except Exception as e:
            logger.exception(f"Error fetching server metrics: {str(e)}")
            metrics = None
        
        # Generate charts
        charts = {}
        chart_generator = ChartGenerator()
        if metrics and 'history' in metrics and metrics['history']:
            charts['latency'] = chart_generator.generate_metrics_image(metrics, 'latency', hours)
            charts['packet_loss'] = chart_generator.generate_metrics_image(metrics, 'packet_loss', hours)
            charts['resources'] = chart_generator.generate_metrics_image(metrics, 'resources', hours)
            
            # Generate interactive chart if plotly is available
            interactive_chart = chart_generator.generate_plotly_chart(metrics, 'server_detail')
        else:
            interactive_chart = None
    
    return render_template(
        'servers/details.html',
        server=server,
        metrics=metrics,
        charts=charts,
        interactive_chart=interactive_chart,
        hours=hours,
        now=datetime.now()
    )

@app.route('/servers/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):
    # Fetch server to edit
    if USE_MOCK_DATA:
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers'))
            
        form = ServerForm(obj=server)
        form.geolocation_id.choices = [(g['id'], g['name']) for g in MOCK_GEOLOCATIONS]
        
        if form.validate_on_submit():
            try:
                # Update server data
                for server_item in MOCK_SERVERS:
                    if server_item['id'] == server_id:
                        server_item.update({
                            'name': form.name.data,
                            'endpoint': form.endpoint.data,
                            'port': form.port.data,
                            'address': form.address.data,
                            'public_key': form.public_key.data,
                            'geolocation_id': form.geolocation_id.data,
                            'geolocation_name': next((g['name'] for g in MOCK_GEOLOCATIONS if g['id'] == form.geolocation_id.data), "Unknown"),
                            'max_peers': form.max_peers.data,
                            'status': form.status.data,
                            'api_key': form.api_key.data,
                            'api_url': form.api_url.data
                        })
                        break
                
                flash('Server updated successfully', 'success')
                return redirect(url_for('server_details', server_id=server_id))
            except Exception as e:
                logger.exception(f"Error updating mock server: {str(e)}")
                flash('Error updating server', 'danger')
    else:
        try:
            response = db_client.get(f'/api/servers/{server_id}')
            if response.status_code == 200:
                server = response.json()
            else:
                flash('Server not found', 'danger')
                return redirect(url_for('servers'))
        except Exception as e:
            logger.exception(f"Error fetching server: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('servers'))
        
        form = ServerForm(obj=server)
        
        # Load geolocation choices
        try:
            geo_response = db_client.get('/api/geolocations')
            if geo_response.status_code == 200:
                geolocations = geo_response.json()
                form.geolocation_id.choices = [(g['id'], g['name']) for g in geolocations]
            else:
                flash('Failed to load geolocation options', 'warning')
                form.geolocation_id.choices = [(server['geolocation_id'], 'Current Location')]
        except Exception as e:
            logger.exception(f"Error loading geolocations: {str(e)}")
            form.geolocation_id.choices = [(server['geolocation_id'], 'Current Location')]
        
        if form.validate_on_submit():
            try:
                # Prepare updated server data
                server_data = {
                    'name': form.name.data,
                    'endpoint': form.endpoint.data,
                    'port': form.port.data,
                    'address': form.address.data,
                    'public_key': form.public_key.data,
                    'geolocation_id': form.geolocation_id.data,
                    'max_peers': form.max_peers.data,
                    'status': form.status.data,
                    'api_key': form.api_key.data,
                    'api_url': form.api_url.data
                }
                
                # Update server via API
                response = db_client.put(f'/api/servers/{server_id}', json=server_data)
                
                if response.status_code == 200:
                    flash('Server updated successfully', 'success')
                    return redirect(url_for('server_details', server_id=server_id))
                else:
                    flash('Failed to update server', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error updating server: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template('servers/edit.html', form=form, server=server, now=datetime.now())

@app.route('/servers/<int:server_id>/delete')
@login_required
def delete_server(server_id):
    if USE_MOCK_DATA:
        # Find server in mock data
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers'))
            
        # Remove server from mock data
        global MOCK_SERVERS
        MOCK_SERVERS = [s for s in MOCK_SERVERS if s['id'] != server_id]
        
        flash('Server deleted successfully', 'success')
    else:
        try:
            response = db_client.delete(f'/api/servers/{server_id}')
            
            if response.status_code == 204:
                flash('Server deleted successfully', 'success')
            else:
                flash('Failed to delete server', 'danger')
                
        except Exception as e:
            logger.exception(f"Error deleting server: {str(e)}")
            flash('Service unavailable', 'danger')
    
    return redirect(url_for('servers'))

@app.route('/servers/<int:server_id>/action/<action>', methods=['POST'])
@login_required
def server_action(server_id, action):
    try:
        if USE_MOCK_DATA:
            server = find_server(server_id)
            if not server:
                flash('Server not found', 'danger')
                return redirect(url_for('servers'))
                
            if action == 'restart':
                flash('WireGuard service restarted successfully (mock)', 'success')
                
            elif action == 'toggle_status':
                # Toggle status in mock data
                for s in MOCK_SERVERS:
                    if s['id'] == server_id:
                        s['status'] = 'inactive' if s['status'] == 'active' else 'active'
                        status_text = 'activated' if s['status'] == 'active' else 'deactivated'
                        flash(f'Server {status_text} successfully', 'success')
                        break
            else:
                flash('Unknown action', 'danger')
        else:
            if action == 'restart':
                response = db_client.post(f'/api/servers/{server_id}/restart')
                if response.status_code == 200:
                    flash('WireGuard service restarted successfully', 'success')
                else:
                    flash('Failed to restart WireGuard service', 'danger')
                    
            elif action == 'toggle_status':
                # First get current status
                server_response = db_client.get(f'/api/servers/{server_id}')
                if server_response.status_code == 200:
                    server = server_response.json()
                    new_status = 'inactive' if server.get('status') == 'active' else 'active'
                    
                    # Update status
                    update_response = db_client.put(
                        f'/api/servers/{server_id}',
                        json={'status': new_status}
                    )
                    
                    if update_response.status_code == 200:
                        status_text = 'activated' if new_status == 'active' else 'deactivated'
                        flash(f'Server {status_text} successfully', 'success')
                    else:
                        flash('Failed to update server status', 'danger')
                else:
                    flash('Failed to get server information', 'danger')
            else:
                flash('Unknown action', 'danger')
                
    except Exception as e:
        logger.exception(f"Error performing server action: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('server_details', server_id=server_id))

# Geolocation management routes
@app.route('/geolocations')
@login_required
def geolocations():
    if USE_MOCK_DATA:
        # Use mock data for development
        geolocations = MOCK_GEOLOCATIONS.copy()
        servers = MOCK_SERVERS
            
        # Count servers per geolocation
        for geo in geolocations:
            geo['server_count'] = sum(1 for s in servers if s.get('geolocation_id') == geo['id'])
    else:
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                geolocations = response.json()
                
                # Get server counts for each geolocation
                server_response = db_client.get('/api/servers')
                if server_response.status_code == 200:
                    servers = server_response.json()
                    
                    # Count servers per geolocation
                    for geo in geolocations:
                        geo['server_count'] = sum(1 for s in servers if s.get('geolocation_id') == geo['id'])
                
            else:
                geolocations = []
                flash('Failed to fetch geolocation list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching geolocations: {str(e)}")
            geolocations = []
            flash('Service unavailable', 'danger')
    
    return render_template('geolocations/index.html', geolocations=geolocations, now=datetime.now())

@app.route('/geolocations/add', methods=['GET', 'POST'])
@login_required
def add_geolocation():
    form = GeolocationForm()
    
    if form.validate_on_submit():
        try:
            if USE_MOCK_DATA:
                # Generate a new ID for the mock geolocation
                new_id = max(g['id'] for g in MOCK_GEOLOCATIONS) + 1
                
                # Create new geolocation
                geo = {
                    'id': new_id,
                    'code': form.code.data.upper(),
                    'name': form.name.data,
                    'available': form.available.data,
                    'description': form.description.data
                }
                
                # Add to mock data
                MOCK_GEOLOCATIONS.append(geo)
                
                flash(f"Geolocation '{geo.get('name')}' created successfully", 'success')
                return redirect(url_for('geolocations'))
            else:
                # Prepare geolocation data
                geo_data = {
                    'code': form.code.data.upper(),
                    'name': form.name.data,
                    'available': form.available.data,
                    'description': form.description.data
                }
                
                # Create geolocation via API
                response = db_client.post('/api/geolocations', json=geo_data)
                
                if response.status_code == 201:
                    geo = response.json()
                    flash(f"Geolocation '{geo.get('name')}' created successfully", 'success')
                    return redirect(url_for('geolocations'))
                else:
                    flash('Failed to create geolocation', 'danger')
                    
        except Exception as e:
            logger.exception(f"Error creating geolocation: {str(e)}")
            flash('Service unavailable', 'danger')
    
    return render_template('geolocations/add.html', form=form, now=datetime.now())

@app.route('/geolocations/<int:geo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_geolocation(geo_id):
    # Fetch geolocation to edit
    if USE_MOCK_DATA:
        geolocation = find_geolocation(geo_id)
        if not geolocation:
            flash('Geolocation not found', 'danger')
            return redirect(url_for('geolocations'))
            
        # Count servers using this geolocation
        geo_servers = [s for s in MOCK_SERVERS if s.get('geolocation_id') == geo_id]
        server_count = len(geo_servers)
        
        form = GeolocationForm(obj=geolocation)
        
        if form.validate_on_submit():
            try:
                # Update geolocation in mock data
                for geo in MOCK_GEOLOCATIONS:
                    if geo['id'] == geo_id:
                        geo.update({
                            'code': form.code.data.upper(),
                            'name': form.name.data,
                            'available': form.available.data,
                            'description': form.description.data
                        })
                        break
                
                flash('Geolocation updated successfully', 'success')
                return redirect(url_for('geolocations'))
            except Exception as e:
                logger.exception(f"Error updating mock geolocation: {str(e)}")
                flash('Error updating geolocation', 'danger')
    else:
        try:
            response = db_client.get(f'/api/geolocations/{geo_id}')
            if response.status_code == 200:
                geolocation = response.json()
            else:
                flash('Geolocation not found', 'danger')
                return redirect(url_for('geolocations'))
        except Exception as e:
            logger.exception(f"Error fetching geolocation: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('geolocations'))
        
        form = GeolocationForm(obj=geolocation)
        
        # Count servers using this geolocation
        try:
            server_response = db_client.get('/api/servers')
            if server_response.status_code == 200:
                servers = server_response.json()
                server_count = sum(1 for s in servers if s.get('geolocation_id') == geo_id)
                geo_servers = [s for s in servers if s.get('geolocation_id') == geo_id]
            else:
                server_count = 0
                geo_servers = []
        except Exception as e:
            logger.exception(f"Error counting servers for geolocation: {str(e)}")
            server_count = 0
            geo_servers = []
        
        if form.validate_on_submit():
            try:
                # Prepare updated geolocation data
                geo_data = {
                    'code': form.code.data.upper(),
                    'name': form.name.data,
                    'available': form.available.data,
                    'description': form.description.data
                }
                
                # Update geolocation via API
                response = db_client.put(f'/api/geolocations/{geo_id}', json=geo_data)
                
                if response.status_code == 200:
                    flash('Geolocation updated successfully', 'success')
                    return redirect(url_for('geolocations'))
                else:
                    flash('Failed to update geolocation', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error updating geolocation: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template(
        'geolocations/edit.html', 
        form=form, 
        geolocation=geolocation, 
        server_count=server_count,
        servers=geo_servers,
        now=datetime.now()
    )

@app.route('/geolocations/<int:geo_id>/toggle')
@login_required
def toggle_geolocation(geo_id):
    try:
        if USE_MOCK_DATA:
            # Find geolocation in mock data
            geolocation = find_geolocation(geo_id)
            if not geolocation:
                flash('Geolocation not found', 'danger')
                return redirect(url_for('geolocations'))
                
            # Toggle availability
            for geo in MOCK_GEOLOCATIONS:
                if geo['id'] == geo_id:
                    geo['available'] = not geo.get('available', True)
                    status_text = 'enabled' if geo['available'] else 'disabled'
                    flash(f'Geolocation {status_text} successfully', 'success')
                    break
        else:
            # First get current status
            geo_response = db_client.get(f'/api/geolocations/{geo_id}')
            if geo_response.status_code == 200:
                geo = geo_response.json()
                
                # Toggle availability
                new_availability = not geo.get('available', True)
                
                # Update status
                update_response = db_client.put(
                    f'/api/geolocations/{geo_id}',
                    json={'available': new_availability}
                )
                
                if update_response.status_code == 200:
                    status_text = 'enabled' if new_availability else 'disabled'
                    flash(f'Geolocation {status_text} successfully', 'success')
                else:
                    flash('Failed to update geolocation status', 'danger')
            else:
                flash('Failed to get geolocation information', 'danger')
                
    except Exception as e:
        logger.exception(f"Error toggling geolocation: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('geolocations'))

@app.route('/geolocations/<int:geo_id>/delete')
@login_required
def delete_geolocation(geo_id):
    try:
        if USE_MOCK_DATA:
            # Check if any servers are using this geolocation
            if any(s.get('geolocation_id') == geo_id for s in MOCK_SERVERS):
                flash('Cannot delete geolocation with active servers', 'danger')
                return redirect(url_for('geolocations'))
                
            # Remove from mock data
            global MOCK_GEOLOCATIONS
            MOCK_GEOLOCATIONS = [g for g in MOCK_GEOLOCATIONS if g['id'] != geo_id]
            
            flash('Geolocation deleted successfully', 'success')
        else:
            # First check if any servers are using this geolocation
            server_response = db_client.get('/api/servers')
            if server_response.status_code == 200:
                servers = server_response.json()
                if any(s.get('geolocation_id') == geo_id for s in servers):
                    flash('Cannot delete geolocation with active servers', 'danger')
                    return redirect(url_for('geolocations'))
            
            # Delete geolocation
            response = db_client.delete(f'/api/geolocations/{geo_id}')
            
            if response.status_code == 204:
                flash('Geolocation deleted successfully', 'success')
            else:
                flash('Failed to delete geolocation', 'danger')
                
    except Exception as e:
        logger.exception(f"Error deleting geolocation: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('geolocations'))

# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    try:
        return render_template('errors/404.html', now=datetime.now()), 404
    except Exception as error:
        # Если шаблон не найден, возвращаем встроенный HTML
        logger.error(f"Error rendering 404 template: {str(error)}")
        error_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Page Not Found</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                h1 { color: #333; }
                .error-container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .back-link { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
                .back-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>404 - Page Not Found</h1>
                <p>The page you are looking for does not exist or has been moved.</p>
                <a href="/" class="back-link">Return to Home</a>
            </div>
        </body>
        </html>
        '''
        return error_html, 404

@app.errorhandler(500)
def server_error(e):
    try:
        return render_template('errors/500.html', now=datetime.now()), 500
    except Exception as error:
        # Если шаблон не найден, возвращаем встроенный HTML
        logger.error(f"Error rendering 500 template: {str(error)}")
        error_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>500 - Server Error</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                h1 { color: #333; }
                .error-container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .back-link { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
                .back-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>500 - Server Error</h1>
                <p>Sorry, something went wrong on our end. Please try again later.</p>
                <a href="/" class="back-link">Return to Home</a>
            </div>
        </body>
        </html>
        '''
        return error_html, 500

# Health check endpoint for container orchestration
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "version": "1.0.0"}), 200



# Создаем базовый шаблон для страниц ошибок
def create_error_templates():
    # Создаем директории для шаблонов
    templates_dir = os.path.join(os.getcwd(), 'templates')
    errors_dir = os.path.join(templates_dir, 'errors')
    
    # Проверяем существование директорий и создаем их при необходимости
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    if not os.path.exists(errors_dir):
        os.makedirs(errors_dir)
    
    # Создаем шаблон 404.html
    error_404_path = os.path.join(errors_dir, '404.html')
    if not os.path.exists(error_404_path):
        with open(error_404_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <link rel="stylesheet" href="/static/css/bootstrap.min.css">
    <style>
        body { 
            padding-top: 50px; 
            padding-bottom: 50px; 
            background-color: #f8f9fa;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .error-code {
            font-size: 120px;
            color: #dc3545;
            margin-bottom: 0;
        }
        .error-message {
            font-size: 24px;
            margin-bottom: 20px;
            color: #343a40;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-container">
            <h1 class="error-code">404</h1>
            <p class="error-message">Page Not Found</p>
            <p class="lead">The page you are looking for does not exist or has been moved.</p>
            <a href="/" class="btn btn-primary">Return to Home</a>
        </div>
    </div>
    <script src="/static/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''')
    
    # Создаем шаблон 500.html
    error_500_path = os.path.join(errors_dir, '500.html')
    if not os.path.exists(error_500_path):
        with open(error_500_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>500 - Server Error</title>
    <link rel="stylesheet" href="/static/css/bootstrap.min.css">
    <style>
        body { 
            padding-top: 50px; 
            padding-bottom: 50px; 
            background-color: #f8f9fa;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .error-code {
            font-size: 120px;
            color: #dc3545;
            margin-bottom: 0;
        }
        .error-message {
            font-size: 24px;
            margin-bottom: 20px;
            color: #343a40;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-container">
            <h1 class="error-code">500</h1>
            <p class="error-message">Server Error</p>
            <p class="lead">Sorry, something went wrong on our end. Please try again later.</p>
            <a href="/" class="btn btn-primary">Return to Home</a>
        </div>
    </div>
    <script src="/static/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''')

# Создаем простую иконку favicon.ico
def create_favicon():
    static_img_dir = os.path.join(os.getcwd(), 'static', 'img')
    
    # Проверяем существование директории и создаем ее при необходимости
    if not os.path.exists(static_img_dir):
        os.makedirs(static_img_dir)
    
    # Создаем простой favicon.ico (пустой 16x16 px ico-файл)
    favicon_path = os.path.join(static_img_dir, 'favicon.ico')
    if not os.path.exists(favicon_path):
        # Минимальный ICO-файл (16x16 px)
        minimal_ico = bytes([
            0, 0, 1, 0, 1, 0, 16, 16, 0, 0, 1, 0, 32, 0, 68, 4, 
            0, 0, 22, 0, 0, 0, 40, 0, 0, 0, 16, 0, 0, 0, 32, 0, 
            0, 0, 1, 0, 32, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        ] + [0] * 1024)  # Заполняем остаток нулями (прозрачный пиксель)
        
        with open(favicon_path, 'wb') as f:
            f.write(minimal_ico)

# Функция для вставки в app.py, чтобы создавать все необходимые директории и файлы
def setup_directories_and_files():
    # Создаем статические директории
    static_dirs = ['css', 'js', 'img', 'errors']
    for static_dir in static_dirs:
        dir_path = os.path.join(os.getcwd(), 'static', static_dir)
        os.makedirs(dir_path, exist_ok=True)
    
    # Создаем шаблоны для ошибок
    create_error_templates()
    
    # Создаем favicon
    create_favicon()






if __name__ == '__main__':
    # Настраиваем режим отладки
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Запускаем приложение
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

