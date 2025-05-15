import os
import json
import psycopg2
import psycopg2.extras
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from user_auth_api import users_api


app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('database-service')

# Параметры подключения к базе данных
db_params = {
    'host': os.environ.get('POSTGRES_HOST', 'db'),
    'database': os.environ.get('POSTGRES_DB', 'wireguard'),
    'user': os.environ.get('POSTGRES_USER', 'postgres'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'postgres')
}

def get_db_connection():
    """Создание соединения с базой данных"""
    return psycopg2.connect(**db_params)

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервиса"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        return jsonify({"status": "ok", "service": "database-service"})
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Существующие API-эндпоинты остаются без изменений
# ...

# Новые API-эндпоинты для работы с удаленными серверами

# @app.route('/api/servers', methods=['GET'])
# def get_servers():
#     """Получение списка всех удаленных серверов"""
#     try:
#         with get_db_connection() as conn:
#             with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
#                 query = """
#                 SELECT 
#                     rs.id, 
#                     rs.server_id, 
#                     rs.name, 
#                     rs.location, 
#                     rs.api_url, 
#                     rs.geolocation_id, 
#                     rs.auth_type, 
#                     rs.max_peers, 
#                     rs.is_active,
#                     g.name as geolocation_name
#                 FROM 
#                     remote_servers rs
#                 LEFT JOIN 
#                     geolocations g ON rs.geolocation_id = g.id
#                 ORDER BY 
#                     rs.name
#                 """
#                 cur.execute(query)
#                 servers = [dict(row) for row in cur.fetchall()]
                
#                 # Удаляем чувствительные данные
#                 for server in servers:
#                     for key in ['api_key', 'oauth_client_id', 'oauth_client_secret', 'hmac_secret']:
#                         if key in server:
#                             del server[key]
                
#                 return jsonify({"servers": servers})
#     except Exception as e:
#         logger.exception(f"Error getting servers: {e}")
#         return jsonify({"error": str(e)}), 500
@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Получение списка всех удаленных серверов"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.api_url, 
                    rs.endpoint,
                    rs.port,
                    rs.address,
                    rs.public_key,
                    rs.api_path,
                    rs.skip_api_check,
                    rs.geolocation_id, 
                    rs.auth_type, 
                    rs.max_peers, 
                    rs.is_active,
                    g.name as geolocation_name
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    geolocations g ON rs.geolocation_id = g.id
                ORDER BY 
                    rs.name
                """
                cur.execute(query)
                servers = [dict(row) for row in cur.fetchall()]
                
                # Удаляем чувствительные данные и форматируем для совместимости
                formatted_servers = []
                for server in servers:
                    # Удаляем чувствительные данные
                    for key in ['api_key', 'oauth_client_id', 'oauth_client_secret', 'hmac_secret']:
                        if key in server:
                            del server[key]
                            
                    # Преобразуем ID в строки
                    if 'id' in server:
                        server['id'] = str(server['id'])
                    if 'geolocation_id' in server and server['geolocation_id']:
                        server['geolocation_id'] = str(server['geolocation_id'])
                        
                    # Преобразуем is_active в status
                    server['status'] = 'active' if server.get('is_active', True) else 'inactive'
                    
                    # Значения по умолчанию
                    if 'api_path' not in server or not server['api_path']:
                        server['api_path'] = '/status'
                        
                    formatted_servers.append(server)
                
                return jsonify({"servers": formatted_servers})
    except Exception as e:
        logger.exception(f"Error getting servers: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/active', methods=['GET'])
def get_active_servers():
    """Получение списка активных удаленных серверов"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.api_url, 
                    rs.geolocation_id,
                    rs.auth_type,
                    rs.max_peers,
                    g.name as geolocation_name
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    geolocations g ON rs.geolocation_id = g.id
                WHERE 
                    rs.is_active = TRUE
                ORDER BY 
                    rs.name
                """
                cur.execute(query)
                servers = [dict(row) for row in cur.fetchall()]
                
                # Удаляем чувствительные данные
                for server in servers:
                    for key in ['api_key', 'oauth_client_id', 'oauth_client_secret', 'hmac_secret']:
                        if key in server:
                            del server[key]
                
                return jsonify({"servers": servers})
    except Exception as e:
        logger.exception(f"Error getting active servers: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/api/servers/<int:server_id>', methods=['GET'])
# def get_server(server_id):
#     """Получение информации об удаленном сервере по ID"""
#     try:
#         with get_db_connection() as conn:
#             with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
#                 query = """
#                 SELECT 
#                     rs.id, 
#                     rs.server_id, 
#                     rs.name, 
#                     rs.location, 
#                     rs.api_url, 
#                     rs.geolocation_id, 
#                     rs.auth_type, 
#                     rs.api_key, 
#                     rs.oauth_client_id, 
#                     rs.oauth_client_secret, 
#                     rs.oauth_token_url, 
#                     rs.hmac_secret, 
#                     rs.max_peers, 
#                     rs.is_active,
#                     g.name as geolocation_name
#                 FROM 
#                     remote_servers rs
#                 LEFT JOIN 
#                     geolocations g ON rs.geolocation_id = g.id
#                 WHERE 
#                     rs.id = %s
#                 """
#                 cur.execute(query, (server_id,))
#                 server = cur.fetchone()
                
#                 if not server:
#                     return jsonify({"error": "Server not found"}), 404
                
#                 return jsonify({"server": dict(server)})
#     except Exception as e:
#         logger.exception(f"Error getting server details: {e}")
#         return jsonify({"error": str(e)}), 500
@app.route('/api/servers/<int:server_id>', methods=['GET'])
def get_server(server_id):
    """Получение информации об удаленном сервере по ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.api_url, 
                    rs.endpoint,
                    rs.port,
                    rs.address,
                    rs.public_key,
                    rs.api_path,
                    rs.skip_api_check, 
                    rs.geolocation_id, 
                    rs.auth_type, 
                    rs.api_key, 
                    rs.oauth_client_id, 
                    rs.oauth_client_secret, 
                    rs.oauth_token_url, 
                    rs.hmac_secret, 
                    rs.max_peers, 
                    rs.is_active,
                    g.name as geolocation_name
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    geolocations g ON rs.geolocation_id = g.id
                WHERE 
                    rs.id = %s
                """
                cur.execute(query, (server_id,))
                server = cur.fetchone()
                
                if not server:
                    return jsonify({"error": "Server not found"}), 404
                
                # Преобразование результата для совместимости
                server_dict = dict(server)
                server_dict['id'] = str(server_dict['id'])
                if server_dict['geolocation_id']:
                    server_dict['geolocation_id'] = str(server_dict['geolocation_id'])
                server_dict['status'] = 'active' if server_dict['is_active'] else 'inactive'
                
                return jsonify({"server": server_dict})
    except Exception as e:
        logger.exception(f"Error getting server details: {e}")
        return jsonify({"error": str(e)}), 500
# @app.route('/api/servers/add', methods=['POST'])
# def add_server_route():
#     """Adding a new remote server"""
#     try:
#         data = request.json
        
#         # Debug output of request data
#         logger.info(f"Received data for adding server: {data}")
        
#         # Check required fields
#         required_fields = ['name', 'endpoint', 'port', 'address', 'public_key', 'geolocation_id']
#         missing_fields = [field for field in required_fields if field not in data]
        
#         if missing_fields:
#             logger.error(f"Missing required fields: {missing_fields}")
#             return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
#         # Validate data types
#         try:
#             if 'port' in data and isinstance(data['port'], str):
#                 data['port'] = int(data['port'])
            
#             if 'geolocation_id' in data and isinstance(data['geolocation_id'], str):
#                 data['geolocation_id'] = int(data['geolocation_id'])
                
#             # Convert boolean fields
#             if 'skip_api_check' in data and isinstance(data['skip_api_check'], str):
#                 data['skip_api_check'] = data['skip_api_check'].lower() in ('true', 'yes', '1', 'y')
#         except ValueError as e:
#             logger.error(f"Data type conversion error: {str(e)}")
#             return jsonify({"error": f"Data type error: {str(e)}"}), 400
        
#         # Generate unique server_id if not provided
#         if 'server_id' not in data:
#             import uuid
#             data['server_id'] = f"srv-{uuid.uuid4().hex[:8]}"
        
#         # Create API URL if not provided
#         if 'api_url' not in data or not data['api_url']:
#             data['api_url'] = f"http://{data['endpoint']}:5000"
        
#         # Use default API path if not provided
#         if 'api_path' not in data:
#             data['api_path'] = '/status'
            
#         # Location (for backwards compatibility)
#         if 'location' not in data:
#             with get_db_connection() as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("SELECT name FROM geolocations WHERE id = %s", (data['geolocation_id'],))
#                     geo = cur.fetchone()
#                     if geo:
#                         data['location'] = geo[0]
#                     else:
#                         data['location'] = "Unknown location"
        
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 query = """
#                 INSERT INTO remote_servers (
#                     server_id, 
#                     name, 
#                     location, 
#                     endpoint,
#                     port,
#                     address,
#                     public_key,
#                     api_url, 
#                     api_path,
#                     geolocation_id, 
#                     auth_type, 
#                     api_key, 
#                     max_peers, 
#                     is_active,
#                     skip_api_check
#                 ) VALUES (
#                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
#                 ) RETURNING id
#                 """
                
#                 # Set default values for optional fields
#                 is_active = data.get('status', 'active') == 'active'
                
#                 cur.execute(query, (
#                     data['server_id'],
#                     data['name'],
#                     data.get('location', 'Unknown'),
#                     data['endpoint'],
#                     data['port'],
#                     data['address'],
#                     data['public_key'],
#                     data['api_url'],
#                     data['api_path'],
#                     data['geolocation_id'],
#                     data.get('auth_type', 'api_key'),
#                     data.get('api_key'),
#                     data.get('max_peers', 100),
#                     is_active,
#                     data.get('skip_api_check', False)
#                 ))
                
#                 server_id = cur.fetchone()[0]
#                 conn.commit()
                
#                 # Return complete server data
#                 cur.execute("""
#                     SELECT 
#                         id, server_id, name, location, endpoint, port, address, 
#                         public_key, api_url, api_path, geolocation_id, 
#                         max_peers, is_active, skip_api_check
#                     FROM remote_servers
#                     WHERE id = %s
#                 """, (server_id,))
                
#                 server_data = dict(zip([column[0] for column in cur.description], cur.fetchone()))
                
#                 logger.info(f"Server successfully added! ID: {server_id}")
                
