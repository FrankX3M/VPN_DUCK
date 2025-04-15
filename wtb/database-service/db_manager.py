import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import math
import requests
from flask import Flask, request, jsonify
import threading
#
app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры подключения к PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'wireguard')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')


def init_db():
    """Инициализация базы данных."""
    # Общая функция для выполнения операции с базой данных с обработкой ошибок
    def execute_and_commit(query, params=None, commit=True, message=None):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            result = None
            if cursor.description:  # Если есть результат (SELECT)
                result = cursor.fetchall()
            if message:
                logger.info(message)
            return result
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при выполнении запроса: {str(e)}")
            logger.error(f"Запрос: {query}")
            return None
        finally:
            if conn:
                conn.close()
    
    # 1. Создаем базовые таблицы
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS configurations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        config TEXT NOT NULL,
        public_key TEXT NOT NULL,
        expiry_time TIMESTAMP NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL
    )
    ''', message="Таблица configurations создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        config_id INTEGER REFERENCES configurations(id),
        stars_amount INTEGER NOT NULL,
        transaction_id TEXT,
        status TEXT NOT NULL,
        days_extended INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL
    )
    ''', message="Таблица payments создана или уже существует")
    
    # 2. Создаем таблицы для мульти-геолокационной архитектуры
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS geolocations (
        id SERIAL PRIMARY KEY,
        code VARCHAR(10) NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT,
        available BOOLEAN NOT NULL DEFAULT TRUE,
        avg_rating FLOAT DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица geolocations создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS servers (
        id SERIAL PRIMARY KEY,
        geolocation_id INTEGER REFERENCES geolocations(id),
        endpoint TEXT NOT NULL,
        port INTEGER NOT NULL,
        public_key TEXT NOT NULL,
        private_key TEXT NOT NULL,
        address TEXT NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        last_check TIMESTAMP,
        load_factor FLOAT DEFAULT 0,
        metrics_rating FLOAT DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица servers создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS server_locations (
        server_id INTEGER PRIMARY KEY REFERENCES servers(id),
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        city TEXT,
        country TEXT,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица server_locations создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS user_locations (
        user_id INTEGER PRIMARY KEY,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        city TEXT,
        country TEXT,
        accuracy FLOAT,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица user_locations создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS server_metrics (
        id SERIAL PRIMARY KEY,
        server_id INTEGER REFERENCES servers(id),
        latency FLOAT,
        bandwidth FLOAT,
        jitter FLOAT,
        packet_loss FLOAT,
        measured_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица server_metrics создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS active_connections (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        server_id INTEGER REFERENCES servers(id),
        connected_at TIMESTAMP NOT NULL DEFAULT NOW(),
        last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
        ip_address TEXT,
        bytes_sent BIGINT DEFAULT 0,
        bytes_received BIGINT DEFAULT 0
    )
    ''', message="Таблица active_connections создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS user_connections (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        server_id INTEGER REFERENCES servers(id),
        geolocation_id INTEGER REFERENCES geolocations(id),
        connected_at TIMESTAMP NOT NULL DEFAULT NOW(),
        disconnected_at TIMESTAMP,
        duration INTEGER,
        bytes_sent BIGINT DEFAULT 0,
        bytes_received BIGINT DEFAULT 0,
        connection_quality INTEGER,
        ip_address TEXT
    )
    ''', message="Таблица user_connections создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        preferred_server_id INTEGER REFERENCES servers(id),
        preferred_geolocation_id INTEGER REFERENCES geolocations(id),
        preferred_time_start TIME,
        preferred_time_end TIME,
        preferred_connection_type TEXT,
        auto_connect BOOLEAN DEFAULT FALSE,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица user_preferences создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS server_migrations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        from_server_id INTEGER REFERENCES servers(id),
        to_server_id INTEGER REFERENCES servers(id),
        migration_reason VARCHAR(50) NOT NULL,
        migration_time TIMESTAMP NOT NULL DEFAULT NOW(),
        success BOOLEAN DEFAULT TRUE
    )
    ''', message="Таблица server_migrations создана или уже существует")
    
    execute_and_commit('''
    CREATE TABLE IF NOT EXISTS user_configurations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        config_id INTEGER REFERENCES configurations(id),
        server_id INTEGER REFERENCES servers(id),
        config_text TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    ''', message="Таблица user_configurations создана или уже существует")
    
    # Добавляем новые колонки в существующие таблицы
    try:
        execute_and_commit('ALTER TABLE configurations ADD COLUMN geolocation_id INTEGER REFERENCES geolocations(id)')
    except:
        logger.info("Колонка geolocation_id уже существует в таблице configurations")
    
    try:
        execute_and_commit('ALTER TABLE configurations ADD COLUMN server_id INTEGER REFERENCES servers(id)')
    except:
        logger.info("Колонка server_id уже существует в таблице configurations")
    
    # Создаем индексы для оптимизации запросов - каждый индекс отдельно
    index_queries = [
        'CREATE INDEX IF NOT EXISTS idx_servers_geolocation_id ON servers(geolocation_id)',
        'CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)',
        'CREATE INDEX IF NOT EXISTS idx_servers_metrics_rating ON servers(metrics_rating)',
        'CREATE INDEX IF NOT EXISTS idx_geolocations_avg_rating ON geolocations(avg_rating)',
        'CREATE INDEX IF NOT EXISTS idx_servers_last_check ON servers(last_check)',
        'CREATE INDEX IF NOT EXISTS idx_server_metrics_server_id_measured_at ON server_metrics(server_id, measured_at)',
        'CREATE INDEX IF NOT EXISTS idx_active_connections_user_id ON active_connections(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_active_connections_server_id ON active_connections(server_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_connections_user_id ON user_connections(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_connections_server_id ON user_connections(server_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_connections_connected_at ON user_connections(connected_at)',
        'CREATE INDEX IF NOT EXISTS idx_user_configurations_user_id ON user_configurations(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_configurations_server_id ON user_configurations(server_id)'
    ]
    
    for query in index_queries:
        execute_and_commit(query)
    
    # Добавляем начальные данные для геолокаций, если таблица пуста
    count = execute_and_commit('SELECT COUNT(*) FROM geolocations', commit=False)
    if count and count[0][0] == 0:
        execute_and_commit('''
        INSERT INTO geolocations (code, name, description, available, created_at)
        VALUES 
            ('ru', 'Россия', 'Серверы в России', TRUE, NOW()),
            ('us', 'США', 'Серверы в США', TRUE, NOW()),
            ('eu', 'Европа', 'Серверы в странах Европы', TRUE, NOW()),
            ('asia', 'Азия', 'Серверы в странах Азии', TRUE, NOW())
        ''', message="Добавлены начальные данные для геолокаций")
    
    # Инициализируем данные для первого сервера, если таблица серверов пуста
    count = execute_and_commit('SELECT COUNT(*) FROM servers', commit=False)
    if count and count[0][0] == 0:
        # Получаем geolocation_id для России
        geo_id_result = execute_and_commit('SELECT id FROM geolocations WHERE code = %s', ('ru',), commit=False)
        
        if geo_id_result:
            geo_id = geo_id_result[0][0]
            
            # Получаем данные сервера из окружения
            server_endpoint = os.getenv('SERVER_ENDPOINT', 'your-server-endpoint.com')
            server_port = int(os.getenv('SERVER_PORT', '51820'))
            server_address = os.getenv('SERVER_ADDRESS', '10.0.0.1/24')
            
            # Получаем ключи из WireGuard
            server_private_key = "dummy_private_key"
            server_public_key = "dummy_public_key"
            
            try:
                with open('/etc/wireguard/private.key', 'r') as f:
                    server_private_key = f.read().strip()
                    
                with open('/etc/wireguard/public.key', 'r') as f:
                    server_public_key = f.read().strip()
            except Exception as e:
                logger.warning(f"Не удалось получить ключи WireGuard: {str(e)}")
            
            execute_and_commit('''
            INSERT INTO servers 
                (geolocation_id, endpoint, port, public_key, private_key, address, status, last_check, created_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
            ''', (geo_id, server_endpoint, server_port, server_public_key, server_private_key, server_address),
            message="Добавлен первый сервер")
    
    # Обновляем существующие конфигурации, привязывая их к первому серверу
    execute_and_commit('''
    UPDATE configurations c
    SET server_id = s.id, geolocation_id = s.geolocation_id
    FROM servers s
    WHERE c.server_id IS NULL AND s.id = (SELECT MIN(id) FROM servers)
    ''')
    
    logger.info("База данных инициализирована успешно")

def get_db_connection():
    """Получение соединения с базой данных PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

def calculate_distance(lat1, lon1, lat2, lon2):
    """Рассчитывает расстояние между двумя точками на земной поверхности в километрах."""
    R = 6371  # Радиус Земли в километрах
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def determine_user_location(user_id, ip_address=None):
    """Определяет географическое положение пользователя по IP-адресу или истории."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже свежие данные о местоположении пользователя
    cursor.execute(
        """
        SELECT latitude, longitude, city, country, updated_at
        FROM user_locations
        WHERE user_id = %s AND updated_at > NOW() - INTERVAL '1 day'
        """,
        (user_id,)
    )
    
    user_location = cursor.fetchone()
    
    if user_location:
        # Используем существующие данные, если они свежие
        conn.close()
        return {
            'latitude': user_location[0],
            'longitude': user_location[1],
            'city': user_location[2],
            'country': user_location[3]
        }
    
    # Если IP-адрес не передан, пытаемся получить последний известный
    if not ip_address:
        cursor.execute(
            """
            SELECT ip_address 
            FROM user_connections 
            WHERE user_id = %s 
            ORDER BY connected_at DESC 
            LIMIT 1
            """,
            (user_id,)
        )
        result = cursor.fetchone()
        if result:
            ip_address = result[0]
    
    if ip_address:
        try:
            # Используем внешний сервис геолокации по IP
            geo_service_url = os.getenv('GEO_SERVICE_URL', 'https://ipapi.co')
            response = requests.get(f"{geo_service_url}/{ip_address}/json/")
            
            if response.status_code == 200:
                location_data = response.json()
                
                # Сохраняем полученные данные
                latitude = location_data.get('latitude')
                longitude = location_data.get('longitude')
                city = location_data.get('city')
                country = location_data.get('country_name')
                
                if latitude and longitude:
                    cursor.execute(
                        """
                        INSERT INTO user_locations (user_id, latitude, longitude, city, country, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (user_id) DO UPDATE 
                        SET latitude = EXCLUDED.latitude, 
                            longitude = EXCLUDED.longitude,
                            city = EXCLUDED.city,
                            country = EXCLUDED.country,
                            updated_at = NOW()
                        """,
                        (user_id, latitude, longitude, city, country)
                    )
                    conn.commit()
                    
                    conn.close()
                    return {
                        'latitude': latitude,
                        'longitude': longitude,
                        'city': city,
                        'country': country
                    }
        except Exception as e:
            logger.error(f"Ошибка при определении геолокации по IP: {str(e)}")
    
    # Если не удалось определить местоположение, возвращаем None
    conn.close()
    return None

def get_user_preferences(user_id):
    """Получает сохраненные предпочтения пользователя."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT * FROM user_preferences WHERE user_id = %s
        """,
        (user_id,)
    )
    
    preferences = cursor.fetchone()
    conn.close()
    
    return preferences

def measure_server_metrics(server_id, endpoint):
    """Измеряет метрики сервера и сохраняет их в базу данных."""
    try:
        import subprocess
        import re
        
        logger.info(f"Измерение метрик для сервера {server_id} ({endpoint})")
        
        # Измерение задержки и джиттера с помощью ping
        ping_result = subprocess.run(
            ["ping", "-c", "10", endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        
        latency = None
        jitter = None
        packet_loss = None
        
        if ping_result.returncode == 0:
            ping_output = ping_result.stdout
            
            # Извлекаем среднюю задержку
            latency_match = re.search(r'min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/([\d.]+)', ping_output)
            if latency_match:
                latency = float(latency_match.group(1))
                jitter = float(latency_match.group(2))
            
            # Извлекаем процент потери пакетов
            packet_loss_match = re.search(r'(\d+)% packet loss', ping_output)
            if packet_loss_match:
                packet_loss = float(packet_loss_match.group(1))
        else:
            logger.warning(f"Ошибка ping для сервера {server_id} ({endpoint}): {ping_result.stderr}")
        
        # Примерное измерение пропускной способности
        # В реальном проекте здесь будет более точная оценка скорости соединения
        bandwidth = None
        try:
            # Имитируем тест скорости (в реальном проекте использовать speedtest или iperf)
            import random
            bandwidth = random.uniform(50, 150)  # Mbps, случайное значение для демонстрации
        except Exception as e:
            logger.warning(f"Ошибка при измерении скорости для сервера {server_id}: {str(e)}")
        
        # Сохраняем метрики в базу данных
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO server_metrics (server_id, latency, jitter, packet_loss, bandwidth, measured_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (server_id, latency, jitter, packet_loss, bandwidth)
        )
        
        # Обновляем время последней проверки сервера
        cursor.execute(
            """
            UPDATE servers
            SET last_check = NOW()
            WHERE id = %s
            """,
            (server_id,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Метрики для сервера {server_id} сохранены: latency={latency}ms, jitter={jitter}ms, packet_loss={packet_loss}%, bandwidth={bandwidth}Mbps")
        
        return {
            'latency': latency,
            'jitter': jitter,
            'packet_loss': packet_loss,
            'bandwidth': bandwidth
        }
    except Exception as e:
        logger.error(f"Ошибка при измерении метрик сервера {server_id}: {str(e)}")
        return None

#-------------------------
# Основные API эндпоинты
#-------------------------
# Новые API-эндпоинты для добавления в db_manager.py

# @app.route('/servers/all', methods=['GET'])
# def get_all_servers():
#     """Получает список всех серверов."""
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
        
#         cursor.execute(
#             """
#             SELECT s.*, sl.city, sl.country, sl.latitude, sl.longitude 
#             FROM servers s
#             LEFT JOIN server_locations sl ON s.id = sl.server_id
#             ORDER BY s.id
#             """
#         )
        
#         servers = cursor.fetchall()
#         conn.close()
        
#         return jsonify({"servers": servers}), 200
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка серверов: {str(e)}")
#         return jsonify({"error": str(e)}), 500

@app.route('/servers/register', methods=['POST'])
def register_server():
    """Регистрирует новый сервер в базе данных."""
    data = request.json
    
    required_fields = ['geolocation_id', 'endpoint', 'port', 'public_key', 'address']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже сервер с таким endpoint и портом
        cursor.execute(
            """
            SELECT id FROM servers WHERE endpoint = %s AND port = %s
            """,
            (data.get('endpoint'), data.get('port'))
        )
        
        existing_server = cursor.fetchone()
        if existing_server:
            conn.close()
            return jsonify({"error": "Сервер с таким endpoint и портом уже существует", "server_id": existing_server[0]}), 409
        
        # Вставляем запись в таблицу servers
        cursor.execute(
            """
            INSERT INTO servers
            (geolocation_id, endpoint, port, public_key, private_key, address, status, last_check, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
            RETURNING id
            """,
            (
                data.get('geolocation_id'),
                data.get('endpoint'),
                data.get('port'),
                data.get('public_key'),
                data.get('private_key', 'private_key_placeholder'),
                data.get('address')
            )
        )
        
        server_id = cursor.fetchone()[0]
        
        # Если предоставлены координаты, вставляем запись в server_locations
        if 'latitude' in data and 'longitude' in data:
            cursor.execute(
                """
                INSERT INTO server_locations
                (server_id, latitude, longitude, city, country, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (
                    server_id,
                    data.get('latitude'),
                    data.get('longitude'),
                    data.get('city'),
                    data.get('country')
                )
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "server_id": server_id}), 201
    except Exception as e:
        logger.error(f"Ошибка при регистрации сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
@app.route('/config', methods=['POST'])
def create_config():
    """Сохранение новой конфигурации WireGuard в базе данных."""
    data = request.json
    
    required_fields = ['user_id', 'config', 'expiry_time']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    config = data.get('config')
    expiry_time = data.get('expiry_time')
    active = data.get('active', True)
    geolocation_id = data.get('geolocation_id')
    server_id = data.get('server_id')
    
    # Извлекаем публичный ключ из конфига
    public_key = None
    for line in config.split('\n'):
        if line.startswith('[Peer]'):
            for peer_line in config.split('\n'):
                if peer_line.startswith('PublicKey'):
                    public_key = peer_line.split('=')[1].strip()
                    break
            break
    
    if not public_key:
        return jsonify({"error": "Не удалось извлечь публичный ключ из конфигурации"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Деактивируем существующие конфигурации для этого пользователя
        cursor.execute(
            "UPDATE configurations SET active = FALSE WHERE user_id = %s",
            (user_id,)
        )
        
        # Если geolocation_id и server_id не указаны, используем значения по умолчанию
        if not geolocation_id or not server_id:
            # Используем первый доступный сервер из России
            cursor.execute(
                """
                SELECT s.id, s.geolocation_id FROM servers s
                JOIN geolocations g ON s.geolocation_id = g.id
                WHERE g.code = 'ru' AND s.status = 'active'
                ORDER BY s.load_factor ASC
                LIMIT 1
                """
            )
            
            default_server = cursor.fetchone()
            if default_server:
                server_id = default_server[0]
                geolocation_id = default_server[1]
        
        # Вставляем новую конфигурацию
        cursor.execute(
            """
            INSERT INTO configurations 
            (user_id, config, public_key, expiry_time, active, created_at, geolocation_id, server_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, config, public_key, expiry_time, active, datetime.now(), geolocation_id, server_id)
        )
        
        config_id = cursor.fetchone()[0]
        
        # Если это первая конфигурация, сохраняем её также в user_configurations
        cursor.execute(
            """
            INSERT INTO user_configurations
            (user_id, config_id, server_id, config_text, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, config_id, server_id, config, datetime.now())
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "config_id": config_id}), 201
    except Exception as e:
        logger.error(f"Ошибка при сохранении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/config/<int:user_id>', methods=['GET'])
def get_user_config(user_id):
    """Получение активной конфигурации для пользователя."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT c.*, g.name as geolocation_name, g.code as geolocation_code, 
                   s.endpoint as server_endpoint, s.port as server_port
            FROM configurations c
            LEFT JOIN geolocations g ON c.geolocation_id = g.id
            LEFT JOIN servers s ON c.server_id = s.id
            WHERE c.user_id = %s AND c.active = TRUE
            """,
            (user_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Преобразуем timestamp в строку для JSON-сериализации
            row['expiry_time'] = row['expiry_time'].isoformat()
            row['created_at'] = row['created_at'].isoformat()
            
            return jsonify(row), 200
        else:
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
    except Exception as e:
        logger.error(f"Ошибка при получении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/config/extend', methods=['POST'])
def extend_config():
    """Продление срока действия конфигурации WireGuard."""
    data = request.json
    
    required_fields = ['user_id', 'days', 'stars_amount', 'transaction_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    days = data.get('days')
    stars_amount = data.get('stars_amount')
    transaction_id = data.get('transaction_id')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем активную конфигурацию пользователя
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = %s AND active = TRUE",
            (user_id,)
        )
        
        config = cursor.fetchone()
        if not config:
            conn.close()
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
        
        # Проверяем, не был ли уже использован этот transaction_id
        cursor.execute(
            "SELECT id FROM payments WHERE transaction_id = %s",
            (transaction_id,)
        )
        
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Транзакция уже обработана"}), 400
        
        # Рассчитываем новое время истечения
        current_expiry = config['expiry_time']
        
        # Если срок истек, начинаем отсчет от текущего времени
        if current_expiry < datetime.now():
            new_expiry = datetime.now() + timedelta(days=days)
        else:
            new_expiry = current_expiry + timedelta(days=days)
        
        # Обновляем время истечения конфигурации
        cursor.execute(
            "UPDATE configurations SET expiry_time = %s WHERE id = %s",
            (new_expiry, config['id'])
        )
        
        # Записываем информацию о платеже
        cursor.execute(
            """
            INSERT INTO payments 
            (user_id, config_id, stars_amount, transaction_id, status, days_extended, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, config['id'], stars_amount, transaction_id, 'completed', days, datetime.now())
        )
        
        payment_id = cursor.fetchone()['id']
        
        conn.commit()
        
        # Подготавливаем данные для ответа
        result = {
            "status": "success",
            "payment_id": payment_id,
            "config_id": config['id'],
            "new_expiry_time": new_expiry.isoformat(),
            "days_extended": days
        }
        
        conn.close()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Ошибка при продлении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/payments/history/<int:user_id>', methods=['GET'])
def get_payment_history(user_id):
    """Получение истории платежей пользователя."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT p.*, c.expiry_time, c.public_key 
            FROM payments p
            JOIN configurations c ON p.config_id = c.id
            WHERE p.user_id = %s
            ORDER BY p.created_at DESC
            """,
            (user_id,)
        )
        
        payments = cursor.fetchall()
        
        # Преобразуем timestamp в строки для JSON-сериализации
        for payment in payments:
            payment['created_at'] = payment['created_at'].isoformat()
            payment['expiry_time'] = payment['expiry_time'].isoformat()
        
        conn.close()
        
        return jsonify({"payments": payments}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении истории платежей: {str(e)}")
        return jsonify({"error": str(e)}), 500
                
@app.route('/servers/all', methods=['GET'])
def get_all_servers():
    """Получает список всех серверов."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT s.*, sl.city, sl.country, sl.latitude, sl.longitude 
            FROM servers s
            LEFT JOIN server_locations sl ON s.id = sl.server_id
            ORDER BY s.id
            """
        )
        
        servers = cursor.fetchall()
        conn.close()
        
        return jsonify({"servers": servers}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cleanup_expired', methods=['POST'])
def cleanup_expired_configs():
    """Очищает истекшие конфигурации."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Деактивируем конфигурации, срок действия которых истек
        cursor.execute(
            """
            UPDATE configurations
            SET active = FALSE
            WHERE expiry_time < NOW() AND active = TRUE
            RETURNING id, user_id, public_key
            """
        )
        
        expired_configs = cursor.fetchall()
        
        for config_id, user_id, public_key in expired_configs:
            # Логируем информацию о деактивированной конфигурации
            logger.info(f"Деактивирована истекшая конфигурация: id={config_id}, user_id={user_id}")
            
            # Пытаемся удалить пир из WireGuard, если предоставлен public_key
            if public_key:
                try:
                    # Отправка запроса на удаление пира из WireGuard
                    wireguard_url = os.getenv('WIREGUARD_SERVICE_URL', 'http://wireguard-service:5001')
                    remove_response = requests.delete(
                        f"{wireguard_url}/remove/{public_key}",
                        timeout=5
                    )
                    
                    if remove_response.status_code == 200:
                        logger.info(f"WireGuard-пир с ключом {public_key} успешно удален")
                    else:
                        logger.warning(f"Не удалось удалить WireGuard-пир: {remove_response.status_code}, {remove_response.text}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении WireGuard-пира: {str(e)}")
        
        conn.commit()
        
        # Также можно проверить и удалить строки с данными пользователей,
        # с которыми нет активных конфигураций более X дней (опционально)
        try:
            # Например, стирание информации о пользователях, неактивных более 90 дней
            days_to_retain = 90
            cursor.execute(
                """
                DELETE FROM user_locations
                WHERE user_id NOT IN (
                    SELECT user_id FROM configurations WHERE active = TRUE
                ) AND updated_at < NOW() - INTERVAL %s DAY
                """,
                (days_to_retain,)
            )
            
            deleted_rows = cursor.rowcount
            if deleted_rows > 0:
                logger.info(f"Удалены данные о местоположении для {deleted_rows} неактивных пользователей")
            
            conn.commit()
        except Exception as e:
            logger.warning(f"Ошибка при очистке устаревших данных о пользователях: {str(e)}")
            conn.rollback()
        
        conn.close()
        
        return jsonify({"cleaned": len(expired_configs)}), 200
    except Exception as e:
        logger.error(f"Ошибка при очистке истекших конфигураций: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Добавьте следующие функции в db_manager.py в соответствующие секции:

#-------------------------
# API для миграции пользователей
#-------------------------

@app.route('/servers/<int:server_id>/connections', methods=['GET'])
def get_server_connections(server_id):
    """Получает список активных подключений к серверу."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT ac.*, c.id as config_id, c.geolocation_id
            FROM active_connections ac
            JOIN configurations c ON ac.user_id = c.user_id AND c.active = TRUE
            WHERE ac.server_id = %s AND ac.last_activity > NOW() - INTERVAL '1 hour'
            ORDER BY ac.last_activity DESC
            """,
            (server_id,)
        )
        
        connections = cursor.fetchall()
        
        # Преобразуем временные метки в строки для JSON-сериализации
        for conn_data in connections:
            if 'connected_at' in conn_data and conn_data['connected_at']:
                conn_data['connected_at'] = conn_data['connected_at'].isoformat()
            if 'last_activity' in conn_data and conn_data['last_activity']:
                conn_data['last_activity'] = conn_data['last_activity'].isoformat()
        
        conn.close()
        
        return jsonify({"connections": connections}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении списка подключений: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/<int:server_id>/status', methods=['POST'])
def update_server_status(server_id):
    """Обновляет статус сервера."""
    data = request.json
    
    if not data or 'status' not in data:
        return jsonify({"error": "Отсутствует поле 'status'"}), 400
    
    status = data.get('status')
    
    # Проверяем допустимость статуса
    valid_statuses = ['active', 'inactive', 'degraded', 'maintenance']
    if status not in valid_statuses:
        return jsonify({"error": f"Недопустимый статус. Допустимые значения: {valid_statuses}"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE servers
            SET status = %s, last_check = NOW()
            WHERE id = %s
            RETURNING id, status
            """,
            (status, server_id)
        )
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({"error": f"Сервер с ID {server_id} не найден"}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "server_id": result[0],
            "status": result[1],
            "updated_at": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/update_status_batch', methods=['POST'])
def update_servers_status_batch():
    """Обновляет статус нескольких серверов за один запрос."""
    data = request.json
    
    if not data or 'servers' not in data:
        return jsonify({"error": "Отсутствует поле 'servers'"}), 400
    
    servers = data.get('servers')
    if not isinstance(servers, list) or not servers:
        return jsonify({"error": "Поле 'servers' должно быть непустым списком"}), 400
    
    # Проверяем допустимость статусов
    valid_statuses = ['active', 'inactive', 'degraded', 'maintenance']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updated_servers = []
        
        for server in servers:
            server_id = server.get('id')
            status = server.get('status')
            
            if not server_id or not status:
                continue
                
            if status not in valid_statuses:
                continue
            
            cursor.execute(
                """
                UPDATE servers
                SET status = %s, last_check = NOW()
                WHERE id = %s
                RETURNING id, status
                """,
                (status, server_id)
            )
            
            result = cursor.fetchone()
            
            if result:
                updated_servers.append({
                    "server_id": result[0],
                    "status": result[1]
                })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "updated_servers": updated_servers,
            "count": len(updated_servers),
            "updated_at": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при пакетном обновлении статуса серверов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/server_migrations/log', methods=['POST'])
def log_server_migration():
    """Записывает информацию о миграции пользователя в журнал."""
    data = request.json
    
    required_fields = ['user_id', 'from_server_id', 'to_server_id', 'migration_reason']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    from_server_id = data.get('from_server_id')
    to_server_id = data.get('to_server_id')
    migration_reason = data.get('migration_reason')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO server_migrations
            (user_id, from_server_id, to_server_id, migration_reason, migration_time, success)
            VALUES (%s, %s, %s, %s, NOW(), TRUE)
            RETURNING id
            """,
            (user_id, from_server_id, to_server_id, migration_reason)
        )
        
        migration_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "migration_id": migration_id,
            "user_id": user_id,
            "from_server_id": from_server_id,
            "to_server_id": to_server_id,
            "migration_reason": migration_reason,
            "migration_time": datetime.now().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Ошибка при записи информации о миграции: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/<int:server_id>', methods=['GET'])
def get_server_details(server_id):
    """Получает детальную информацию о сервере."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT s.*, g.name as geolocation_name, g.code as geolocation_code,
                   sl.city, sl.country, sl.latitude, sl.longitude,
                   (SELECT COUNT(*) FROM active_connections WHERE server_id = s.id) as active_connections_count,
                   (SELECT AVG(latency) FROM server_metrics WHERE server_id = s.id AND measured_at > NOW() - INTERVAL '24 hours') as avg_latency,
                   (SELECT AVG(packet_loss) FROM server_metrics WHERE server_id = s.id AND measured_at > NOW() - INTERVAL '24 hours') as avg_packet_loss
            FROM servers s
            LEFT JOIN geolocations g ON s.geolocation_id = g.id
            LEFT JOIN server_locations sl ON s.id = sl.server_id
            WHERE s.id = %s
            """,
            (server_id,)
        )
        
        server = cursor.fetchone()
        
        if not server:
            conn.close()
            return jsonify({"error": f"Сервер с ID {server_id} не найден"}), 404
        
        # Преобразуем временные метки в строки для JSON-сериализации
        if 'last_check' in server and server['last_check']:
            server['last_check'] = server['last_check'].isoformat()
        if 'created_at' in server and server['created_at']:
            server['created_at'] = server['created_at'].isoformat()
        
        conn.close()
        
        return jsonify(server), 200
    except Exception as e:
        logger.error(f"Ошибка при получении информации о сервере: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Добавьте этот код в db_manager.py в раздел API-эндпоинтов

# @app.route('/servers/<int:server_id>', methods=['PUT'])
# def update_server(server_id):
#     """API для обновления данных сервера."""
#     data = request.json
    
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         # Проверяем, существует ли сервер с таким ID
#         cursor.execute(
#             """
#             SELECT id FROM servers WHERE id = %s
#             """,
#             (server_id,)
#         )
        
#         if not cursor.fetchone():
#             conn.close()
#             return jsonify({"error": "Сервер с таким ID не найден"}), 404
        
#         # Формируем запрос на обновление
#         update_fields = []
#         params = []
        
#         if 'geolocation_id' in data:
#             update_fields.append("geolocation_id = %s")
#             params.append(data['geolocation_id'])
            
#         if 'endpoint' in data:
#             update_fields.append("endpoint = %s")
#             params.append(data['endpoint'])
            
#         if 'port' in data:
#             update_fields.append("port = %s")
#             params.append(data['port'])
            
#         if 'address' in data:
#             update_fields.append("address = %s")
#             params.append(data['address'])
            
#         if 'status' in data:
#             update_fields.append("status = %s")
#             params.append(data['status'])
            
#         if 'public_key' in data:
#             update_fields.append("public_key = %s")
#             params.append(data['public_key'])
            
#         if 'private_key' in data:
#             update_fields.append("private_key = %s")
#             params.append(data['private_key'])
            
#         if 'load_factor' in data:
#             update_fields.append("load_factor = %s")
#             params.append(data['load_factor'])
            
#         if 'metrics_rating' in data:
#             update_fields.append("metrics_rating = %s")
#             params.append(data['metrics_rating'])
        
#         # Если нет полей для обновления, возвращаем ошибку
#         if not update_fields:
#             conn.close()
#             return jsonify({"error": "Не указаны поля для обновления"}), 400
        
#         # Добавляем ID сервера в список параметров
#         params.append(server_id)
        
#         # Формируем и выполняем запрос на обновление
#         update_query = f"""
#             UPDATE servers
#             SET {", ".join(update_fields)}, last_check = NOW()
#             WHERE id = %s
#             RETURNING id
#         """
        
#         cursor.execute(update_query, params)
#         updated_server_id = cursor.fetchone()[0]
        
#         # Если есть данные о местоположении, обновляем таблицу server_locations
#         if ('latitude' in data and 'longitude' in data) or ('city' in data or 'country' in data):
#             # Проверяем, существует ли запись в server_locations
#             cursor.execute(
#                 """
#                 SELECT server_id FROM server_locations WHERE server_id = %s
#                 """,
#                 (server_id,)
#             )
            
#             location_exists = cursor.fetchone() is not None
            
#             if location_exists:
#                 # Обновляем существующую запись
#                 location_update_fields = []
#                 location_params = []
                
#                 if 'latitude' in data:
#                     location_update_fields.append("latitude = %s")
#                     location_params.append(data['latitude'])
                
#                 if 'longitude' in data:
#                     location_update_fields.append("longitude = %s")
#                     location_params.append(data['longitude'])
                
#                 if 'city' in data:
#                     location_update_fields.append("city = %s")
#                     location_params.append(data['city'])
                
#                 if 'country' in data:
#                     location_update_fields.append("country = %s")
#                     location_params.append(data['country'])
                
#                 if location_update_fields:
#                     location_update_fields.append("updated_at = NOW()")
#                     location_params.append(server_id)
                    
#                     location_update_query = f"""
#                         UPDATE server_locations
#                         SET {", ".join(location_update_fields)}
#                         WHERE server_id = %s
#                     """
                    
#                     cursor.execute(location_update_query, location_params)
#             else:
#                 # Создаем новую запись только если есть координаты
#                 if 'latitude' in data and 'longitude' in data:
#                     cursor.execute(
#                         """
#                         INSERT INTO server_locations
#                         (server_id, latitude, longitude, city, country, updated_at)
#                         VALUES (%s, %s, %s, %s, %s, NOW())
#                         """,
#                         (
#                             server_id,
#                             data.get('latitude'),
#                             data.get('longitude'),
#                             data.get('city'),
#                             data.get('country')
#                         )
#                     )
        
#         conn.commit()
#         conn.close()
        
#         return jsonify({"status": "success", "server_id": updated_server_id}), 200
#     except Exception as e:
#         logger.error(f"Ошибка при обновлении сервера: {str(e)}")
#         return jsonify({"error": str(e)}), 500
# Добавьте этот код в db_manager.py в раздел API-эндпоинтов

@app.route('/servers/<int:server_id>', methods=['PUT'])
def update_server(server_id):
    """API для обновления данных сервера."""
    data = request.json
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли сервер с таким ID
        cursor.execute(
            """
            SELECT id FROM servers WHERE id = %s
            """,
            (server_id,)
        )
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Сервер с таким ID не найден"}), 404
        
        # Формируем запрос на обновление
        update_fields = []
        params = []
        
        if 'geolocation_id' in data:
            update_fields.append("geolocation_id = %s")
            params.append(data['geolocation_id'])
            
        if 'endpoint' in data:
            update_fields.append("endpoint = %s")
            params.append(data['endpoint'])
            
        if 'port' in data:
            update_fields.append("port = %s")
            params.append(data['port'])
            
        if 'address' in data:
            update_fields.append("address = %s")
            params.append(data['address'])
            
        if 'status' in data:
            update_fields.append("status = %s")
            params.append(data['status'])
            
        if 'public_key' in data:
            update_fields.append("public_key = %s")
            params.append(data['public_key'])
            
        if 'private_key' in data:
            update_fields.append("private_key = %s")
            params.append(data['private_key'])
            
        if 'load_factor' in data:
            update_fields.append("load_factor = %s")
            params.append(data['load_factor'])
            
        if 'metrics_rating' in data:
            update_fields.append("metrics_rating = %s")
            params.append(data['metrics_rating'])
        
        # Если нет полей для обновления, возвращаем ошибку
        if not update_fields:
            conn.close()
            return jsonify({"error": "Не указаны поля для обновления"}), 400
        
        # Добавляем ID сервера в список параметров
        params.append(server_id)
        
        # Формируем и выполняем запрос на обновление
        update_query = f"""
            UPDATE servers
            SET {", ".join(update_fields)}, last_check = NOW()
            WHERE id = %s
            RETURNING id
        """
        
        cursor.execute(update_query, params)
        updated_server_id = cursor.fetchone()[0]
        
        # Если есть данные о местоположении, обновляем таблицу server_locations
        if ('latitude' in data and 'longitude' in data) or ('city' in data or 'country' in data):
            # Проверяем, существует ли запись в server_locations
            cursor.execute(
                """
                SELECT server_id FROM server_locations WHERE server_id = %s
                """,
                (server_id,)
            )
            
            location_exists = cursor.fetchone() is not None
            
            if location_exists:
                # Обновляем существующую запись
                location_update_fields = []
                location_params = []
                
                if 'latitude' in data:
                    location_update_fields.append("latitude = %s")
                    location_params.append(data['latitude'])
                
                if 'longitude' in data:
                    location_update_fields.append("longitude = %s")
                    location_params.append(data['longitude'])
                
                if 'city' in data:
                    location_update_fields.append("city = %s")
                    location_params.append(data['city'])
                
                if 'country' in data:
                    location_update_fields.append("country = %s")
                    location_params.append(data['country'])
                
                if location_update_fields:
                    location_update_fields.append("updated_at = NOW()")
                    location_params.append(server_id)
                    
                    location_update_query = f"""
                        UPDATE server_locations
                        SET {", ".join(location_update_fields)}
                        WHERE server_id = %s
                    """
                    
                    cursor.execute(location_update_query, location_params)
            else:
                # Создаем новую запись только если есть координаты
                if 'latitude' in data and 'longitude' in data:
                    cursor.execute(
                        """
                        INSERT INTO server_locations
                        (server_id, latitude, longitude, city, country, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            server_id,
                            data.get('latitude'),
                            data.get('longitude'),
                            data.get('city'),
                            data.get('country')
                        )
                    )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "server_id": updated_server_id}), 200
    except Exception as e:
        logger.error(f"Ошибка при обновлении сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

        
# @app.route('/servers/register', methods=['POST'])
# def register_server():
#     """Регистрирует новый сервер в базе данных."""
#     data = request.json
    
#     required_fields = ['geolocation_id', 'endpoint', 'port', 'public_key', 'address']
#     if not all(field in data for field in required_fields):
#         return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         # Проверяем, существует ли уже сервер с таким endpoint и портом
#         cursor.execute(
#             """
#             SELECT id FROM servers WHERE endpoint = %s AND port = %s
#             """,
#             (data.get('endpoint'), data.get('port'))
#         )
        
#         existing_server = cursor.fetchone()
#         if existing_server:
#             conn.close()
#             return jsonify({"error": "Сервер с таким endpoint и портом уже существует", "server_id": existing_server[0]}), 409
        
#         # Вставляем запись в таблицу servers
#         cursor.execute(
#             """
#             INSERT INTO servers
#             (geolocation_id, endpoint, port, public_key, private_key, address, status, last_check, created_at)
#             VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
#             RETURNING id
#             """,
#             (
#                 data.get('geolocation_id'),
#                 data.get('endpoint'),
#                 data.get('port'),
#                 data.get('public_key'),
#                 data.get('private_key', 'private_key_placeholder'),
#                 data.get('address')
#             )
#         )
        
#         server_id = cursor.fetchone()[0]
        
#         # Если предоставлены координаты, вставляем запись в server_locations
#         if 'latitude' in data and 'longitude' in data:
#             cursor.execute(
#                 """
#                 INSERT INTO server_locations
#                 (server_id, latitude, longitude, city, country, updated_at)
#                 VALUES (%s, %s, %s, %s, %s, NOW())
#                 """,
#                 (
#                     server_id,
#                     data.get('latitude'),
#                     data.get('longitude'),
#                     data.get('city'),
#                     data.get('country')
#                 )
#             )
        
#         conn.commit()
#         conn.close()
        
#         return jsonify({"status": "success", "server_id": server_id}), 201
#     except Exception as e:
#         logger.error(f"Ошибка при регистрации сервера: {str(e)}")
#         return jsonify({"error": str(e)}), 500
        
@app.route('/configs/change_geolocation', methods=['POST'])
def change_config_geolocation():
    """Изменение геолокации для активной конфигурации."""
    data = request.json
    
    required_fields = ['user_id', 'geolocation_id', 'server_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    geolocation_id = data.get('geolocation_id')
    server_id = data.get('server_id')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем активную конфигурацию
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = %s AND active = TRUE",
            (user_id,)
        )
        
        active_config = cursor.fetchone()
        if not active_config:
            conn.close()
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
        
        # Получаем конфигурацию для выбранного сервера
        cursor.execute(
            """
            SELECT uc.* 
            FROM user_configurations uc
            WHERE uc.user_id = %s AND uc.server_id = %s
            ORDER BY uc.created_at DESC
            LIMIT 1
            """,
            (user_id, server_id)
        )
        
        server_config = cursor.fetchone()
        
        # Если конфигурации для выбранного сервера нет, создаём её
        if not server_config:
            # Получаем детали сервера
            cursor.execute(
                """
                SELECT s.*, g.code as geo_code
                FROM servers s
                JOIN geolocations g ON s.geolocation_id = g.id
                WHERE s.id = %s
                """,
                (server_id,)
            )
            
            server = cursor.fetchone()
            if not server:
                conn.close()
                return jsonify({"error": "Выбранный сервер не найден"}), 404
            
            # Создаем новую конфигурацию для этого сервера
            # В реальном сценарии здесь был бы вызов к wireguard-service
            # для генерации конфигурации, для примера используем шаблон
            
            # Получаем данные текущей конфигурации
            public_key = active_config['public_key']
            
            # Создаем IP на основе user_id и server_id
            client_ip = f"10.{geolocation_id}.{server_id % 250}.{(user_id % 250) + 2}/24"
            
            # Создаем конфигурацию для нового сервера
            new_config_text = (
                f"[Interface]\n"
                f"# Клиентская конфигурация для VPN Duck\n"
                f"PrivateKey = <private_key_placeholder>\n"  # В реальном сценарии здесь будет приватный ключ клиента
                f"Address = {client_ip}\n"
                f"DNS = 1.1.1.1, 8.8.8.8\n\n"
                f"[Peer]\n"
                f"PublicKey = {server['public_key']}\n"
                f"Endpoint = {server['endpoint']}:{server['port']}\n"
                f"AllowedIPs = 0.0.0.0/0\n"
                f"PersistentKeepalive = 25\n"
            )
            
            # Сохраняем новую конфигурацию
            cursor.execute(
                """
                INSERT INTO user_configurations
                (user_id, config_id, server_id, config_text, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, config_text
                """,
                (user_id, active_config['id'], server_id, new_config_text, datetime.now())
            )
            
            server_config = cursor.fetchone()
        
        # Обновляем активную конфигурацию
        cursor.execute(
            """
            UPDATE configurations 
            SET config = %s, geolocation_id = %s, server_id = %s
            WHERE id = %s
            """,
            (server_config['config_text'], geolocation_id, server_id, active_config['id'])
        )
        
        conn.commit()
        
        # Получаем обновленную конфигурацию
        cursor.execute(
            """
            SELECT c.*, g.name as geolocation_name, s.endpoint as server_endpoint 
            FROM configurations c
            JOIN geolocations g ON c.geolocation_id = g.id
            JOIN servers s ON c.server_id = s.id
            WHERE c.id = %s
            """,
            (active_config['id'],)
        )
        
        updated_config = cursor.fetchone()
        
        # Преобразуем timestamp в строку для JSON-сериализации
        updated_config['expiry_time'] = updated_config['expiry_time'].isoformat()
        updated_config['created_at'] = updated_config['created_at'].isoformat()
        
        conn.close()
        
        return jsonify({"status": "success", "config": updated_config}), 200
    except Exception as e:
        logger.error(f"Ошибка при изменении геолокации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/configs/save_all', methods=['POST'])
def save_all_configs():
    """Сохранение всех конфигураций для пользователя."""
    data = request.json
    
    required_fields = ['user_id', 'configs', 'primary_geolocation_id', 'primary_server_id', 'client_public_key']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    configs = data.get('configs')
    primary_geolocation_id = data.get('primary_geolocation_id')
    primary_server_id = data.get('primary_server_id')
    client_public_key = data.get('client_public_key')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Деактивируем существующие конфигурации для этого пользователя
        cursor.execute(
            "UPDATE configurations SET active = FALSE WHERE user_id = %s",
            (user_id,)
        )
        
        # Находим конфигурацию для основного сервера
        primary_config_text = None
        for config in configs:
            if config.get('server_id') == primary_server_id:
                primary_config_text = config.get('config_text')
                break
        
        if not primary_config_text:
            return jsonify({"error": "Не найдена конфигурация для основного сервера"}), 400
        
        # Рассчитываем дату истечения (7 дней от текущей даты или берем из предыдущей конфигурации)
        expiry_time = data.get('expiry_time')
        if not expiry_time:
            # Ищем предыдущую активную конфигурацию
            cursor.execute(
                "SELECT expiry_time FROM configurations WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            prev_config = cursor.fetchone()
            if prev_config and prev_config[0]:
                expiry_time = prev_config[0]
            else:
                # Если предыдущей конфигурации нет, то 7 дней от текущей даты
                expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
        
        # Вставляем основную конфигурацию
        cursor.execute(
            """
            INSERT INTO configurations 
            (user_id, config, public_key, expiry_time, active, created_at, geolocation_id, server_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, primary_config_text, client_public_key, expiry_time, True, datetime.now(), 
             primary_geolocation_id, primary_server_id)
        )
        
        config_id = cursor.fetchone()[0]
        
        # Сохраняем все конфигурации в таблицу user_configurations
        for config in configs:
            server_id = config.get('server_id')
            config_text = config.get('config_text')
            
            cursor.execute(
                """
                INSERT INTO user_configurations 
                (user_id, config_id, server_id, config_text, created_at) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, config_id, server_id, config_text, datetime.now())
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "config_id": config_id}), 200
    except Exception as e:
        logger.error(f"Ошибка при сохранении конфигураций: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/configs/get_all/<int:user_id>', methods=['GET'])
def get_all_user_configs(user_id):
    """Получение всех конфигураций для пользователя."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем активную конфигурацию
        cursor.execute(
            """
            SELECT c.*, g.name as geolocation_name, g.code as geolocation_code, 
                   s.endpoint as server_endpoint, s.port as server_port
            FROM configurations c
            LEFT JOIN geolocations g ON c.geolocation_id = g.id
            LEFT JOIN servers s ON c.server_id = s.id
            WHERE c.user_id = %s AND c.active = TRUE
            """,
            (user_id,)
        )
        
        active_config = cursor.fetchone()
        if not active_config:
            conn.close()
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
        
        # Получаем все конфигурации для всех серверов
        cursor.execute(
            """
            SELECT uc.*, s.endpoint, s.port, g.code as geo_code, g.name as geo_name 
            FROM user_configurations uc
            JOIN servers s ON uc.server_id = s.id
            JOIN geolocations g ON s.geolocation_id = g.id
            WHERE uc.user_id = %s AND uc.config_id = %s
            """,
            (user_id, active_config['id'])
        )
        
        all_configs = cursor.fetchall()
        
        # Преобразуем timestamp в строку для JSON-сериализации
        active_config['expiry_time'] = active_config['expiry_time'].isoformat()
        active_config['created_at'] = active_config['created_at'].isoformat()
        
        for config in all_configs:
            config['created_at'] = config['created_at'].isoformat()
        
        conn.close()
        
        result = {
            "active_config": active_config,
            "all_configs": all_configs,
            "count": len(all_configs)
        }
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Ошибка при получении конфигураций: {str(e)}")
        return jsonify({"error": str(e)}), 500

#-------------------------
# Геолокации и сервера
#-------------------------

@app.route('/geolocations', methods=['GET'])
def get_geolocations():
    """Получает список всех геолокаций."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT g.*, 
                COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_servers_count
            FROM geolocations g
            LEFT JOIN servers s ON g.id = s.geolocation_id
            GROUP BY g.id
            ORDER BY g.name
            """
        )
        
        geolocations = cursor.fetchall()
        conn.close()
        
        return jsonify({"geolocations": geolocations}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении списка геолокаций: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/geolocations/available', methods=['GET'])
def get_available_geolocations():
    """Получает список доступных геолокаций."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT g.*, 
                COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_servers_count,
                AVG(s.metrics_rating) FILTER (WHERE s.status = 'active') AS avg_metrics_rating
            FROM geolocations g
            LEFT JOIN servers s ON g.id = s.geolocation_id
            WHERE g.available = TRUE
            GROUP BY g.id
            HAVING COUNT(s.id) FILTER (WHERE s.status = 'active') > 0
            ORDER BY g.name
            """
        )
        
        geolocations = cursor.fetchall()
        conn.close()
        
        return jsonify({"geolocations": geolocations}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении списка доступных геолокаций: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/geolocations/check', methods=['GET'])
def check_geolocations_availability():
    """Проверяет доступность геолокаций и обновляет их статус."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Обновляем доступность геолокаций на основе активных серверов
        cursor.execute(
            """
            WITH geo_servers AS (
                SELECT 
                    g.id,
                    COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_servers_count,
                    AVG(s.metrics_rating) FILTER (WHERE s.status = 'active') AS avg_metrics_rating
                FROM geolocations g
                LEFT JOIN servers s ON g.id = s.geolocation_id
                GROUP BY g.id
            )
            UPDATE geolocations g
            SET 
                available = (gs.active_servers_count > 0),
                avg_rating = COALESCE(gs.avg_metrics_rating, 0)
            FROM geo_servers gs
            WHERE g.id = gs.id
            RETURNING g.id, g.code, g.name, g.available
            """
        )
        
        updated_geolocations = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        return jsonify({"updated_geolocations": len(updated_geolocations)}), 200
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности геолокаций: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/geolocation/<int:geolocation_id>', methods=['GET'])
def get_servers_by_geolocation(geolocation_id):
    """Получает список серверов для заданной геолокации."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT s.*, sl.city, sl.country
            FROM servers s
            LEFT JOIN server_locations sl ON s.id = sl.server_id
            WHERE s.geolocation_id = %s AND s.status = 'active'
            ORDER BY s.load_factor ASC, s.metrics_rating DESC
            """,
            (geolocation_id,)
        )
        
        servers = cursor.fetchall()
        conn.close()
        
        return jsonify({"servers": servers}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/select_optimal', methods=['POST'])
def select_optimal_server_api():
    """API для выбора оптимального сервера для пользователя."""
    data = request.json
    
    user_id = data.get('user_id')
    geolocation_id = data.get('geolocation_id')
    ip_address = data.get('ip_address')
    
    if not user_id or not geolocation_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Если передан IP-адрес, обновляем информацию о местоположении пользователя
        if ip_address:
            determine_user_location(user_id, ip_address)
        
        # Получаем локацию пользователя
        user_location = determine_user_location(user_id)
        
        # Получаем предпочтения пользователя
        user_preferences = get_user_preferences(user_id)
        
        # Получаем все активные серверы в выбранной геолокации
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT s.*, sl.latitude, sl.longitude, sl.city,
                AVG(sm.latency) as avg_latency,
                AVG(sm.bandwidth) as avg_bandwidth,
                AVG(sm.jitter) as avg_jitter,
                AVG(sm.packet_loss) as avg_packet_loss
            FROM servers s
            LEFT JOIN server_locations sl ON s.id = sl.server_id
            LEFT JOIN server_metrics sm ON s.id = sm.server_id
            WHERE s.geolocation_id = %s AND s.status = 'active'
            GROUP BY s.id, sl.latitude, sl.longitude, sl.city
            """,
            (geolocation_id,)
        )
        
        servers = cursor.fetchall()
        
        if not servers:
            conn.close()
            return jsonify({"error": "Не удалось найти подходящие серверы в выбранной геолокации"}), 404
        
        # Рассчитываем рейтинг для каждого сервера
        for server in servers:
            # Базовый рейтинг - инвертированная нагрузка
            load_score = 1 - min(server.get('load_factor', 0) / 100, 1)
            
            # Рейтинг по задержке
            latency_score = 0.5
            if server.get('avg_latency'):
                latency_score = 1 - min(server.get('avg_latency', 0) / 500, 1)
            
            # Рейтинг по пропускной способности
            bandwidth_score = 0.5
            if server.get('avg_bandwidth'):
                bandwidth_score = min(server.get('avg_bandwidth', 0) / 1000, 1)
            
            # Рейтинг по джиттеру
            jitter_score = 0.5
            if server.get('avg_jitter'):
                jitter_score = 1 - min(server.get('avg_jitter', 0) / 100, 1)
            
            # Рейтинг по географической близости
            distance_score = 0.5
            if user_location and 'latitude' in user_location and 'longitude' in user_location and 'latitude' in server and 'longitude' in server:
                distance = calculate_distance(
                    user_location['latitude'], user_location['longitude'],
                    server['latitude'], server['longitude']
                )
                distance_score = 1 - min(distance / 5000, 1)
            
            # Рейтинг по предпочтениям пользователя
            preference_score = 0
            if user_preferences and user_preferences.get('preferred_server_id') == server['id']:
                preference_score = 1
            
            # Рассчитываем общий рейтинг с весами
            server['score'] = (
                0.3 * load_score +
                0.2 * latency_score +
                0.1 * bandwidth_score +
                0.1 * jitter_score +
                0.2 * distance_score +
                0.1 * preference_score
            )
        
        # Сортируем серверы по рейтингу и выбираем лучший
        servers.sort(key=lambda s: s.get('score', 0), reverse=True)
        optimal_server = servers[0]
        conn.close()
        
        return jsonify({"server": optimal_server}), 200
    except Exception as e:
        logger.error(f"Ошибка при выборе оптимального сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

#-------------------------
# Метрики и мониторинг
#-------------------------

@app.route('/servers/metrics/add', methods=['POST'])
def add_server_metrics():
    """Добавляет новые метрики сервера."""
    data = request.json
    
    server_id = data.get('server_id')
    latency = data.get('latency')
    jitter = data.get('jitter')
    packet_loss = data.get('packet_loss')
    bandwidth = data.get('bandwidth')
    
    if not server_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO server_metrics
            (server_id, latency, jitter, packet_loss, bandwidth, measured_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (server_id, latency, jitter, packet_loss, bandwidth)
        )
        
        metric_id = cursor.fetchone()[0]
        
        # Обновляем время последней проверки сервера
        cursor.execute(
            """
            UPDATE servers
            SET last_check = NOW()
            WHERE id = %s
            """,
            (server_id,)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "metric_id": metric_id}), 200
    except Exception as e:
        logger.error(f"Ошибка при добавлении метрик сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/metrics/analyze', methods=['POST'])
def analyze_servers_metrics():
    """Анализирует метрики серверов и обновляет их рейтинги."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем средние метрики за последние 24 часа
        cursor.execute(
            """
            WITH server_avg_metrics AS (
                SELECT 
                    server_id,
                    AVG(latency) as avg_latency,
                    AVG(jitter) as avg_jitter,
                    AVG(packet_loss) as avg_packet_loss,
                    AVG(bandwidth) as avg_bandwidth,
                    COUNT(*) as measurement_count
                FROM server_metrics
                WHERE measured_at > NOW() - INTERVAL '24 hours'
                GROUP BY server_id
            )
            UPDATE servers s
            SET 
                status = CASE
                    WHEN sam.avg_latency IS NULL THEN 'inactive'
                    WHEN sam.avg_packet_loss > 10 THEN 'degraded'
                    ELSE 'active'
                END,
                metrics_rating = CASE
                    WHEN sam.avg_latency IS NULL THEN 0
                    ELSE (
                        (1 - LEAST(sam.avg_latency / 500, 1)) * 0.4 +
                        (1 - LEAST(COALESCE(sam.avg_jitter, 50) / 100, 1)) * 0.2 +
                        (1 - LEAST(COALESCE(sam.avg_packet_loss, 5) / 20, 1)) * 0.2 +
                        LEAST(COALESCE(sam.avg_bandwidth, 10) / 100, 1) * 0.2
                    ) * 100
                END
            FROM server_avg_metrics sam
            WHERE s.id = sam.server_id
            RETURNING s.id, s.status, s.metrics_rating
            """
        )
        
        updated_servers = cursor.fetchall()
        
        # Обновляем связанные таблицы (геолокации, рейтинги серверов и т.д.)
        cursor.execute(
            """
            WITH geo_servers AS (
                SELECT 
                    g.id,
                    COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_servers_count,
                    AVG(s.metrics_rating) FILTER (WHERE s.status = 'active') AS avg_metrics_rating
                FROM geolocations g
                LEFT JOIN servers s ON g.id = s.geolocation_id
                GROUP BY g.id
            )
            UPDATE geolocations g
            SET 
                available = (gs.active_servers_count > 0),
                avg_rating = COALESCE(gs.avg_metrics_rating, 0)
            FROM geo_servers gs
            WHERE g.id = gs.id
            """
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "updated_servers": len(updated_servers)
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при анализе метрик: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/<int:server_id>/metrics', methods=['GET'])
def get_server_metrics(server_id):
    """Получает метрики сервера."""
    hours = request.args.get('hours', default=24, type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем средние метрики
        cursor.execute(
            """
            SELECT 
                AVG(latency) as avg_latency,
                AVG(jitter) as avg_jitter,
                AVG(packet_loss) as avg_packet_loss,
                AVG(bandwidth) as avg_bandwidth,
                COUNT(*) as measurement_count,
                MIN(measured_at) as first_measurement,
                MAX(measured_at) as last_measurement
            FROM server_metrics
            WHERE server_id = %s AND measured_at > NOW() - INTERVAL '%s hours'
            """,
            (server_id, hours)
        )
        
        metrics = cursor.fetchone()
        
        # Получаем историю метрик с разбивкой по часам
        cursor.execute(
            """
            SELECT 
                DATE_TRUNC('hour', measured_at) as hour,
                AVG(latency) as avg_latency,
                AVG(jitter) as avg_jitter,
                AVG(packet_loss) as avg_packet_loss,
                AVG(bandwidth) as avg_bandwidth,
                COUNT(*) as measurement_count
            FROM server_metrics
            WHERE server_id = %s AND measured_at > NOW() - INTERVAL '%s hours'
            GROUP BY DATE_TRUNC('hour', measured_at)
            ORDER BY hour
            """,
            (server_id, hours)
        )
        
        metrics_history = cursor.fetchall()
        
        # Преобразуем временные метки в строки
        for item in metrics_history:
            item['hour'] = item['hour'].isoformat()
        
        if metrics and 'first_measurement' in metrics and metrics['first_measurement']:
            metrics['first_measurement'] = metrics['first_measurement'].isoformat()
        if metrics and 'last_measurement' in metrics and metrics['last_measurement']:
            metrics['last_measurement'] = metrics['last_measurement'].isoformat()
        
        conn.close()
        
        return jsonify({
            "metrics": metrics,
            "history": metrics_history
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при получении метрик сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/update_metrics', methods=['POST'])
def update_server_metrics_api():
    """API для обновления метрик сервера."""
    data = request.json
    
    server_id = data.get('server_id')
    endpoint = data.get('endpoint')
    
    if not server_id or not endpoint:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Запускаем измерение метрик в отдельном потоке
        threading.Thread(
            target=measure_server_metrics,
            args=(server_id, endpoint),
            daemon=True
        ).start()
        
        return jsonify({"status": "success", "message": "Обновление метрик запущено"}), 200
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления метрик сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

#-------------------------
# Миграция пользователей
#-------------------------

@app.route('/configs/migrate_users', methods=['POST'])
def migrate_users_from_inactive_servers():
    """Мигрирует пользователей с неактивных серверов на активные."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Находим пользователей, которые используют неактивные серверы
        cursor.execute(
            """
            SELECT DISTINCT c.id, c.user_id, c.server_id, c.geolocation_id
            FROM configurations c
            JOIN servers s ON c.server_id = s.id
            WHERE c.active = TRUE AND s.status != 'active'
            """
        )
        
        configs_to_migrate = cursor.fetchall()
        
        if not configs_to_migrate:
            conn.close()
            return jsonify({"message": "Нет пользователей для миграции"}), 200
        
        migrated_count = 0
        
        # Мигрируем каждого пользователя на другой активный сервер в той же геолокации
        for config_id, user_id, server_id, geolocation_id in configs_to_migrate:
            # Находим новый активный сервер в той же геолокации
            cursor.execute(
                """
                SELECT id 
                FROM servers 
                WHERE geolocation_id = %s AND status = 'active'
                ORDER BY load_factor ASC, metrics_rating DESC
                LIMIT 1
                """,
                (geolocation_id,)
            )
            
            new_server = cursor.fetchone()
            
            if not new_server:
                # Если нет активных серверов в этой геолокации, 
                # пробуем найти сервер в любой другой доступной геолокации
                cursor.execute(
                    """
                    SELECT s.id, s.geolocation_id
                    FROM servers s
                    JOIN geolocations g ON s.geolocation_id = g.id
                    WHERE s.status = 'active' AND g.available = TRUE
                    ORDER BY s.load_factor ASC, s.metrics_rating DESC
                    LIMIT 1
                    """
                )
                
                new_server_data = cursor.fetchone()
                
                if not new_server_data:
                    # Если нет активных серверов вообще, пропускаем этого пользователя
                    continue
                
                new_server_id, new_geolocation_id = new_server_data
                
                # Обновляем геолокацию и сервер пользователя
                cursor.execute(
                    """
                    UPDATE configurations
                    SET server_id = %s, geolocation_id = %s
                    WHERE id = %s
                    """,
                    (new_server_id, new_geolocation_id, config_id)
                )
                
                # Регистрируем миграцию
                cursor.execute(
                    """
                    INSERT INTO server_migrations
                    (user_id, from_server_id, to_server_id, migration_reason)
                    VALUES (%s, %s, %s, 'server_down')
                    """,
                    (user_id, server_id, new_server_id)
                )
            else:
                new_server_id = new_server[0]
                
                # Обновляем сервер пользователя
                cursor.execute(
                    """
                    UPDATE configurations
                    SET server_id = %s
                    WHERE id = %s
                    """,
                    (new_server_id, config_id)
                )
                
                # Регистрируем миграцию
                cursor.execute(
                    """
                    INSERT INTO server_migrations
                    (user_id, from_server_id, to_server_id, migration_reason)
                    VALUES (%s, %s, %s, 'server_down')
                    """,
                    (user_id, server_id, new_server_id)
                )
            
            migrated_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({"migrated": migrated_count}), 200
    except Exception as e:
        logger.error(f"Ошибка при миграции пользователей: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/rebalance', methods=['POST'])
def rebalance_servers_api():
    """API для перебалансировки нагрузки серверов."""
    data = request.json
    
    geolocation_id = data.get('geolocation_id')
    threshold = data.get('threshold', 80)
    
    if not geolocation_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Обновляем факторы нагрузки серверов
        updated_count = update_server_load_factors()
        
        # Выполняем перебалансировку
        migrated_count = rebalance_server_load(geolocation_id, threshold)
        
        return jsonify({
            "status": "success", 
            "updated_servers": updated_count,
            "migrated_users": migrated_count
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при перебалансировке серверов: {str(e)}")
        return jsonify({"error": str(e)}), 500

def update_server_load_factors():
    """Обновляет факторы нагрузки серверов на основе активных соединений."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Рассчитываем нагрузку на основе количества активных соединений и трафика
        cursor.execute(
            """
            WITH server_loads AS (
                SELECT 
                    server_id,
                    COUNT(*) as connection_count,
                    SUM(bytes_sent + bytes_received) as total_traffic
                FROM active_connections
                WHERE last_activity > NOW() - INTERVAL '10 minutes'
                GROUP BY server_id
            )
            UPDATE servers s
            SET load_factor = COALESCE(
                -- Нормализуем значение к диапазону [0, 100]
                LEAST(
                    (sl.connection_count * 5) + (sl.total_traffic / 1000000000), 
                    100
                ),
                0
            )
            FROM server_loads sl
            WHERE s.id = sl.server_id
            RETURNING s.id, s.load_factor
            """
        )
        
        updated_servers = cursor.fetchall()
        conn.commit()
        conn.close()
        
        return len(updated_servers)
    except Exception as e:
        logger.error(f"Ошибка при обновлении факторов нагрузки: {str(e)}")
        return 0

def rebalance_server_load(geolocation_id, threshold=80):
    """Перераспределяет пользователей с перегруженных серверов."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Находим перегруженные серверы
        cursor.execute(
            """
            SELECT id, endpoint, load_factor
            FROM servers
            WHERE geolocation_id = %s AND status = 'active' AND load_factor > %s
            ORDER BY load_factor DESC
            """,
            (geolocation_id, threshold)
        )
        
        overloaded_servers = cursor.fetchall()
        
        if not overloaded_servers:
            conn.close()
            return 0
        
        # Находим недогруженные серверы
        cursor.execute(
            """
            SELECT id, endpoint, load_factor
            FROM servers
            WHERE geolocation_id = %s AND status = 'active' AND load_factor < %s
            ORDER BY load_factor ASC
            """,
            (geolocation_id, threshold / 2)
        )
        
        underloaded_servers = cursor.fetchall()
        
        if not underloaded_servers:
            conn.close()
            return 0
        
        migrated_count = 0
        
        # Для каждого перегруженного сервера находим пользователей для миграции
        for overloaded_server in overloaded_servers:
            # Определяем сколько пользователей нужно мигрировать
            target_reduction = (overloaded_server['load_factor'] - threshold) / 5  # Примерно 5% нагрузки на пользователя
            users_to_migrate = max(1, int(target_reduction))
            
            # Находим пользователей для миграции
            cursor.execute(
                """
                SELECT ac.id, ac.user_id
                FROM active_connections ac
                WHERE ac.server_id = %s AND ac.last_activity > NOW() - INTERVAL '30 minutes'
                ORDER BY ac.last_activity ASC
                LIMIT %s
                """,
                (overloaded_server['id'], users_to_migrate)
            )
            
            users = cursor.fetchall()
            
            for user in users:
                # Выбираем недогруженный сервер с наименьшей нагрузкой
                target_server = underloaded_servers[0]
                
                # Создаем новую запись в таблице миграций
                cursor.execute(
                    """
                    INSERT INTO server_migrations (user_id, from_server_id, to_server_id, migration_reason)
                    VALUES (%s, %s, %s, 'load_balancing')
                    """,
                    (user['user_id'], overloaded_server['id'], target_server['id'])
                )
                
                # Обновляем конфигурацию пользователя
                cursor.execute(
                    """
                    UPDATE configurations
                    SET server_id = %s
                    WHERE user_id = %s AND active = TRUE
                    """,
                    (target_server['id'], user['user_id'])
                )
                
                # Обновляем нагрузку серверов для балансировки следующих миграций
                target_server['load_factor'] += 5  # Примерное увеличение
                overloaded_server['load_factor'] -= 5  # Примерное уменьшение
                
                # Переупорядочиваем недогруженные серверы
                underloaded_servers.sort(key=lambda s: s['load_factor'])
                
                migrated_count += 1
        
        conn.commit()
        conn.close()
        
        return migrated_count
    except Exception as e:
        logger.error(f"Ошибка при балансировке нагрузки: {str(e)}")
        return 0

@app.route('/users/analyze_preferences', methods=['POST'])
def analyze_user_preferences_api():
    """API для анализа предпочтений пользователя."""
    data = request.json
    
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Анализируем историю подключений пользователя
        preferences = analyze_user_connection_history(user_id)
        
        if not preferences:
            return jsonify({"error": "Недостаточно данных для анализа предпочтений"}), 404
        
        return jsonify({"preferences": preferences}), 200
    except Exception as e:
        logger.error(f"Ошибка при анализе предпочтений пользователя: {str(e)}")
        return jsonify({"error": str(e)}), 500

def analyze_user_connection_history(user_id):
    """Анализирует историю подключений пользователя для выявления предпочтений."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем историю подключений пользователя за последние 30 дней
    cursor.execute(
        """
        SELECT 
            server_id,
            geolocation_id,
            COUNT(*) as connection_count,
            AVG(duration) as avg_duration,
            AVG(connection_quality) as avg_quality,
            EXTRACT(HOUR FROM connected_at) as hour_of_day
        FROM user_connections
        WHERE user_id = %s AND connected_at > NOW() - INTERVAL '30 days'
        GROUP BY server_id, geolocation_id, EXTRACT(HOUR FROM connected_at)
        ORDER BY connection_count DESC, avg_quality DESC
        """,
        (user_id,)
    )
    
    connections = cursor.fetchall()
    
    if not connections:
        conn.close()
        return None
    
    # Определяем предпочитаемый сервер и геолокацию
    preferred_server_id = connections[0]['server_id']
    preferred_geolocation_id = connections[0]['geolocation_id']
    
    # Определяем предпочитаемое время суток
    hour_counts = {}
    for conn_data in connections:
        hour = int(conn_data['hour_of_day'])
        hour_counts[hour] = hour_counts.get(hour, 0) + conn_data['connection_count']
    
    peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
    preferred_time_start = peak_hours[0][0] if peak_hours else None
    preferred_time_end = (preferred_time_start + 3) % 24 if preferred_time_start is not None else None
    
    # Сохраняем предпочтения пользователя
    cursor.execute(
        """
        INSERT INTO user_preferences 
        (user_id, preferred_server_id, preferred_geolocation_id, preferred_time_start, preferred_time_end, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET preferred_server_id = EXCLUDED.preferred_server_id,
            preferred_geolocation_id = EXCLUDED.preferred_geolocation_id,
            preferred_time_start = EXCLUDED.preferred_time_start,
            preferred_time_end = EXCLUDED.preferred_time_end,
            updated_at = NOW()
        """,
        (
            user_id, 
            preferred_server_id, 
            preferred_geolocation_id, 
            f"{preferred_time_start}:00" if preferred_time_start is not None else None,
            f"{preferred_time_end}:00" if preferred_time_end is not None else None
        )
    )
    
    conn.commit()
    conn.close()
    
    return {
        'preferred_server_id': preferred_server_id,
        'preferred_geolocation_id': preferred_geolocation_id,
        'preferred_time_start': preferred_time_start,
        'preferred_time_end': preferred_time_end
    }

#-------------------------
# Запуск приложения
#-------------------------

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=5002)