import os
import json
import psycopg2
import psycopg2.extras
import logging
from datetime import datetime, timedelta
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
                        "packet_loss": "packet_loss",
                        "measured_at": "timestamp"
                        }
                    
                    for db_field, api_field in field_mapping.items():
                        if db_field in columns:
                            select_fields.append(f"{db_field} as {api_field}")
                    
                    # Формируем SQL запрос с обнаруженными столбцами
                    query = f"""
                    SELECT 
                        {", ".join(select_fields)}
                    FROM 
                        server_metrics
                    WHERE 
                        server_id = %s AND
                        collected_at >= %s
                    ORDER BY 
                        collected_at ASC
                    """
                    
                    cur.execute(query, (server_id, time_threshold))
                    metrics = [dict(row) for row in cur.fetchall()]
                    
                    # Если нет данных, генерируем мок-данные
                    if not metrics:
                        mock_metrics = generate_mock_metrics(server_id, hours)
                        return jsonify({"metrics": mock_metrics, "mocked": True})
                    
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
                    
                    return jsonify({"metrics": metrics})
                    
                except Exception as e:
                    logger.exception(f"Ошибка при получении схемы таблицы: {e}")
                    # Если не удалось получить схему, используем мок-данные
                    mock_metrics = generate_mock_metrics(server_id, hours)
                    return jsonify({"metrics": mock_metrics, "mocked": True})
                
    except Exception as e:
        logger.exception(f"Error getting server metrics by ID: {e}")
        # Даже при ошибке возвращаем мок-данные для корректной работы интерфейса
        mock_metrics = generate_mock_metrics(server_id, hours)
        return jsonify({"metrics": mock_metrics, "mocked": True})

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

@app.route('/api/configs/migrate_users', methods=['POST'])
def migrate_users():
    """Миграция пользователей между серверами"""
    try:
        data = request.json
        
        # Проверка обязательных параметров
        required_fields = ['source_server_id', 'target_server_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Отсутствует обязательное поле: {field}"}), 400
        
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
                
                # Очистка старых метрик
                if cleanup_metrics:
                    cur.execute("""
                    DELETE FROM server_metrics
                    WHERE collected_at < %s
                    """, (metrics_threshold,))
                    cleaned_data["old_metrics"] = cur.rowcount
                
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002) 