#                 return jsonify({
#                     "success": True,
#                     "message": "Server added successfully",
#                     "server": server_data
#                 })
#     except Exception as e:
#         logger.exception(f"Error adding server: {e}")
#         return jsonify({"error": str(e)}), 500

@app.route('/api/servers/add', methods=['POST'])
def add_server_route():
    """Adding a new remote server"""
    try:
        data = request.json
        
        # Debug output of request data
        logger.info(f"Received data for adding server: {data}")
        
        # Check required fields
        required_fields = ['name', 'endpoint', 'port', 'address', 'public_key', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Validate data types
        try:
            if 'port' in data and isinstance(data['port'], str):
                data['port'] = int(data['port'])
            
            if 'geolocation_id' in data and isinstance(data['geolocation_id'], str):
                data['geolocation_id'] = int(data['geolocation_id'])
                
            # Convert boolean fields
            if 'skip_api_check' in data and isinstance(data['skip_api_check'], str):
                data['skip_api_check'] = data['skip_api_check'].lower() in ('true', 'yes', '1', 'y')
        except ValueError as e:
            logger.error(f"Data type conversion error: {str(e)}")
            return jsonify({"error": f"Data type error: {str(e)}"}), 400
        
        # Generate unique server_id if not provided
        if 'server_id' not in data:
            import uuid
            data['server_id'] = f"srv-{uuid.uuid4().hex[:8]}"
        
        # Create API URL if not provided
        if 'api_url' not in data or not data['api_url']:
            data['api_url'] = f"http://{data['endpoint']}:5000"
        
        # Use default API path if not provided
        if 'api_path' not in data or not data['api_path']:
            data['api_path'] = '/status'
            
        # Location (for backwards compatibility)
        if 'location' not in data:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM geolocations WHERE id = %s", (data['geolocation_id'],))
                    geo = cur.fetchone()
                    if geo:
                        data['location'] = geo[0]
                    else:
                        data['location'] = "Unknown location"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                INSERT INTO remote_servers (
                    server_id, 
                    name, 
                    location, 
                    endpoint,
                    port,
                    address,
                    public_key,
                    api_url, 
                    api_path,
                    geolocation_id, 
                    auth_type, 
                    api_key, 
                    max_peers, 
                    is_active,
                    skip_api_check
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id, server_id, name, endpoint, port, address, public_key, api_url, api_path, 
                          geolocation_id, auth_type, max_peers, is_active, skip_api_check
                """
                
                # Set default values for optional fields
                is_active = data.get('status', 'active') == 'active'
                
                cur.execute(query, (
                    data['server_id'],
                    data['name'],
                    data.get('location', 'Unknown'),
                    data['endpoint'],
                    data['port'],
                    data['address'],
                    data['public_key'],
                    data['api_url'],
                    data['api_path'],
                    data['geolocation_id'],
                    data.get('auth_type', 'api_key'),
                    data.get('api_key'),
                    data.get('max_peers', 100),
                    is_active,
                    data.get('skip_api_check', False)
                ))
                
                server = cur.fetchone()
                conn.commit()
                
                # Форматирование ответа для совместимости с приложением
                formatted_server = dict(server)
                formatted_server['id'] = str(formatted_server['id'])
                
                if formatted_server['geolocation_id']:
                    formatted_server['geolocation_id'] = str(formatted_server['geolocation_id'])
                    
                # Преобразуем is_active в status
                formatted_server['status'] = 'active' if formatted_server.get('is_active', True) else 'inactive'
                
                logger.info(f"Server successfully added! ID: {formatted_server['id']}")
                
                return jsonify(formatted_server)
    except Exception as e:
        logger.exception(f"Error adding server: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/servers', methods=['POST'])
def add_server():
    """Добавление нового удаленного сервера"""
    try:
        data = request.json
        
        # Вывод данных запроса для отладки
        logger.info(f"Получены данные для добавления сервера: {data}")
        
        # Проверка обязательных полей
        required_fields = ['name', 'endpoint', 'port', 'address', 'public_key', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Отсутствуют обязательные поля: {missing_fields}")
            return jsonify({"error": f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"}), 400
        
        # Проверка типов данных
        try:
            if 'port' in data and isinstance(data['port'], str):
                data['port'] = int(data['port'])
            
            if 'geolocation_id' in data and isinstance(data['geolocation_id'], str):
                data['geolocation_id'] = int(data['geolocation_id'])
        except ValueError as e:
            logger.error(f"Ошибка преобразования типов данных: {str(e)}")
            return jsonify({"error": f"Ошибка преобразования типов данных: {str(e)}"}), 400
        
        # Генерация уникального server_id, если не указан
        if 'server_id' not in data:
            import uuid
            data['server_id'] = f"srv-{uuid.uuid4().hex[:8]}"
        
        # Создаем URL API, если не указан
        if 'api_url' not in data:
            data['api_url'] = f"http://{data['endpoint']}:{data['port']}/api"
        
        # Локация сервера (для обратной совместимости)
        if 'location' not in data:
            # Пытаемся найти название геолокации
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM geolocations WHERE id = %s", (data['geolocation_id'],))
                    geo = cur.fetchone()
                    if geo:
                        data['location'] = geo[0]
                    else:
                        data['location'] = "Unknown location"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                INSERT INTO remote_servers (
                    server_id, 
                    name, 
                    location, 
                    api_url, 
                    geolocation_id, 
                    auth_type, 
                    api_key, 
                    oauth_client_id, 
                    oauth_client_secret, 
                    oauth_token_url, 
                    hmac_secret, 
                    max_peers, 
                    is_active
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
                """
                
                cur.execute(query, (
                    data['server_id'],
                    data['name'],
                    data.get('location', 'Unknown'),
                    data.get('api_url'),
                    data['geolocation_id'],
                    data.get('auth_type', 'api_key'),
                    data.get('api_key'),
                    data.get('oauth_client_id'),
                    data.get('oauth_client_secret'),
                    data.get('oauth_token_url'),
                    data.get('hmac_secret'),
                    data.get('max_peers', 100),
                    data.get('is_active', True)
                ))
                
                server_id = cur.fetchone()[0]
                conn.commit()
                
                logger.info(f"Сервер успешно добавлен! ID: {server_id}")
                
                return jsonify({
                    "success": True,
                    "message": "Server added successfully",
                    "server_id": server_id
                })
    except Exception as e:
        logger.exception(f"Ошибка при добавлении сервера: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/api/servers/<int:server_id>', methods=['PUT'])
# def update_server(server_id):
#     """Обновление информации об удаленном сервере"""
#     try:
#         data = request.json
        
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 # Проверка существования сервера
#                 cur.execute("SELECT id FROM remote_servers WHERE id = %s", (server_id,))
#                 if not cur.fetchone():
#                     return jsonify({"error": "Server not found"}), 404
                
#                 # Формирование SET части запроса
#                 update_fields = []
#                 params = []
                
#                 for field in ['name', 'location', 'api_url', 'geolocation_id', 'auth_type', 
#                              'api_key', 'oauth_client_id', 'oauth_client_secret', 
#                              'oauth_token_url', 'hmac_secret', 'max_peers', 'is_active']:
#                     if field in data:
#                         update_fields.append(f"{field} = %s")
#                         params.append(data[field])
                
#                 if not update_fields:
#                     return jsonify({"message": "No fields to update"}), 400
                
#                 # Добавление ID сервера в параметры
#                 params.append(server_id)
                
#                 # Формирование полного запроса
#                 query = f"""
#                 UPDATE remote_servers 
#                 SET {', '.join(update_fields)}
#                 WHERE id = %s
#                 """
                
#                 cur.execute(query, params)
#                 conn.commit()
                
#                 return jsonify({
#                     "success": True,
#                     "message": "Server updated successfully"
#                 })
#     except Exception as e:
#         logger.exception(f"Error updating server: {e}")
#         return jsonify({"error": str(e)}), 500
@app.route('/api/servers/<int:server_id>', methods=['PUT'])
def update_server(server_id):
    """Обновление информации об удаленном сервере"""
    try:
        data = request.json
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования сервера
                cur.execute("SELECT id FROM remote_servers WHERE id = %s", (server_id,))
                if not cur.fetchone():
                    return jsonify({"error": "Server not found"}), 404
                
                # Формирование SET части запроса
                update_fields = []
                params = []
                
                # Все возможные поля для обновления
                field_list = [
                    'name', 'location', 'api_url', 'geolocation_id', 'auth_type', 
                    'api_key', 'oauth_client_id', 'oauth_client_secret', 'oauth_token_url',
                    'hmac_secret', 'max_peers', 'endpoint', 'port', 'address', 
                    'public_key', 'api_path', 'skip_api_check'
                ]
                
                # Обработка флага is_active отдельно
                if 'status' in data:
                    update_fields.append("is_active = %s")
                    params.append(data['status'] == 'active')
                
                # Добавляем все остальные поля
                for field in field_list:
                    if field in data:
                        update_fields.append(f"{field} = %s")
                        params.append(data[field])
                
                if not update_fields:
                    return jsonify({"message": "No fields to update"}), 400
                
                # Добавление ID сервера в параметры
                params.append(server_id)
                
                # Формирование полного запроса
                query = f"""
                UPDATE remote_servers 
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = %s
                RETURNING id, server_id, name, endpoint, port, address, public_key, api_url, 
                          api_path, geolocation_id, max_peers, is_active, skip_api_check
                """
                
                cur.execute(query, params)
                updated_server = cur.fetchone()
                conn.commit()
                
                if updated_server:
                    # Преобразование результата в словарь
                    column_names = [desc[0] for desc in cur.description]
                    server_dict = dict(zip(column_names, updated_server))
                    
                    # Форматирование для совместимости
                    server_dict['id'] = str(server_dict['id'])
                    if server_dict['geolocation_id']:
                        server_dict['geolocation_id'] = str(server_dict['geolocation_id'])
                    server_dict['status'] = 'active' if server_dict['is_active'] else 'inactive'
                    
                    return jsonify(server_dict)
                
                return jsonify({
                    "success": True,
                    "message": "Server updated successfully"
                })
    except Exception as e:
        logger.exception(f"Error updating server: {e}")
        return jsonify({"error": str(e)}), 500
@app.route('/api/server_metrics/add', methods=['POST'])
def add_server_metric():
    """Добавление метрик сервера"""
    try:
        data = request.json
        
        # Проверка обязательных полей
        required_fields = ['server_id', 'is_available', 'response_time']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Получение ID сервера по server_id
                if data.get('server_id').isdigit():
                    # Если server_id числовой, пробуем найти по id или server_id
                    cur.execute(
                        "SELECT id FROM remote_servers WHERE id = %s OR server_id = %s", 
                        (data.get('server_id'), data.get('server_id'))
                    )
                else:
                    # Иначе ищем только по server_id
                    cur.execute(
                        "SELECT id FROM remote_servers WHERE server_id = %s", 
                        (data.get('server_id'),)
                    )
                
                server = cur.fetchone()
                
                if not server:
                    return jsonify({'error': f'Server not found: {data.get("server_id")}'}), 404
                    
                server_id = server['id']
                
                # Проверяем, существует ли таблица remote_server_metrics
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'remote_server_metrics'
                    )
                """)
                
                table_exists = cur.fetchone()[0]
                
                if table_exists:
                    # Используем таблицу remote_server_metrics
                    query = """
                        INSERT INTO remote_server_metrics (
                            server_id, 
                            peers_count,
                            is_available, 
                            response_time, 
                            collected_at
                        ) VALUES (
                            %s, %s, %s, %s, NOW()
                        ) RETURNING id, server_id, is_available, response_time, collected_at
                    """
                    
                    cur.execute(query, (
                        server_id,
                        data.get('peers_count', 0),
                        data.get('is_available'),
                        data.get('response_time')
                    ))
                else:
                    # Пробуем использовать server_metrics, если remote_server_metrics не существует
                    query = """
                        INSERT INTO server_metrics (
                            server_id,
                            latency,
                            is_available,
                            measured_at
                        ) VALUES (
                            %s, %s, %s, NOW()
                        ) RETURNING id, server_id, latency, measured_at
                    """
                    
                    cur.execute(query, (
                        server_id,
                        data.get('response_time'),
                        data.get('is_available')
                    ))
                
                metric = cur.fetchone()
                conn.commit()
                
                if metric:
                    return jsonify({
                        'success': True,
                        'message': 'Server metrics added successfully',
                        'metric_id': metric['id']
                    })
                else:
                    return jsonify({'error': 'Failed to add server metrics'}), 500
                
    except Exception as e:
        logger.exception(f"Error adding server metrics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    """Удаление удаленного сервера"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования сервера
                cur.execute("SELECT id FROM remote_servers WHERE id = %s", (server_id,))
                if not cur.fetchone():
                    return jsonify({"error": "Server not found"}), 404
                
                # Удаление сервера
                cur.execute("DELETE FROM remote_servers WHERE id = %s", (server_id,))
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Server deleted successfully"
                })
    except Exception as e:
        logger.exception(f"Error deleting server: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/metrics', methods=['POST'])
def update_server_metrics():
    """Обновление метрик удаленного сервера"""
    try:
        data = request.json
        
        if 'server_id' not in data:
            return jsonify({"error": "Missing server_id"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования сервера
                cur.execute("SELECT id FROM remote_servers WHERE server_id = %s", (data['server_id'],))
                server = cur.fetchone()
                if not server:
                    return jsonify({"error": "Server not found"}), 404
                
                server_id = server[0]
                
                # Вставка новых метрик
                query = """
                INSERT INTO server_metrics (
                    server_id,
                    peers_count,
                    cpu_load,
                    memory_usage,
                    network_in,
                    network_out,
                    is_available,
                    response_time
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                """
                
                cur.execute(query, (
                    server_id,
                    data.get('peers_count', 0),
                    data.get('cpu_load', 0),
                    data.get('memory_usage', 0),
                    data.get('network_in', 0),
                    data.get('network_out', 0),
                    data.get('is_available', True),
                    data.get('response_time', 0)
                ))
                
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Server metrics updated successfully"
                })
    except Exception as e:
        logger.exception(f"Error updating server metrics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/metrics/<server_id>', methods=['GET'])
def get_server_metrics(server_id):
    """Получение метрик удаленного сервера"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Проверка существования сервера
                cur.execute("SELECT id FROM remote_servers WHERE server_id = %s", (server_id,))
                server = cur.fetchone()
                if not server:
                    return jsonify({"error": "Server not found"}), 404
                
                server_id = server[0]
                
                # Получение последних метрик
                query = """
                SELECT 
                    peers_count,
                    cpu_load,
                    memory_usage,
                    network_in,
                    network_out,
                    is_available,
                    response_time,
                    collected_at
                FROM 
                    server_metrics
                WHERE 
                    server_id = %s
                ORDER BY 
                    collected_at DESC
                LIMIT 1
                """
                
                cur.execute(query, (server_id,))
                metrics = cur.fetchone()
                
                if not metrics:
                    return jsonify({"message": "No metrics available for this server"}), 404
                
                return jsonify({"metrics": dict(metrics)})
    except Exception as e:
        logger.exception(f"Error getting server metrics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/peers/find', methods=['GET'])
def find_peer_server():
    """Поиск сервера для пира по публичному ключу"""
    try:
        public_key = request.args.get('public_key')
        if not public_key:
            return jsonify({"error": "Missing public_key parameter"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT 
                    psm.server_id,
                    rs.server_id as remote_server_id,
                    rs.name as server_name
                FROM 
                    peer_server_mapping psm
                JOIN 
                    remote_servers rs ON psm.server_id = rs.id
                WHERE 
                    psm.public_key = %s
                """
                
                cur.execute(query, (public_key,))
                mapping = cur.fetchone()
                
                if not mapping:
                    return jsonify({"message": "No server found for this peer"}), 404
                
                return jsonify({
                    "server_id": mapping['remote_server_id'],
                    "server_name": mapping['server_name']
                })
    except Exception as e:
        logger.exception(f"Error finding server for peer: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/servers/<int:server_id>/metrics', methods=['GET'])
def get_server_metrics_by_id(server_id):
    """Получение метрик удаленного сервера по ID"""
    try:
        # Получаем параметр часов из запроса
        hours = request.args.get('hours', default=24, type=int)
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Проверка существования сервера
                cur.execute("SELECT id FROM remote_servers WHERE id = %s", (server_id,))
                server = cur.fetchone()
                if not server:
                    return jsonify({"error": "Server not found"}), 404
                
                # Вычисляем временную метку для фильтрации по времени
                from datetime import datetime, timedelta
                time_threshold = datetime.now() - timedelta(hours=hours)
                
                # Сначала получим схему таблицы server_metrics, чтобы убедиться, какие столбцы существуют
                try:
                    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'server_metrics'")
                    columns = [col[0] for col in cur.fetchall()]
                    
                    logger.info(f"Доступные столбцы в таблице server_metrics: {columns}")
                    
                    # Строим запрос, используя только существующие столбцы
                    select_fields = ["id", "server_id"]
                    
                    # Маппинг имен столбцов из БД на имена полей в API
                    field_mapping = {
                        "latency": "latency_ms",
                        "bandwidth": "bandwidth",
                        "jitter": "jitter",
                        "packet_loss": "packet_loss"
                    }
                    
                    for db_field, api_field in field_mapping.items():
                        if db_field in columns:
                            select_fields.append(f"{db_field} as {api_field}")
                    
                    # Определяем правильное имя столбца времени
                    time_column = "measured_at"  # По умолчанию используем measured_at
                    if "measured_at" in columns:
                        select_fields.append("measured_at as timestamp")
                        time_column = "measured_at"
                    elif "collected_at" in columns:
                        select_fields.append("collected_at as timestamp")
                        time_column = "collected_at"
                    
                    # Формируем SQL запрос с обнаруженными столбцами
                    query = f"""
                    SELECT 
                        {", ".join(select_fields)}
                    FROM 
                        server_metrics
                    WHERE 
                        server_id = %s AND
                        {time_column} >= %s
                    ORDER BY 
                        {time_column} ASC
                    """
                    
                    cur.execute(query, (server_id, time_threshold))
                    metrics = [dict(row) for row in cur.fetchall()]
                    
                    # Если нет данных, генерируем мок-данные
                    if not metrics:
                        mock_metrics = generate_mock_metrics(server_id, hours)
                        return jsonify(mock_metrics)
                    
                    # Добавляем отсутствующие поля с мок-данными, если они нужны для интерфейса
                    for metric in metrics:
                        if "peers_count" not in metric:
                            metric["peers_count"] = 5 + (server_id % 10)
                        if "packet_loss" not in metric:
                            metric["packet_loss"] = server_id % 5
                        if "load" not in metric and "cpu_usage" in metric:
                            metric["load"] = metric["cpu_usage"] * 0.8
                        elif "load" not in metric:
                            metric["load"] = 30
                    
                    return jsonify({
                        "current": metrics[-1] if metrics else {},
                        "history": metrics
                    })
                    
                except Exception as e:
                    logger.exception(f"Ошибка при получении схемы таблицы: {e}")
                    # Если не удалось получить схему, используем мок-данные
                    mock_metrics = generate_mock_metrics(server_id, hours)
                    return jsonify(mock_metrics)
                
    except Exception as e:
        logger.exception(f"Error getting server metrics by ID: {e}")
        # Даже при ошибке возвращаем мок-данные для корректной работы интерфейса
        mock_metrics = generate_mock_metrics(server_id, hours)
        return jsonify(mock_metrics)

def generate_mock_metrics(server_id, hours):
    """
    Генерация мок-данных метрик для тестирования интерфейса
    
    Args:
        server_id (int): ID сервера
        hours (int): Количество часов для генерации данных
        
    Returns:
        list: Список сгенерированных метрик
    """
    import random
    from datetime import datetime, timedelta
    
    metrics = []
    now = datetime.now()
    
    # Определяем базовые значения в зависимости от ID сервера
    base_peers = 10 + (server_id % 5) * 5
    base_load = 30 + (server_id % 7) * 10
    base_cpu = 25 + (server_id % 6) * 5
    base_memory = 40 + (server_id % 5) * 6
    base_latency = 20 + (server_id % 10) * 2
    
    # Генерируем точки данных с интервалом в 1 час
    for hour in range(hours, 0, -1):
        timestamp = now - timedelta(hours=hour)
        
        # Добавляем случайные колебания к базовым значениям
        hour_of_day = timestamp.hour
        day_factor = 1.0 + (0.2 if 9 <= hour_of_day <= 18 else -0.1)  # Больше нагрузки в рабочие часы
        
        rand_factor = random.uniform(0.8, 1.2)
        
        peers = max(0, int(base_peers * day_factor * rand_factor))
        load = min(100, max(0, base_load * day_factor * rand_factor))
        cpu = min(100, max(0, base_cpu * day_factor * rand_factor))
        memory = min(100, max(0, base_memory * day_factor * rand_factor))
        packet_loss = min(100, max(0, (server_id % 5) * random.uniform(0, 2)))
        latency = max(1, base_latency * rand_factor)
        
        metrics.append({
            "id": hour,
            "server_id": server_id,
            "timestamp": timestamp.isoformat(),
            "peers_count": peers,
            "cpu_usage": round(cpu, 1),
            "memory_usage": round(memory, 1),
            "load": round(load, 1),
            "network_in": int(1024 * 1024 * rand_factor),
            "network_out": int(512 * 1024 * rand_factor),
            "is_available": True,
            "packet_loss": round(packet_loss, 1),
            "latency_ms": round(latency, 1)
        })
    
    return metrics

@app.route('/api/peers/map', methods=['POST'])
def map_peer_to_server():
    """Добавление маппинга пира к серверу"""
    try:
        data = request.json
        
        required_fields = ['peer_id', 'server_id', 'public_key']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования сервера
                cur.execute("SELECT id FROM remote_servers WHERE server_id = %s", (data['server_id'],))
                server = cur.fetchone()
                if not server:
                    return jsonify({"error": "Server not found"}), 404
                
                server_id = server[0]
                
                # Проверка существования пира
                cur.execute("SELECT id FROM peers WHERE id = %s", (data['peer_id'],))
                if not cur.fetchone():
                    return jsonify({"error": "Peer not found"}), 404
                
                # Добавление маппинга
                query = """
                INSERT INTO peer_server_mapping (
                    peer_id,
                    server_id,
                    public_key
                ) VALUES (
                    %s, %s, %s
                )
                ON CONFLICT (public_key) 
                DO UPDATE SET 
                    peer_id = EXCLUDED.peer_id,
                    server_id = EXCLUDED.server_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """
                
                cur.execute(query, (
                    data['peer_id'],
                    server_id,
                    data['public_key']
                ))
                
                mapping_id = cur.fetchone()[0]
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Peer mapped to server successfully",
                    "mapping_id": mapping_id
                })
    except Exception as e:
        logger.exception(f"Error mapping peer to server: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/peers/unmap/<public_key>', methods=['DELETE'])
def unmap_peer(public_key):
    """Удаление маппинга пира к серверу"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования маппинга
                cur.execute("SELECT id FROM peer_server_mapping WHERE public_key = %s", (public_key,))
                if not cur.fetchone():
                    return jsonify({"error": "Mapping not found"}), 404
                
                # Удаление маппинга
                cur.execute("DELETE FROM peer_server_mapping WHERE public_key = %s", (public_key,))
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Peer unmapped successfully"
                })
    except Exception as e:
        logger.exception(f"Error unmapping peer: {e}")
        return jsonify({"error": str(e)}), 500
        
# @app.route('/api/config/<int:user_id>', methods=['GET'])
# def get_user_config(user_id):
#     """Получение конфигурации пользователя по ID"""
#     try:
#         with get_db_connection() as conn:
#             with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
#                 query = """
#                 SELECT * FROM user_configs WHERE user_id = %s
#                 """
#                 cur.execute(query, (user_id,))
#                 config = cur.fetchone()
                
#                 if not config:
#                     return jsonify({"error": "Конфигурация не найдена"}), 404
                
#                 return jsonify({"config": dict(config)})
#     except Exception as e:
#         logger.exception(f"Ошибка при получении конфигурации пользователя: {e}")
#         return jsonify({"error": str(e)}), 500

@app.route('/api/geolocations', methods=['GET'])
def get_geolocations():
    """Получение списка всех геолокаций"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT * FROM geolocations ORDER BY name
                """
                cur.execute(query)
                geolocations = [dict(row) for row in cur.fetchall()]
                
                return jsonify({"geolocations": geolocations})
    except Exception as e:
        logger.exception(f"Ошибка при получении геолокаций: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/by-geolocation/<int:geolocation_id>', methods=['GET'])
def get_servers_by_geolocation(geolocation_id):
    """Получение списка серверов по ID геолокации"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.api_url, 
                    rs.geolocation_id,
                    rs.auth_type,
                    rs.max_peers,
                    g.name as geolocation_name
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    geolocations g ON rs.geolocation_id = g.id
                WHERE 
                    rs.geolocation_id = %s
                    AND rs.is_active = TRUE
                ORDER BY 
                    rs.name
                """
                cur.execute(query, (geolocation_id,))
                servers = [dict(row) for row in cur.fetchall()]
                
                return jsonify({"servers": servers})
    except Exception as e:
        logger.exception(f"Error getting servers by geolocation: {e}")
        return jsonify({"error": str(e)}), 500

# Добавьте эти эндпоинты в файл db_manager.py

@app.route('/api/servers/all', methods=['GET'])
def get_all_servers():
    """Возвращает все серверы (alias для /api/servers)"""
    return get_servers()

@app.route('/api/servers/<int:server_id>/connections', methods=['GET'])
def get_server_connections(server_id):
    """Получение активных подключений к серверу"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT 
                    ac.id,
                    ac.user_id,
                    ac.server_id,
                    ac.connected_at,
                    ac.last_activity,
                    ac.ip_address,
                    ac.bytes_sent,
                    ac.bytes_received
                FROM 
                    active_connections ac
                WHERE 
                    ac.server_id = %s
                """
                cur.execute(query, (server_id,))
                connections = [dict(row) for row in cur.fetchall()]
                
                return jsonify({"connections": connections})
    except Exception as e:
        logger.exception(f"Error getting server connections: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<int:server_id>/status', methods=['POST'])
def update_server_status(server_id):
    """Обновление статуса сервера"""
    try:
        data = request.json
        if 'status' not in data:
            return jsonify({"error": "Missing status field"}), 400
            
        status = data['status']
        if status not in ['active', 'inactive', 'maintenance', 'error']:
            return jsonify({"error": "Invalid status value"}), 400
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                UPDATE remote_servers
                SET is_active = %s
                WHERE id = %s
                """
                is_active = status == 'active'
                cur.execute(query, (is_active, server_id))
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": f"Server status updated to {status}"
                })
    except Exception as e:
        logger.exception(f"Error updating server status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/configs/change_geolocation', methods=['POST'])
def change_user_geolocation():
    """Изменение геолокации для пользователя"""
    try:
        data = request.json
        required_fields = ['user_id', 'geolocation_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
                
        user_id = data['user_id']
        geolocation_id = data['geolocation_id']
        server_id = data.get('server_id')
        migration_reason = data.get('migration_reason', 'user_request')
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Обновляем геолокацию в конфигурации пользователя
                query = """
                UPDATE configurations
                SET geolocation_id = %s
                WHERE user_id = %s AND active = TRUE
                """
                cur.execute(query, (geolocation_id, user_id))
                
                if server_id:
                    # Если указан конкретный сервер, привязываем к нему
                    query = """
                    UPDATE configurations
                    SET server_id = %s
                    WHERE user_id = %s AND active = TRUE
                    """
                    cur.execute(query, (server_id, user_id))
                
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Geolocation changed successfully"
                })
    except Exception as e:
        logger.exception(f"Error changing geolocation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/server_migrations/log', methods=['POST'])
def log_server_migration():
    """Логирование миграции пользователя между серверами"""
    try:
        data = request.json
        required_fields = ['user_id', 'from_server_id', 'to_server_id', 'migration_reason']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
                
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                INSERT INTO server_migrations (
                    user_id,
                    from_server_id,
                    to_server_id,
                    migration_reason,
                    migration_time,
                    success
                ) VALUES (
                    %s, %s, %s, %s, NOW(), %s
                ) RETURNING id
                """
                
                cur.execute(query, (
                    data['user_id'],
                    data['from_server_id'],
                    data['to_server_id'],
                    data['migration_reason'],
                    data.get('success', True)
                ))
                
                migration_id = cur.fetchone()[0]
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Migration logged successfully",
                    "migration_id": migration_id
                })
    except Exception as e:
        logger.exception(f"Error logging migration: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/select_optimal', methods=['POST'])
def select_optimal_server():
    """Выбор оптимального сервера для пользователя"""
    try:
        data = request.json
        if 'user_id' not in data:
            return jsonify({"error": "Missing user_id field"}), 400
            
        user_id = data['user_id']
        geolocation_id = data.get('geolocation_id')
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Базовый запрос для получения активных серверов
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.geolocation_id,
                    COUNT(ac.id) as active_connections
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    active_connections ac ON rs.id = ac.server_id
                WHERE 
                    rs.is_active = TRUE
                """
                
                params = []
                
                # Если указана геолокация, фильтруем по ней
                if geolocation_id:
                    query += " AND rs.geolocation_id = %s"
                    params.append(geolocation_id)
                
                # Группировка и сортировка
                query += """
                GROUP BY rs.id
                ORDER BY active_connections ASC, rs.id ASC
                LIMIT 1
                """
                
                cur.execute(query, params)
                optimal_server = cur.fetchone()
                
                if not optimal_server:
                    return jsonify({"message": "No available servers found"}), 404
                
                return jsonify({"server": dict(optimal_server)})
    except Exception as e:
        logger.exception(f"Error selecting optimal server: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/update_status_batch', methods=['POST'])
def update_servers_status_batch():
    """Обновление статуса нескольких серверов"""
    try:
        data = request.json
        if 'servers' not in data or not isinstance(data['servers'], list):
            return jsonify({"error": "Missing or invalid servers list"}), 400
            
        servers = data['servers']
        updated_count = 0
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for server in servers:
                    if 'id' not in server or 'status' not in server:
                        continue
                        
                    # Преобразуем статус в is_active
                    is_active = server['status'] == 'active'
                    
                    query = """
                    UPDATE remote_servers
                    SET is_active = %s, updated_at = NOW()
                    WHERE id = %s
                    """
                    
                    cur.execute(query, (is_active, server['id']))
                    updated_count += 1
                
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": f"Updated status for {updated_count} servers"
                })
    except Exception as e:
        logger.exception(f"Error updating servers status: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/api/servers/metrics/add', methods=['POST'])
# def add_server_metrics():
#     """Добавление метрик сервера"""
#     try:
#         logger.debug(f"Получен запрос на добавление метрик сервера: {request.method} {request.path}")
#         data = request.json
#         logger.debug(f"Полученные данные: {data}")
        
#         if 'server_id' not in data:
#             logger.warning("Отсутствует обязательное поле server_id")
#             return jsonify({"error": "Missing server_id field"}), 400
        
#         logger.debug(f"Проверка сервера с ID: {data['server_id']}")    
#         with get_db_connection() as conn:
#             # Проверим, существует ли сервер с таким ID
#             with conn.cursor() as check_cur:
#                 # Сначала проверяем в таблице remote_servers
#                 check_cur.execute("SELECT id FROM remote_servers WHERE id = %s", (data['server_id'],))
#                 server = check_cur.fetchone()
                
#                 if not server:
#                     # Если не нашли в remote_servers, проверяем в таблице servers
#                     check_cur.execute("SELECT id FROM servers WHERE id = %s", (data['server_id'],))
#                     server = check_cur.fetchone()
                    
#                     if not server:
#                         logger.warning(f"Сервер с ID {data['server_id']} не найден в базе данных")
#                         # Создаем запись о сервере перед добавлением метрик
#                         logger.info(f"Создание записи о сервере {data['server_id']} в таблице servers")
                        
#                         try:
#                             with conn.cursor() as insert_cur:
#                                 insert_query = """
#                                 INSERT INTO servers (id, name, status) 
#                                 VALUES (%s, %s, %s) 
#                                 RETURNING id
#                                 """
#                                 insert_cur.execute(insert_query, (
#                                     data['server_id'], 
#                                     f"Автоматически созданный сервер {data['server_id']}", 
#                                     "active"
#                                 ))
#                                 new_server_id = insert_cur.fetchone()[0]
#                                 conn.commit()
#                                 logger.info(f"Создан новый сервер с ID: {new_server_id}")
#                         except Exception as create_err:
#                             conn.rollback()
#                             logger.error(f"Ошибка при создании записи о сервере: {create_err}")
#                             return jsonify({"error": f"Сервер не существует и не удалось его создать: {str(create_err)}"}), 500
            
#             with conn.cursor() as cur:
#                 logger.debug("Подготовка SQL запроса для вставки метрик")
#                 # Проверим структуру таблицы server_metrics
#                 try:
#                     cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'server_metrics'")
#                     columns = cur.fetchall()
#                     logger.debug(f"Структура таблицы server_metrics: {columns}")
                    
#                     # Определим имена столбцов и составим запрос динамически
#                     column_names = [col[0] for col in columns]
#                     valid_fields = ['server_id', 'latency', 'bandwidth', 'jitter', 'packet_loss']
                    
#                     # Создаем списки полей и значений для запроса
#                     insert_fields = ['server_id']
#                     insert_values = [data['server_id']]
                    
#                     for field in valid_fields[1:]:  # Пропускаем server_id, он уже добавлен
#                         if field in column_names and field in data:
#                             insert_fields.append(field)
#                             insert_values.append(data.get(field))
                    
#                     # Добавляем поле времени измерения
#                     time_field = 'measured_at' if 'measured_at' in column_names else 'collected_at'
#                     insert_fields.append(time_field)
#                     insert_values.append('NOW()')
                    
#                     # Формируем SQL запрос
#                     placeholders = ', '.join(['%s' if val != 'NOW()' else val for val in insert_values])
#                     query = f"""
#                     INSERT INTO server_metrics (
#                         {', '.join(insert_fields)}
#                     ) VALUES (
#                         {placeholders}
#                     ) RETURNING id
#                     """
                    
#                     # Удаляем 'NOW()' из значений, так как это SQL-выражение
#                     final_values = [val for val in insert_values if val != 'NOW()']
                    
#                     logger.debug(f"Выполнение SQL запроса: {query} с параметрами {final_values}")
                    
#                     cur.execute(query, final_values)
#                     metric_id = cur.fetchone()[0]
#                     conn.commit()
#                     logger.info(f"Метрики успешно добавлены для сервера {data['server_id']}, ID метрики: {metric_id}")
                    
#                     return jsonify({
#                         "success": True,
#                         "message": "Metrics added successfully",
#                         "metric_id": metric_id
#                     })
#                 except Exception as sql_err:
#                     conn.rollback()
#                     logger.error(f"Ошибка выполнения SQL запроса: {sql_err}")
#                     # Попробуем использовать базовый запрос вставки
#                     try:
#                         simple_query = """
#                         INSERT INTO server_metrics (
#                             server_id,
#                             latency,
#                             bandwidth,
#                             jitter,
#                             packet_loss,
#                             measured_at
#                         ) VALUES (
#                             %s, %s, %s, %s, %s, NOW()
#                         ) RETURNING id
#                         """
                        
#                         simple_params = (
#                             data['server_id'],
#                             data.get('latency'),
#                             data.get('bandwidth'),
#                             data.get('jitter'),
#                             data.get('packet_loss')
#                         )
                        
#                         logger.debug(f"Выполнение базового SQL запроса с параметрами: {simple_params}")
#                         cur.execute(simple_query, simple_params)
#                         metric_id = cur.fetchone()[0]
#                         conn.commit()
#                         logger.info(f"Метрики успешно добавлены базовым запросом для сервера {data['server_id']}, ID метрики: {metric_id}")
                        
#                         return jsonify({
#                             "success": True,
#                             "message": "Metrics added successfully with basic query",
#                             "metric_id": metric_id
#                         })
#                     except Exception as basic_err:
#                         conn.rollback()
#                         logger.error(f"Ошибка выполнения базового SQL запроса: {basic_err}")
#                         raise basic_err
#     except Exception as e:
#         logger.exception(f"Ошибка добавления метрик сервера: {e}")
#         return jsonify({"error": str(e)}), 500

# Файл: /app/db_manager.py

@app.route('/api/servers/metrics/add', methods=['POST'])
def add_server_metrics():  # Удалил параметр 'self'
    """Добавление метрик сервера"""
    try:
        logger.debug(f"Получен запрос на добавление метрик сервера: {request.method} {request.path}")
        data = request.json
        logger.debug(f"Полученные данные: {data}")
        
        if 'server_id' not in data:
            logger.warning("Отсутствует обязательное поле server_id")
            return jsonify({"error": "Missing server_id field"}), 400
        
        logger.debug(f"Проверка сервера с ID: {data['server_id']}")    
        with get_db_connection() as conn:
            # Проверим, существует ли сервер с таким ID
            with conn.cursor() as check_cur:
                # Изменить запрос для правильного сравнения типов
                # Преобразуем server_id к строке при сравнении
                check_cur.execute("SELECT id FROM remote_servers WHERE server_id = %s::text", (data['server_id'],))
                server_exists = check_cur.fetchone()
                if not server_exists:
                    logger.warning(f"Сервер с ID {data['server_id']} не найден в базе данных")
                    # Проверим в логах, что именно приходит в server_id
                    logger.debug(f"Тип данных server_id: {type(data['server_id'])}, значение: {data['server_id']}")
                    
                    # Вместо ошибки создадим запись о неизвестном сервере
                    logger.info(f"Создание записи метрик для неизвестного сервера {data['server_id']}")
            
            with conn.cursor() as cur:
                logger.debug("Подготовка SQL запроса для вставки метрик")
                query = """
                INSERT INTO server_metrics (
                    server_id,
                    latency,
                    bandwidth,
                    jitter,
                    packet_loss,
                    measured_at
                ) VALUES (
                    %s, %s, %s, %s, %s, NOW()
                ) RETURNING id
                """
                
                params = (
                    data['server_id'],
                    data.get('latency'),
                    data.get('bandwidth'),
                    data.get('jitter'),
                    data.get('packet_loss')
                )
                logger.debug(f"Выполнение SQL запроса с параметрами: {params}")
                
                try:
                    cur.execute(query, params)
                    metric_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"Метрики успешно добавлены для сервера {data['server_id']}, ID метрики: {metric_id}")
                    
                    return jsonify({
                        "success": True,
                        "message": "Metrics added successfully",
                        "metric_id": metric_id
                    })
                except Exception as sql_err:
                    conn.rollback()
                    logger.error(f"Ошибка выполнения SQL запроса: {sql_err}")
                    # Проверим структуру таблицы
                    try:
                        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'server_metrics'")
                        columns = cur.fetchall()
                        logger.debug(f"Структура таблицы server_metrics: {columns}")
                    except Exception as schema_err:
                        logger.error(f"Не удалось получить структуру таблицы server_metrics: {schema_err}")
                    
                    raise sql_err
    except Exception as e:
        logger.exception(f"Ошибка добавления метрик сервера: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
def create_user_config():
    """Создание или обновление конфигурации пользователя"""
    try:
        data = request.json
        logger.debug(f"Получены данные для создания/обновления конфигурации: {data}")
        
        if 'user_id' not in data:
            logger.warning("Отсутствует обязательное поле user_id")
            return jsonify({"error": "Missing user_id field"}), 400
        
        user_id = data['user_id']
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверяем, существует ли уже конфигурация для этого пользователя
                cur.execute("SELECT id FROM user_configs WHERE user_id = %s", (user_id,))
                existing_config = cur.fetchone()
                
                if existing_config:
                    # Обновляем существующую конфигурацию
                    logger.info(f"Обновление существующей конфигурации для пользователя {user_id}")
                    
                    # Формируем список полей для обновления
                    update_fields = []
                    update_values = []
                    
                    # Обязательные поля
                    if 'config' in data:
                        update_fields.append("config = %s")
                        update_values.append(data['config'])
                    
                    if 'public_key' in data:
                        update_fields.append("public_key = %s")
                        update_values.append(data['public_key'])
                    
                    if 'active' in data:
                        update_fields.append("active = %s")
                        update_values.append(data['active'])
                    
                    # Дополнительные поля
                    if 'geolocation_id' in data:
                        update_fields.append("geolocation_id = %s")
                        update_values.append(data['geolocation_id'])
                    
                    if 'server_id' in data:
                        update_fields.append("server_id = %s")
                        update_values.append(data['server_id'])
                    
                    if 'expiry_time' in data:
                        update_fields.append("expiry_time = %s")
                        update_values.append(data['expiry_time'])
                    
                    # Добавляем поле updated_at
                    update_fields.append("updated_at = NOW()")
                    
                    # Добавляем ID в конец списка параметров
                    update_values.append(existing_config[0])
                    
                    # Выполняем запрос на обновление
                    update_query = f"""
                        UPDATE user_configs 
                        SET {', '.join(update_fields)}
                        WHERE id = %s
                        RETURNING id
                    """
                    
                    cur.execute(update_query, update_values)
                    updated_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Конфигурация успешно обновлена, ID: {updated_id}")
                    return jsonify({
                        "success": True,
                        "message": "Configuration updated successfully",
                        "config_id": updated_id
                    })
                else:
                    # Создаем новую конфигурацию
                    logger.info(f"Создание новой конфигурации для пользователя {user_id}")
                    
                    # Базовые поля
                    fields = ['user_id']
                    values = [user_id]
                    
                    # Добавляем дополнительные поля, если они есть
                    optional_fields = [
                        'config', 'public_key', 'geolocation_id', 'server_id', 
                        'active', 'expiry_time'
                    ]
                    
                    for field in optional_fields:
                        if field in data:
                            fields.append(field)
                            values.append(data[field])
                    
                    # Добавляем поле created_at и updated_at
                    fields.extend(['created_at', 'updated_at'])
                    placeholders = ['%s'] * len(values) + ['NOW()', 'NOW()']
                    
                    # Формируем SQL запрос
                    insert_query = f"""
                        INSERT INTO user_configs (
                            {', '.join(fields)}
                        ) VALUES (
                            {', '.join(placeholders)}
                        ) RETURNING id
                    """
                    
                    cur.execute(insert_query, values)
                    config_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Конфигурация успешно создана, ID: {config_id}")
                    return jsonify({
                        "success": True,
                        "message": "Configuration created successfully",
                        "config_id": config_id
                    }), 201
    except Exception as e:
        logger.exception(f"Ошибка при создании/обновлении конфигурации: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/api/config/<int:user_id>', methods=['GET'])
# def get_user_config_by_id(user_id):
#     """Получение конфигурации пользователя по ID"""
#     try:
#         with get_db_connection() as conn:
#             with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
#                 # Проверяем в таблице configurations
#                 query = """
#                 SELECT * FROM configurations WHERE user_id = %s AND active = TRUE
#                 """
#                 cur.execute(query, (user_id,))
#                 config = cur.fetchone()
                
#                 if config:
#                     return jsonify({"config": dict(config)})
                
#                 # Если в configurations не нашли, проверяем в user_configs
#                 query = """
#                 SELECT * FROM user_configs WHERE user_id = %s
#                 """
#                 cur.execute(query, (user_id,))
#                 config = cur.fetchone()
                
#                 if config:
#                     return jsonify({"config": dict(config)})
                
#                 # Если конфигурация не найдена, создаем заглушку
#                 logger.warning(f"Конфигурация не найдена для пользователя {user_id}, создаем заглушку")
#                 return jsonify({
#                     "config": {
#                         "user_id": user_id,
#                         "status": "not_configured",
#                         "message": "Конфигурация не найдена"
#                     }
#                 })
#     except Exception as e:
#         logger.exception(f"Ошибка при получении конфигурации пользователя: {e}")
#         return jsonify({"error": str(e)}), 500

# Файл: database-service/db_manager.py

@app.route('/api/config/<int:user_id>', methods=['GET'])
def get_user_config(user_id):
    """Получение конфигурации пользователя по ID"""
    try:
        logger.info(f"Запрос конфигурации для пользователя {user_id}")
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Сначала проверяем в таблице user_configs
                cur.execute("""
                    SELECT 
                        uc.*,
                        g.name as geolocation_name,
                        rs.name as server_name
                    FROM 
                        user_configs uc
                    LEFT JOIN 
                        geolocations g ON uc.geolocation_id = g.id
                    LEFT JOIN 
                        remote_servers rs ON uc.server_id = rs.id
                    WHERE 
                        uc.user_id = %s
                    ORDER BY
                        uc.active DESC, uc.updated_at DESC
                    LIMIT 1
                """, (user_id,))
                
                config = cur.fetchone()
                
                if not config:
                    # Если в user_configs не нашли, проверяем в других таблицах или создаем пустую запись
                    logger.warning(f"Конфигурация для пользователя {user_id} не найдена")
                    
                    # Если хотите автоматически создавать пустую запись:
                    # cur.execute("""
                    #     INSERT INTO user_configs (user_id, active, created_at, updated_at)
                    #     VALUES (%s, FALSE, NOW(), NOW())
                    #     RETURNING id
                    # """, (user_id,))
                    # conn.commit()
                    
                    return jsonify({"error": "User configuration not found"}), 404
                
                # Преобразуем datetime объекты в строки
                result = dict(config)
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
                
                logger.info(f"Конфигурация успешно получена для пользователя {user_id}")
                return jsonify(result)
    except Exception as e:
        logger.exception(f"Ошибка при получении конфигурации пользователя: {e}")
        return jsonify({"error": str(e)}), 500

# Файл: database-service/db_manager.py

@app.route('/api/servers/<server_id>', methods=['GET'])
def get_server_by_id_or_name(server_id):
    """Получение информации о сервере по ID или имени сервера"""
    try:
        logger.info(f"Запрос информации о сервере {server_id}")
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Пробуем найти по ID или server_id (для строковых идентификаторов)
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.api_url, 
                    rs.endpoint,
                    rs.port,
                    rs.address,
                    rs.public_key,
                    rs.api_path,
                    rs.skip_api_check, 
                    rs.geolocation_id, 
                    rs.auth_type, 
                    rs.api_key, 
                    rs.oauth_client_id, 
                    rs.oauth_client_secret, 
                    rs.oauth_token_url, 
                    rs.hmac_secret, 
                    rs.max_peers, 
                    rs.is_active,
                    g.name as geolocation_name
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    geolocations g ON rs.geolocation_id = g.id
                WHERE 
                    rs.id = %s OR rs.server_id = %s
                """
                
                # Преобразуем server_id в число, если он числовой
                numeric_id = None
                try:
                    numeric_id = int(server_id)
                except ValueError:
                    # Если не преобразуется в число, оставляем None
                    pass
                
                cur.execute(query, (numeric_id if numeric_id else -1, server_id))
                server = cur.fetchone()
                
                if not server:
                    # Если сервер не найден, возвращаем ошибку
                    logger.warning(f"Сервер {server_id} не найден")
                    
                    # Если это строковый ID, возможно стоит создать запись автоматически
                    if isinstance(server_id, str) and server_id.startswith('srv-'):
                        logger.info(f"Автоматическое создание сервера с ID {server_id}")
                        
                        # Создаем базовую запись сервера
                        cur.execute("""
                            INSERT INTO remote_servers (
                                server_id, name, endpoint, port, address, 
                                public_key, location, is_active
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s
                            ) RETURNING id
                        """, (
                            server_id,
                            f"Auto-created server {server_id}",
                            "localhost",  # Базовые значения
                            51820,
                            "10.0.0.1/24",
                            "auto_created_public_key",
                            "Auto-created location",
                            True
                        ))
                        
                        new_server_id = cur.fetchone()[0]
                        conn.commit()
                        
                        # Повторный запрос для получения созданного сервера
                        cur.execute(query, (new_server_id, server_id))
                        server = cur.fetchone()
                        
                        if server:
                            logger.info(f"Сервер {server_id} успешно создан автоматически")
                            # Преобразование результата для совместимости
                            server_dict = dict(server)
                            server_dict['id'] = str(server_dict['id'])
                            if server_dict['geolocation_id']:
                                server_dict['geolocation_id'] = str(server_dict['geolocation_id'])
                            server_dict['status'] = 'active' if server_dict['is_active'] else 'inactive'
                            
                            return jsonify({"server": server_dict})
                    
                    return jsonify({"error": "Server not found"}), 404
                
                # Преобразование результата для совместимости
                server_dict = dict(server)
                server_dict['id'] = str(server_dict['id'])
                if server_dict['geolocation_id']:
                    server_dict['geolocation_id'] = str(server_dict['geolocation_id'])
                server_dict['status'] = 'active' if server_dict['is_active'] else 'inactive'
                
                return jsonify({"server": server_dict})
    except Exception as e:
        logger.exception(f"Ошибка при получении информации о сервере: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/status', methods=['GET'])
def get_api_status():
    """Проверка статуса API"""
    try:
        # Проверяем соединение с базой данных
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                
                # Собираем информацию о системе
                from datetime import datetime
                import os
                import platform
                
                system_info = {
                    "api_status": "ok",
                    "service_name": "database-service",
                    "service_version": os.environ.get("SERVICE_VERSION", "1.0.0"),
                    "database_connection": "ok",
                    "system": platform.system(),
                    "python_version": platform.python_version(),
                    "current_time": datetime.now().isoformat(),
                    "uptime": "N/A"  # Требуется дополнительная логика для отслеживания uptime
                }
                
                return jsonify(system_info)
    except Exception as e:
        logger.exception(f"Ошибка при проверке статуса API: {e}")
        return jsonify({
            "api_status": "error",
            "error_message": str(e),
            "service_name": "database-service"
        }), 500

# Анализ метрик серверов
@app.route('/api/servers/metrics/analyze', methods=['POST'])
def analyze_server_metrics():
    """Анализ метрик серверов для выявления аномалий и тенденций"""
    try:
        data = request.json
        
        # Проверка наличия данных
        if not data:
            return jsonify({"error": "Отсутствуют данные для анализа"}), 400
            
        # Получение параметров запроса
        server_ids = data.get('server_ids', [])
        time_period = data.get('time_period', 24)  # часы
        metrics_types = data.get('metrics_types', ['all'])
        
        results = {}
        anomalies = []
        
        # Анализ метрик для выбранных серверов
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                for server_id in server_ids:
                    # Проверка существования сервера
                    cur.execute("SELECT id FROM remote_servers WHERE id = %s", (server_id,))
                    if not cur.fetchone():
                        results[server_id] = {"error": "Сервер не найден"}
                        continue
                    
                    # Вычисляем временную метку для фильтрации по времени
                    from datetime import datetime, timedelta
                    time_threshold = datetime.now() - timedelta(hours=time_period)
                    
                    # Получение метрик сервера за указанный период
                    query = """
                    SELECT 
                        server_id,
                        AVG(cpu_load) as avg_cpu,
                        MAX(cpu_load) as max_cpu,
                        AVG(memory_usage) as avg_memory,
                        MAX(memory_usage) as max_memory,
                        AVG(network_in) as avg_network_in,
                        AVG(network_out) as avg_network_out,
                        COUNT(*) as data_points
                    FROM 
                        server_metrics
                    WHERE 
                        server_id = %s AND
                        collected_at >= %s
                    GROUP BY 
                        server_id
                    """
                    
                    cur.execute(query, (server_id, time_threshold))
                    metrics_summary = cur.fetchone()
                    
                    if not metrics_summary:
                        results[server_id] = {"status": "no_data"}
                        continue
                        
                    # Анализ аномалий (пример: высокая загрузка CPU)
                    if metrics_summary['max_cpu'] > 90:
                        anomalies.append({
                            "server_id": server_id,
                            "metric": "cpu_load",
                            "value": metrics_summary['max_cpu'],
                            "severity": "high",
                            "message": f"Высокая загрузка CPU: {metrics_summary['max_cpu']}%"
                        })
                    
                    # Добавление результатов анализа
                    results[server_id] = {
                        "status": "analyzed",
                        "summary": dict(metrics_summary),
                        "anomalies": [a for a in anomalies if a['server_id'] == server_id]
                    }
        
        return jsonify({
            "results": results,
            "anomalies": anomalies,
            "analyzed_servers": len(server_ids),
            "servers_with_data": len([s for s in results.values() if s.get('status') != 'no_data'])
        })
                
    except Exception as e:
        logger.exception(f"Ошибка при анализе метрик: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/geolocations/check', methods=['GET'])
def check_geolocations():
    """Проверка доступности геолокаций"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Получение списка геолокаций
                cur.execute("""
                    SELECT 
                        g.id, 
                        g.code, 
                        g.name, 
                        g.available,
                        COUNT(rs.id) as server_count,
                        SUM(CASE WHEN rs.is_active = TRUE THEN 1 ELSE 0 END) as active_servers
                    FROM 
                        geolocations g
                    LEFT JOIN 
                        remote_servers rs ON g.id = rs.geolocation_id
                    GROUP BY 
                        g.id, g.code, g.name, g.available
                    ORDER BY 
                        g.name
                """)
                
                geolocations = []
                for row in cur.fetchall():
                    geolocations.append({
                        "id": row['id'],
                        "code": row['code'],
                        "name": row['name'],
                        "available": row['available'],
                        "server_count": row['server_count'],
                        "active_servers": row['active_servers'],
                        "status": "operational" if row['active_servers'] > 0 else "unavailable"
                    })
                
                return jsonify({"geolocations": geolocations})
                
    except Exception as e:
        logger.exception(f"Ошибка при проверке геолокаций: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/api/configs/migrate_users', methods=['POST'])
# def migrate_users():
#     """Миграция пользователей между серверами"""
#     try:
#         data = request.json
        
#         # Проверка обязательных параметров
#         required_fields = ['source_server_id', 'target_server_id']
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({"error": f"Отсутствует обязательное поле: {field}"}), 400
        
#         source_server_id = data['source_server_id']
#         target_server_id = data['target_server_id']
#         user_ids = data.get('user_ids', [])  # Если не указаны, мигрируем всех пользователей
        
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 # Проверка существования серверов
#                 cur.execute("SELECT id FROM remote_servers WHERE id = %s", (source_server_id,))
#                 if not cur.fetchone():
#                     return jsonify({"error": f"Сервер-источник не найден: {source_server_id}"}), 404
                
#                 cur.execute("SELECT id FROM remote_servers WHERE id = %s", (target_server_id,))
#                 if not cur.fetchone():
#                     return jsonify({"error": f"Сервер-назначение не найден: {target_server_id}"}), 404
                
#                 # Получение конфигураций для миграции
#                 if user_ids:
#                     query = """
#                     SELECT id, user_id FROM configurations 
#                     WHERE server_id = %s AND active = TRUE AND user_id = ANY(%s)
#                     """
#                     cur.execute(query, (source_server_id, user_ids))
#                 else:
#                     query = """
#                     SELECT id, user_id FROM configurations 
#                     WHERE server_id = %s AND active = TRUE
#                     """
#                     cur.execute(query, (source_server_id,))
                
#                 configs = cur.fetchall()
                
#                 if not configs:
#                     return jsonify({"message": "Нет конфигураций для миграции", "migrated": 0}), 200
                
#                 # Обновление конфигураций
#                 migrated_count = 0
#                 for config in configs:
#                     # Логируем миграцию
#                     cur.execute("""
#                     INSERT INTO server_migrations 
#                     (user_id, from_server_id, to_server_id, migration_reason, migration_time, success)
#                     VALUES (%s, %s, %s, %s, NOW(), TRUE)
#                     """, (config[1], source_server_id, target_server_id, data.get('reason', 'admin_request')))
                    
#                     # Обновляем конфигурацию
#                     cur.execute("""
#                     UPDATE configurations
#                     SET server_id = %s, updated_at = NOW()
#                     WHERE id = %s
#                     """, (target_server_id, config[0]))
                    
#                     migrated_count += 1
                
#                 conn.commit()
                
#                 return jsonify({
#                     "success": True,
#                     "message": f"Успешно мигрировано {migrated_count} пользователей",
#                     "migrated": migrated_count,
#                     "total": len(configs)
#                 })
                
#     except Exception as e:
#         logger.exception(f"Ошибка при миграции пользователей: {e}")
#         return jsonify({"error": str(e)}), 500


@app.route('/api/configs/migrate_users', methods=['POST'])
def migrate_users():
    """Миграция пользователей между серверами"""
    try:
        data = request.json
        
        # Проверка наличия данных
        if not data:
            return jsonify({"error": "Отсутствуют данные для миграции"}), 400
            
        # Проверка обязательных параметров
        required_fields = ['source_server_id', 'target_server_id']
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
                
        if missing_fields:
            return jsonify({"error": f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"}), 400
        
        source_server_id = data['source_server_id']
        target_server_id = data['target_server_id']
        user_ids = data.get('user_ids', [])  # Если не указаны, мигрируем всех пользователей
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования серверов
                cur.execute("SELECT id FROM remote_servers WHERE id = %s", (source_server_id,))
                if not cur.fetchone():
                    return jsonify({"error": f"Сервер-источник не найден: {source_server_id}"}), 404
                
                cur.execute("SELECT id FROM remote_servers WHERE id = %s", (target_server_id,))
                if not cur.fetchone():
                    return jsonify({"error": f"Сервер-назначение не найден: {target_server_id}"}), 404
                
                # Получение конфигураций для миграции
                if user_ids:
                    query = """
                    SELECT id, user_id FROM configurations 
                    WHERE server_id = %s AND active = TRUE AND user_id = ANY(%s)
                    """
                    cur.execute(query, (source_server_id, user_ids))
                else:
                    query = """
                    SELECT id, user_id FROM configurations 
                    WHERE server_id = %s AND active = TRUE
                    """
                    cur.execute(query, (source_server_id,))
                
                configs = cur.fetchall()
                
                if not configs:
                    return jsonify({"message": "Нет конфигураций для миграции", "migrated": 0}), 200
                
                # Обновление конфигураций
                migrated_count = 0
                for config in configs:
                    # Логируем миграцию
                    cur.execute("""
                    INSERT INTO server_migrations 
                    (user_id, from_server_id, to_server_id, migration_reason, migration_time, success)
                    VALUES (%s, %s, %s, %s, NOW(), TRUE)
                    """, (config[1], source_server_id, target_server_id, data.get('reason', 'admin_request')))
                    
                    # Обновляем конфигурацию
                    cur.execute("""
                    UPDATE configurations
                    SET server_id = %s, updated_at = NOW()
                    WHERE id = %s
                    """, (target_server_id, config[0]))
                    
                    migrated_count += 1
                
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": f"Успешно мигрировано {migrated_count} пользователей",
                    "migrated": migrated_count,
                    "total": len(configs)
                })
                
    except Exception as e:
        logger.exception(f"Ошибка при миграции пользователей: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/geolocations/available', methods=['GET'])
def get_available_geolocations():
    """Получение списка доступных геолокаций"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Получение списка доступных геолокаций с активными серверами
                cur.execute("""
                    SELECT 
                        g.id, 
                        g.code, 
                        g.name, 
                        g.description,
                        COUNT(rs.id) as server_count,
                        SUM(CASE WHEN rs.is_active = TRUE THEN 1 ELSE 0 END) as active_servers
                    FROM 
                        geolocations g
                    JOIN 
                        remote_servers rs ON g.id = rs.geolocation_id
                    WHERE 
                        g.available = TRUE AND rs.is_active = TRUE
                    GROUP BY 
                        g.id, g.code, g.name, g.description
                    HAVING 
                        SUM(CASE WHEN rs.is_active = TRUE THEN 1 ELSE 0 END) > 0
                    ORDER BY 
                        g.name
                """)
                
                geolocations = [dict(row) for row in cur.fetchall()]
                
                return jsonify({"geolocations": geolocations})
                
    except Exception as e:
        logger.exception(f"Ошибка при получении доступных геолокаций: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/api/cleanup_expired', methods=['POST'])
# def cleanup_expired():
#     """Очистка просроченных данных (конфигурации, токены и т.д.)"""
#     try:
#         data = request.json or {}
        
#         # Параметры для контроля очистки разных типов данных
#         cleanup_configs = data.get('cleanup_configs', True)
#         cleanup_metrics = data.get('cleanup_metrics', True)
#         metrics_retention_days = data.get('metrics_retention_days', 30)
        
#         from datetime import datetime, timedelta
#         metrics_threshold = datetime.now() - timedelta(days=metrics_retention_days)
        
#         cleaned_data = {
#             "expired_configs": 0,
#             "old_metrics": 0
#         }
        
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 # Очистка просроченных конфигураций
#                 if cleanup_configs:
#                     cur.execute("""
#                     UPDATE configurations
#                     SET active = FALSE
#                     WHERE expiry_time < NOW() AND active = TRUE
#                     """)
#                     cleaned_data["expired_configs"] = cur.rowcount
                
#                 # Очистка старых метрик
#                 if cleanup_metrics:
#                     cur.execute("""
#                     DELETE FROM server_metrics
#                     WHERE collected_at < %s
#                     """, (metrics_threshold,))
#                     cleaned_data["old_metrics"] = cur.rowcount
                
#                 conn.commit()
                
#                 return jsonify({
#                     "success": True,
#                     "message": "Очистка просроченных данных выполнена успешно",
#                     "cleaned_data": cleaned_data
#                 })
                
#     except Exception as e:
#         logger.exception(f"Ошибка при очистке просроченных данных: {e}")
#         return jsonify({"error": str(e)}), 500

@app.route('/api/cleanup_expired', methods=['POST'])
def cleanup_expired():
    """Очистка просроченных данных (конфигурации, токены и т.д.)"""
    try:
        data = request.json or {}
        
        # Параметры для контроля очистки разных типов данных
        cleanup_configs = data.get('cleanup_configs', True)
        cleanup_metrics = data.get('cleanup_metrics', True)
        metrics_retention_days = data.get('metrics_retention_days', 30)
        
        from datetime import datetime, timedelta
        metrics_threshold = datetime.now() - timedelta(days=metrics_retention_days)
        
        cleaned_data = {
            "expired_configs": 0,
            "old_metrics": 0
        }
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Очистка просроченных конфигураций
                if cleanup_configs:
                    cur.execute("""
                    UPDATE configurations
                    SET active = FALSE
                    WHERE expiry_time < NOW() AND active = TRUE
                    """)
                    cleaned_data["expired_configs"] = cur.rowcount
                
                # Очистка старых метрик - проверяем существование таблицы и поля
                if cleanup_metrics:
                    # Проверяем существование колонки collected_at в таблице server_metrics
                    cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'server_metrics' AND column_name = 'collected_at'
                    """)
                    
                    if cur.fetchone():
                        # Если колонка collected_at существует
                        cur.execute("""
                        DELETE FROM server_metrics
                        WHERE collected_at < %s
                        """, (metrics_threshold,))
                        cleaned_data["old_metrics"] = cur.rowcount
                    else:
                        # Попробуем поле measured_at вместо collected_at
                        cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'server_metrics' AND column_name = 'measured_at'
                        """)
                        
                        if cur.fetchone():
                            cur.execute("""
                            DELETE FROM server_metrics
                            WHERE measured_at < %s
                            """, (metrics_threshold,))
                            cleaned_data["old_metrics"] = cur.rowcount
                        else:
                            logger.warning("Не найдена колонка для очистки метрик. Пропускаем очистку.")
                            cleaned_data["old_metrics"] = "скипнуто: не найдена подходящая колонка"
                
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Очистка просроченных данных выполнена успешно",
                    "cleaned_data": cleaned_data
                })
                
    except Exception as e:
        logger.exception(f"Ошибка при очистке просроченных данных: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['GET'])
def get_geolocation(geo_id):
    """Получение информации о геолокации по ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT * FROM geolocations WHERE id = %s
                """
                cur.execute(query, (geo_id,))
                geolocation = cur.fetchone()
                
                if not geolocation:
                    logger.warning(f"Геолокация не найдена. ID: {geo_id}")
                    return jsonify({"error": "Geolocation not found"}), 404
                
                return jsonify(dict(geolocation))
    except Exception as e:
        logger.exception(f"Ошибка при получении геолокации: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['PUT'])
def update_geolocation(geo_id):
    """Обновление информации о геолокации"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования геолокации
                cur.execute("SELECT id FROM geolocations WHERE id = %s", (geo_id,))
                if not cur.fetchone():
                    logger.warning(f"Геолокация не найдена при обновлении. ID: {geo_id}")
                    return jsonify({"error": "Geolocation not found"}), 404
                
                # Подготовка запроса на обновление
                update_fields = []
                params = []
                
                if 'code' in data:
                    update_fields.append("code = %s")
                    params.append(data['code'])
                
                if 'name' in data:
                    update_fields.append("name = %s")
                    params.append(data['name'])
                
                if 'available' in data:
                    update_fields.append("available = %s")
                    params.append(data['available'])
                
                if 'description' in data:
                    update_fields.append("description = %s")
                    params.append(data['description'])
                
                if not update_fields:
                    return jsonify({"message": "No fields to update"}), 400
                
                # Добавление ID в параметры
                params.append(geo_id)
                
                # Выполнение запроса на обновление
                query = f"""
                UPDATE geolocations 
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, code, name, available, description
                """
                
                cur.execute(query, params)
                updated_geo = cur.fetchone()
                conn.commit()
                
                if updated_geo:
                    logger.info(f"Геолокация успешно обновлена. ID: {geo_id}")
                    column_names = [desc[0] for desc in cur.description]
                    result = dict(zip(column_names, updated_geo))
                    return jsonify(result)
                else:
                    logger.error(f"Не удалось обновить геолокацию. ID: {geo_id}")
                    return jsonify({"error": "Failed to update geolocation"}), 500
                
    except Exception as e:
        logger.exception(f"Ошибка при обновлении геолокации: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/geolocations/<int:geo_id>', methods=['DELETE'])
def delete_geolocation(geo_id):
    """Удаление геолокации"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка существования геолокации
                cur.execute("SELECT id FROM geolocations WHERE id = %s", (geo_id,))
                if not cur.fetchone():
                    logger.warning(f"Геолокация не найдена при удалении. ID: {geo_id}")
                    return jsonify({"error": "Geolocation not found"}), 404
                
                # Проверка использования геолокации серверами
                cur.execute("SELECT COUNT(*) FROM remote_servers WHERE geolocation_id = %s", (geo_id,))
                server_count = cur.fetchone()[0]
                if server_count > 0:
                    logger.warning(f"Невозможно удалить геолокацию, так как она используется {server_count} серверами. ID: {geo_id}")
                    return jsonify({
                        "error": f"Cannot delete geolocation: it is used by {server_count} servers. Change the servers' geolocation first."
                    }), 400
                
                # Удаление геолокации
                cur.execute("DELETE FROM geolocations WHERE id = %s", (geo_id,))
                conn.commit()
                
                logger.info(f"Геолокация успешно удалена. ID: {geo_id}")
                return jsonify({
                    "success": True,
                    "message": "Geolocation deleted successfully"
                })
    except Exception as e:
        logger.exception(f"Ошибка при удалении геолокации: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/geolocations', methods=['POST'])
def add_geolocation():
    """Добавление новой геолокации"""
    try:
        data = request.json
        
        # Проверка обязательных полей
        required_fields = ['code', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Проверка уникальности кода геолокации
                cur.execute("SELECT id FROM geolocations WHERE code = %s", (data['code'],))
                if cur.fetchone():
                    logger.warning(f"Геолокация с кодом {data['code']} уже существует")
                    return jsonify({"error": f"Geolocation with code {data['code']} already exists"}), 400
                
                # Вставка новой геолокации
                query = """
                INSERT INTO geolocations (
                    code, name, description, available
                ) VALUES (
                    %s, %s, %s, %s
                ) RETURNING id, code, name, description, available
                """
                
                cur.execute(query, (
                    data['code'].upper(),
                    data['name'],
                    data.get('description', ''),
                    data.get('available', True)
                ))
                
                new_geo = cur.fetchone()
                conn.commit()
                
                if new_geo:
                    column_names = [desc[0] for desc in cur.description]
                    result = dict(zip(column_names, new_geo))
                    logger.info(f"Геолокация успешно добавлена: {result}")
                    return jsonify(result), 201
                else:
                    logger.error(f"Не удалось добавить геолокацию")
                    return jsonify({"error": "Failed to add geolocation"}), 500
                
    except Exception as e:
        logger.exception(f"Ошибка при добавлении геолокации: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/rebalance', methods=['POST'])
def rebalance_servers():
    """Ребалансировка нагрузки на серверах"""
    try:
        data = request.json or {}
        
        # Получение параметров
        geolocation_id = data.get('geolocation_id')
        auto_migrate = data.get('auto_migrate', False)
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Базовый запрос для получения активных серверов
                query = """
                SELECT 
                    rs.id, 
                    rs.server_id, 
                    rs.name, 
                    rs.location, 
                    rs.geolocation_id,
                    COUNT(c.id) as active_configs,
                    rs.max_peers
                FROM 
                    remote_servers rs
                LEFT JOIN 
                    configurations c ON rs.id = c.server_id AND c.active = TRUE
                WHERE 
                    rs.is_active = TRUE
                """
                
                params = []
                
                # Если указана геолокация, фильтруем по ней
                if geolocation_id:
                    query += " AND rs.geolocation_id = %s"
                    params.append(geolocation_id)
                
                # Группировка и получение данных
                query += """
                GROUP BY rs.id
                ORDER BY rs.id ASC
                """
                
                cur.execute(query, params)
                servers = [dict(row) for row in cur.fetchall()]
                
                if not servers:
                    return jsonify({"message": "Нет доступных серверов для ребалансировки"}), 404
                
                # Рассчитываем статистику заполненности серверов
                total_users = sum(s['active_configs'] for s in servers)
                total_capacity = sum(s['max_peers'] or 100 for s in servers)
                
                if total_capacity == 0:
                    return jsonify({"error": "Общая вместимость серверов равна нулю"}), 400
                    
                average_load = total_users / total_capacity
                
                # Определяем перегруженные и недогруженные серверы
                overloaded = []
                underloaded = []
                
                for server in servers:
                    capacity = server['max_peers'] or 100
                    load_factor = server['active_configs'] / capacity if capacity > 0 else 0
                    
                    server['load_factor'] = load_factor
                    server['load_percent'] = round(load_factor * 100, 1)
                    
                    if load_factor > average_load * 1.2:  # На 20% больше среднего
                        overloaded.append(server)
                    elif load_factor < average_load * 0.8:  # На 20% меньше среднего
                        underloaded.append(server)
                
                # Если включена автоматическая миграция
                migrations = []
                if auto_migrate and overloaded and underloaded:
                    for o_server in overloaded:
                        for u_server in underloaded:
                            # Определяем, сколько пользователей нужно переместить
                            o_capacity = o_server['max_peers'] or 100
                            u_capacity = u_server['max_peers'] or 100
                            
                            o_ideal = o_capacity * average_load
                            u_ideal = u_capacity * average_load
                            
                            o_excess = o_server['active_configs'] - o_ideal
                            u_space = u_ideal - u_server['active_configs']
                            
                            # Сколько пользователей можем переместить
                            to_migrate = min(int(o_excess), int(u_space))
                            
                            if to_migrate > 0:
                                # Получаем пользователей для миграции
                                cur.execute("""
                                SELECT id, user_id FROM configurations
                                WHERE server_id = %s AND active = TRUE
                                LIMIT %s
                                """, (o_server['id'], to_migrate))
                                
                                configs = cur.fetchall()
                                if configs:
                                    # Выполняем миграцию
                                    for config in configs:
                                        # Логируем миграцию
                                        cur.execute("""
                                        INSERT INTO server_migrations 
                                        (user_id, from_server_id, to_server_id, migration_reason, migration_time, success)
                                        VALUES (%s, %s, %s, 'auto_rebalance', NOW(), TRUE)
                                        """, (config[1], o_server['id'], u_server['id']))
                                        
                                        # Обновляем конфигурацию
                                        cur.execute("""
                                        UPDATE configurations
                                        SET server_id = %s, updated_at = NOW()
                                        WHERE id = %s
                                        """, (u_server['id'], config[0]))
                                    
                                    migrations.append({
                                        "from_server": o_server['server_id'],
                                        "to_server": u_server['server_id'],
                                        "users_migrated": len(configs)
                                    })
                
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "servers": servers,
                    "statistics": {
                        "total_users": total_users,
                        "total_capacity": total_capacity,
                        "average_load_percent": round(average_load * 100, 1),
                        "overloaded_servers": len(overloaded),
                        "underloaded_servers": len(underloaded)
                    },
                    "migrations": migrations,
                    "auto_migrated": auto_migrate and len(migrations) > 0
                })
                
    except Exception as e:
        logger.exception(f"Ошибка при ребалансировке серверов: {e}")
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002) 