import os
import json
import psycopg2
import psycopg2.extras
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO,
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
                
                # Удаляем чувствительные данные
                for server in servers:
                    for key in ['api_key', 'oauth_client_id', 'oauth_client_secret', 'hmac_secret']:
                        if key in server:
                            del server[key]
                
                return jsonify({"servers": servers})
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
                
                return jsonify({"server": dict(server)})
    except Exception as e:
        logger.exception(f"Error getting server details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/add', methods=['POST'])
def add_server():
    """Добавление нового удаленного сервера"""
    try:
        data = request.json
        
        # Проверка обязательных полей
        required_fields = ['name', 'location', 'api_url', 'geolocation_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Генерация уникального server_id, если не указан
        if 'server_id' not in data:
            import uuid
            data['server_id'] = f"srv-{uuid.uuid4().hex[:8]}"
        
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
                    data['location'],
                    data['api_url'],
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
                
                return jsonify({
                    "success": True,
                    "message": "Server added successfully",
                    "server_id": server_id
                })
    except Exception as e:
        logger.exception(f"Error adding server: {e}")
        return jsonify({"error": str(e)}), 500

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
                
                for field in ['name', 'location', 'api_url', 'geolocation_id', 'auth_type', 
                             'api_key', 'oauth_client_id', 'oauth_client_secret', 
                             'oauth_token_url', 'hmac_secret', 'max_peers', 'is_active']:
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
                SET {', '.join(update_fields)}
                WHERE id = %s
                """
                
                cur.execute(query, params)
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Server updated successfully"
                })
    except Exception as e:
        logger.exception(f"Error updating server: {e}")
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
        
@app.route('/api/config/<int:user_id>', methods=['GET'])
def get_user_config(user_id):
    """Получение конфигурации пользователя по ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                SELECT * FROM user_configs WHERE user_id = %s
                """
                cur.execute(query, (user_id,))
                config = cur.fetchone()
                
                if not config:
                    return jsonify({"error": "Конфигурация не найдена"}), 404
                
                return jsonify({"config": dict(config)})
    except Exception as e:
        logger.exception(f"Ошибка при получении конфигурации пользователя: {e}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/api/servers/metrics/add', methods=['POST'])
def add_server_metrics():
    """Добавление метрик сервера"""
    try:
        data = request.json
        if 'server_id' not in data:
            return jsonify({"error": "Missing server_id field"}), 400
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
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
                
                cur.execute(query, (
                    data['server_id'],
                    data.get('latency'),
                    data.get('bandwidth'),
                    data.get('jitter'),
                    data.get('packet_loss')
                ))
                
                metric_id = cur.fetchone()[0]
                conn.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Metrics added successfully",
                    "metric_id": metric_id
                })
    except Exception as e:
        logger.exception(f"Error adding server metrics: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002) 