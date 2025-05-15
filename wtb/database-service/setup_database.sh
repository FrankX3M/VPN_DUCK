#!/bin/bash
# setup_database.sh - Скрипт для инициализации базы данных для системы управления удаленными серверами WireGuard

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Инициализация базы данных для системы управления удаленными серверами WireGuard ===${NC}"

# Параметры подключения к PostgreSQL
DB_HOST=${POSTGRES_HOST:-"db"}
DB_PORT=${POSTGRES_PORT:-"5432"}
DB_NAME=${POSTGRES_DB:-"wireguard"}
DB_USER=${POSTGRES_USER:-"postgres"}
DB_PASS=${POSTGRES_PASSWORD:-"postgres"}

# Функция для подключения к базе данных
run_psql() {
  PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

# Проверка доступности PostgreSQL
echo -e "${YELLOW}Проверка доступности PostgreSQL (${DB_HOST}:${DB_PORT})...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if run_psql -c '\q' 2>/dev/null; then
        echo -e "${GREEN}PostgreSQL доступен!${NC}"
        break
    fi
    attempt=$((attempt+1))
    echo -e "${YELLOW}Попытка $attempt из $max_attempts: PostgreSQL недоступен, ожидание...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}Не удалось подключиться к PostgreSQL после $max_attempts попыток. Выход.${NC}"
    exit 1
fi

# Создание временного SQL-файла для инициализации базы данных
SQL_FILE="init_database_$(date +%Y%m%d%H%M%S).sql"

cat > "$SQL_FILE" << 'SQL_CONTENT'
-- init_database.sql
-- Полная схема базы данных для системы управления удаленными серверами WireGuard

-- Создание базовых таблиц

-- Таблица для хранения геолокаций (должна быть создана перед remote_servers)
CREATE TABLE IF NOT EXISTS geolocations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    avg_rating FLOAT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения информации о пирах WireGuard (должна быть создана перед peer_server_mapping)
CREATE TABLE IF NOT EXISTS peers (
    id SERIAL PRIMARY KEY,
    public_key VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_handshake TIMESTAMP WITH TIME ZONE,
    transfer_rx BIGINT DEFAULT 0,
    transfer_tx BIGINT DEFAULT 0
);

-- Таблица для хранения информации о внешних серверах
CREATE TABLE IF NOT EXISTS remote_servers (
    id SERIAL PRIMARY KEY,
    server_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    api_url VARCHAR(255) NOT NULL,
    geolocation_id INTEGER REFERENCES geolocations(id),
    auth_type VARCHAR(20) DEFAULT 'api_key',
    api_key VARCHAR(255),
    oauth_client_id VARCHAR(255),
    oauth_client_secret VARCHAR(255),
    oauth_token_url VARCHAR(255),
    hmac_secret VARCHAR(255),
    max_peers INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Добавление новых полей в существующую таблицу remote_servers
ALTER TABLE remote_servers ADD COLUMN IF NOT EXISTS endpoint VARCHAR(255);
ALTER TABLE remote_servers ADD COLUMN IF NOT EXISTS port INTEGER;
ALTER TABLE remote_servers ADD COLUMN IF NOT EXISTS address VARCHAR(255);
ALTER TABLE remote_servers ADD COLUMN IF NOT EXISTS public_key VARCHAR(255);
ALTER TABLE remote_servers ADD COLUMN IF NOT EXISTS api_path VARCHAR(255) DEFAULT '/status';
ALTER TABLE remote_servers ADD COLUMN IF NOT EXISTS skip_api_check BOOLEAN DEFAULT FALSE;

-- Создание индексов для remote_servers
CREATE INDEX IF NOT EXISTS idx_remote_servers_geolocation_id ON remote_servers(geolocation_id);
CREATE INDEX IF NOT EXISTS idx_remote_servers_is_active ON remote_servers(is_active);
CREATE INDEX IF NOT EXISTS idx_remote_servers_status ON remote_servers(is_active);

-- Добавление поля server_id в таблицу peers для обратной совместимости
ALTER TABLE peers ADD COLUMN IF NOT EXISTS server_id INTEGER REFERENCES remote_servers(id);

-- Таблица для хранения метрик удаленных серверов
CREATE TABLE IF NOT EXISTS remote_server_metrics (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES remote_servers(id) ON DELETE CASCADE,
    peers_count INTEGER DEFAULT 0,
    cpu_load FLOAT DEFAULT 0,
    memory_usage FLOAT DEFAULT 0,
    network_in BIGINT DEFAULT 0,
    network_out BIGINT DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    response_time FLOAT DEFAULT 0,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_remote_server_metrics_server_id ON remote_server_metrics(server_id);
CREATE INDEX IF NOT EXISTS idx_remote_server_metrics_collected_at ON remote_server_metrics(collected_at);

-- Таблица для маппинга пиров к удаленным серверам
CREATE TABLE IF NOT EXISTS peer_server_mapping (
    id SERIAL PRIMARY KEY,
    peer_id INTEGER REFERENCES peers(id) ON DELETE CASCADE,
    server_id INTEGER REFERENCES remote_servers(id) ON DELETE CASCADE,
    public_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (peer_id, server_id)
);

CREATE INDEX IF NOT EXISTS idx_peer_server_mapping_peer_id ON peer_server_mapping(peer_id);
CREATE INDEX IF NOT EXISTS idx_peer_server_mapping_server_id ON peer_server_mapping(server_id);
CREATE INDEX IF NOT EXISTS idx_peer_server_mapping_public_key ON peer_server_mapping(public_key);

-- Таблица для хранения конфигураций WireGuard
CREATE TABLE IF NOT EXISTS configurations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    config TEXT NOT NULL,
    public_key TEXT NOT NULL,
    expiry_time TIMESTAMP NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    geolocation_id INTEGER,
    server_id INTEGER
);

-- Таблица для хранения информации о платежах
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    config_id INTEGER REFERENCES configurations(id),
    stars_amount INTEGER NOT NULL,
    transaction_id TEXT,
    status TEXT NOT NULL,
    days_extended INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения информации о серверах
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
);

-- Таблица для хранения географических координат серверов
CREATE TABLE IF NOT EXISTS server_locations (
    server_id INTEGER PRIMARY KEY REFERENCES servers(id),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    city TEXT,
    country TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения информации о местоположении пользователей
CREATE TABLE IF NOT EXISTS user_locations (
    user_id INTEGER PRIMARY KEY,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    city TEXT,
    country TEXT,
    accuracy FLOAT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения метрик серверов
CREATE TABLE IF NOT EXISTS server_metrics (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    latency FLOAT,
    bandwidth FLOAT,
    jitter FLOAT,
    packet_loss FLOAT,
    measured_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения информации о активных соединениях
CREATE TABLE IF NOT EXISTS active_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    server_id INTEGER REFERENCES servers(id),
    connected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address TEXT,
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0
);

-- Таблица для хранения истории подключений пользователей
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
);

-- Таблица для хранения предпочтений пользователей
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    preferred_server_id INTEGER REFERENCES servers(id),
    preferred_geolocation_id INTEGER REFERENCES geolocations(id),
    preferred_time_start TIME,
    preferred_time_end TIME,
    preferred_connection_type TEXT,
    auto_connect BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения информации о миграциях пользователей между серверами
CREATE TABLE IF NOT EXISTS server_migrations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    from_server_id INTEGER REFERENCES servers(id),
    to_server_id INTEGER REFERENCES servers(id),
    migration_reason VARCHAR(50) NOT NULL,
    migration_time TIMESTAMP NOT NULL DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE
);

-- Таблица тестовых серверов для отладки
CREATE TABLE IF NOT EXISTS test_servers (
    id SERIAL PRIMARY KEY,
    server_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    endpoint TEXT NOT NULL,
    port INTEGER NOT NULL,
    public_key TEXT NOT NULL,
    geolocation_id INTEGER REFERENCES geolocations(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для хранения информации о конфигурациях пользователей
-- Обновленная версия с дополнительными полями для совместимости
CREATE TABLE IF NOT EXISTS user_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    config_id INTEGER REFERENCES configurations(id),
    server_id INTEGER REFERENCES servers(id),
    -- Новое поле для поддержки строковых идентификаторов серверов
    server_id_string VARCHAR(50),
    config_text TEXT NOT NULL,
    config TEXT,                                       -- Добавлено для совместимости
    public_key TEXT,                                   -- Добавлено для совместимости
    expiry_time TIMESTAMP,                             -- Добавлено для совместимости
    geolocation_id INTEGER REFERENCES geolocations(id), -- Добавлено для совместимости
    active BOOLEAN DEFAULT TRUE,                       -- Добавлено для совместимости
    updated_at TIMESTAMP DEFAULT NOW(),                -- Добавлено для совместимости
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица для связи между серверами и их удаленными аналогами
CREATE TABLE IF NOT EXISTS server_mapping (
    remote_server_id INTEGER PRIMARY KEY REFERENCES remote_servers(id) ON DELETE CASCADE,
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE
);

-- Добавление колонок в существующую таблицу user_configs если они не существуют
DO $$
BEGIN
    -- Проверяем и добавляем столбец 'config', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'config') THEN
        ALTER TABLE user_configs ADD COLUMN config TEXT;
        -- Обновляем значения в новом столбце
        UPDATE user_configs SET config = config_text;
    END IF;
    
    -- Проверяем и добавляем столбец 'public_key', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'public_key') THEN
        ALTER TABLE user_configs ADD COLUMN public_key TEXT;
    END IF;
    
    -- Проверяем и добавляем столбец 'expiry_time', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'expiry_time') THEN
        ALTER TABLE user_configs ADD COLUMN expiry_time TIMESTAMP;
    END IF;
    
    -- Проверяем и добавляем столбец 'geolocation_id', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'geolocation_id') THEN
        ALTER TABLE user_configs ADD COLUMN geolocation_id INTEGER REFERENCES geolocations(id);
    END IF;
    
    -- Проверяем и добавляем столбец 'active', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'active') THEN
        ALTER TABLE user_configs ADD COLUMN active BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- Проверяем и добавляем столбец 'updated_at', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'updated_at') THEN
        ALTER TABLE user_configs ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
        -- Обновляем значения в новом столбце
        UPDATE user_configs SET updated_at = created_at;
    END IF;
    
    -- Проверяем и добавляем столбец 'server_id_string', если он не существует
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_name = 'user_configs' AND column_name = 'server_id_string') THEN
        ALTER TABLE user_configs ADD COLUMN server_id_string VARCHAR(50);
    END IF;
END $$;

-- Создание представления для совместимости
CREATE OR REPLACE VIEW user_configs_view AS
SELECT
    id,
    user_id,
    config_id,
    server_id,
    server_id_string,
    COALESCE(config, config_text) as config,
    config_text,
    public_key,
    expiry_time,
    geolocation_id,
    active,
    updated_at,
    created_at
FROM
    user_configs;

-- Функция для безопасного преобразования ID сервера
CREATE OR REPLACE FUNCTION safe_cast_server_id(server_id_value TEXT)
RETURNS INTEGER AS $$
DECLARE
    server_id_int INTEGER;
BEGIN
    -- Попытка преобразовать в INTEGER
    BEGIN
        server_id_int := server_id_value::INTEGER;
        RETURN server_id_int;
    EXCEPTION WHEN OTHERS THEN
        -- Если не удалось преобразовать, возвращаем NULL
        RETURN NULL;
    END;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения ID сервера (для remote_servers)
CREATE OR REPLACE FUNCTION get_remote_server_id(server_identifier ANYELEMENT)
RETURNS INTEGER AS $$
DECLARE
    server_id_int INTEGER;
    server_id_str TEXT;
BEGIN
    -- Преобразуем входной параметр в текст для универсальности
    server_id_str := server_identifier::TEXT;
    
    -- Если входное значение является числом, ищем сначала по ID
    IF server_id_str ~ '^[0-9]+$' THEN
        -- Ищем в remote_servers по id
        SELECT id INTO server_id_int FROM remote_servers WHERE id = server_id_str::INTEGER;
        IF server_id_int IS NOT NULL THEN
            RETURN server_id_int;
        END IF;
    END IF;
    
    -- Ищем в remote_servers по server_id (строковому идентификатору)
    SELECT id INTO server_id_int FROM remote_servers WHERE server_id = server_id_str;
    
    -- Возвращаем найденный ID или NULL
    RETURN server_id_int;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения ID сервера по server_id или ID
CREATE OR REPLACE FUNCTION get_server_id(server_identifier ANYELEMENT)
RETURNS INTEGER AS $$
DECLARE
    server_id_int INTEGER;
    server_id_str TEXT;
BEGIN
    -- Преобразуем входной параметр в текст для универсальности
    server_id_str := server_identifier::TEXT;
    
    -- Если входное значение является числом, ищем сначала по ID
    IF server_id_str ~ '^[0-9]+$' THEN
        -- Проверяем, существует ли ID в таблице servers
        SELECT id INTO server_id_int FROM servers WHERE id = server_id_str::INTEGER;
        IF server_id_int IS NOT NULL THEN
            RETURN server_id_int;
        END IF;
    END IF;
    
    -- Ищем в test_servers по server_id
    SELECT id INTO server_id_int FROM test_servers WHERE server_id = server_id_str;
    IF server_id_int IS NOT NULL THEN
        RETURN server_id_int;
    END IF;
    
    -- Ищем в remote_servers по server_id
    SELECT id INTO server_id_int FROM remote_servers WHERE server_id = server_id_str;
    
    -- Возвращаем найденный ID или NULL
    RETURN server_id_int;
END;
$$ LANGUAGE plpgsql;

-- Функция для добавления метрик сервера
CREATE OR REPLACE FUNCTION add_server_metrics(
    p_server_id ANYELEMENT,
    p_latency FLOAT,
    p_bandwidth FLOAT,
    p_jitter FLOAT,
    p_packet_loss FLOAT,
    p_measured_at TIMESTAMP
) RETURNS INTEGER AS $$
DECLARE
    server_id_int INTEGER;
    metric_id INTEGER;
BEGIN
    -- Получаем числовой ID сервера
    server_id_int := get_remote_server_id(p_server_id);
    
    -- Если сервер не найден, возвращаем ошибку
    IF server_id_int IS NULL THEN
        RAISE EXCEPTION 'Server with identifier % not found', p_server_id;
    END IF;
    
    -- Вставляем метрики
    INSERT INTO server_metrics (
        server_id,
        latency,
        bandwidth,
        jitter,
        packet_loss,
        measured_at
    ) VALUES (
        server_id_int,
        p_latency,
        p_bandwidth,
        p_jitter,
        p_packet_loss,
        COALESCE(p_measured_at, NOW())
    ) RETURNING id INTO metric_id;
    
    RETURN metric_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для вставки конфигурации пользователя с поддержкой строковых идентификаторов серверов
CREATE OR REPLACE FUNCTION insert_user_config(
    p_user_id INTEGER,
    p_config TEXT,
    p_public_key TEXT,
    p_geolocation_id INTEGER,
    p_server_id TEXT,
    p_active BOOLEAN,
    p_expiry_time TIMESTAMP
) RETURNS INTEGER AS $$
DECLARE
    server_id_int INTEGER;
    new_config_id INTEGER;
BEGIN
    -- Попытка преобразовать server_id в число
    BEGIN
        server_id_int := p_server_id::INTEGER;
    EXCEPTION WHEN OTHERS THEN
        server_id_int := NULL;
    END;
    
    -- Вставка с учетом типа server_id
    INSERT INTO user_configs (
        user_id,
        config,
        public_key,
        geolocation_id,
        server_id,
        server_id_string,
        active,
        expiry_time,
        config_text
    ) VALUES (
        p_user_id,
        p_config,
        p_public_key,
        p_geolocation_id,
        server_id_int,
        CASE WHEN server_id_int IS NULL THEN p_server_id ELSE NULL END,
        p_active,
        p_expiry_time,
        p_config
    ) RETURNING id INTO new_config_id;
    
    RETURN new_config_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для синхронизации между remote_servers и servers
CREATE OR REPLACE FUNCTION sync_remote_server_to_server()
RETURNS TRIGGER AS $$
DECLARE
    server_id_val INTEGER;
BEGIN
    -- Проверяем, существует ли сервер с такими данными
    SELECT id INTO server_id_val FROM servers 
    WHERE endpoint = NEW.endpoint 
      AND port = NEW.port 
      AND public_key = NEW.public_key;
      
    -- Если сервер не найден, создаем новый
    IF server_id_val IS NULL THEN
        INSERT INTO servers (
            geolocation_id,
            endpoint,
            port,
            public_key,
            private_key,  -- здесь используем временный placeholder
            address,
            status
        ) VALUES (
            NEW.geolocation_id,
            NEW.endpoint,
            NEW.port,
            NEW.public_key,
            'placeholder_private_key',  -- замените на реальное значение или генерацию
            NEW.address,
            CASE WHEN NEW.is_active THEN 'active' ELSE 'inactive' END
        )
        RETURNING id INTO server_id_val;
    END IF;
    
    -- Добавляем запись в mapping
    INSERT INTO server_mapping (remote_server_id, server_id)
    VALUES (NEW.id, server_id_val)
    ON CONFLICT (remote_server_id) DO UPDATE
    SET server_id = server_id_val;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Добавление тестовых серверов для совместимости с кодом
INSERT INTO test_servers (server_id, name, endpoint, port, public_key, geolocation_id)
VALUES
    ('test-server-1', 'Test Server 1', 'test-us.example.com', 51820, 'test_public_key_1', 2),
    ('test-server-2', 'Test Server 2', 'test-eu.example.com', 51820, 'test_public_key_2', 3)
ON CONFLICT (server_id) DO NOTHING;

-- Создаем триггер для синхронизации
DROP TRIGGER IF EXISTS sync_servers_trigger ON remote_servers;
CREATE TRIGGER sync_servers_trigger
AFTER INSERT OR UPDATE ON remote_servers
FOR EACH ROW
EXECUTE FUNCTION sync_remote_server_to_server();

-- Триггер для автоматического обновления updated_at в user_configs
CREATE OR REPLACE FUNCTION update_user_configs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_configs_timestamp ON user_configs;
CREATE TRIGGER update_user_configs_timestamp
BEFORE UPDATE ON user_configs
FOR EACH ROW
EXECUTE FUNCTION update_user_configs_timestamp();

-- Создание функции для обновления timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Создание триггеров для обновления timestamps
DROP TRIGGER IF EXISTS update_remote_servers_timestamp ON remote_servers;
CREATE TRIGGER update_remote_servers_timestamp
BEFORE UPDATE ON remote_servers
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS update_peer_server_mapping_timestamp ON peer_server_mapping;
CREATE TRIGGER update_peer_server_mapping_timestamp
BEFORE UPDATE ON peer_server_mapping
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_configurations_user_id ON configurations(user_id);
CREATE INDEX IF NOT EXISTS idx_configurations_public_key ON configurations(public_key);
CREATE INDEX IF NOT EXISTS idx_configurations_expiry_time ON configurations(expiry_time);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_config_id ON payments(config_id);
CREATE INDEX IF NOT EXISTS idx_peers_user_id ON peers(user_id);
CREATE INDEX IF NOT EXISTS idx_peers_public_key ON peers(public_key);
CREATE INDEX IF NOT EXISTS idx_servers_geolocation_id ON servers(geolocation_id);
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);
CREATE INDEX IF NOT EXISTS idx_servers_metrics_rating ON servers(metrics_rating);
CREATE INDEX IF NOT EXISTS idx_geolocations_avg_rating ON geolocations(avg_rating);
CREATE INDEX IF NOT EXISTS idx_servers_last_check ON servers(last_check);
CREATE INDEX IF NOT EXISTS idx_server_metrics_server_id_measured_at ON server_metrics(server_id, measured_at);
CREATE INDEX IF NOT EXISTS idx_active_connections_user_id ON active_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_active_connections_server_id ON active_connections(server_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_user_id ON user_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_server_id ON user_connections(server_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_connected_at ON user_connections(connected_at);
CREATE INDEX IF NOT EXISTS idx_user_configs_user_id ON user_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_configs_server_id ON user_configs(server_id);
CREATE INDEX IF NOT EXISTS idx_user_configs_server_id_string ON user_configs(server_id_string);
CREATE INDEX IF NOT EXISTS idx_user_configs_active_updated_at ON user_configs(active, updated_at);
CREATE INDEX IF NOT EXISTS idx_server_mapping_remote_server_id ON server_mapping(remote_server_id);
CREATE INDEX IF NOT EXISTS idx_server_mapping_server_id ON server_mapping(server_id);
CREATE INDEX IF NOT EXISTS idx_test_servers_server_id ON test_servers(server_id);

-- Заполнение начальными данными

-- Добавление основных геолокаций
INSERT INTO geolocations (code, name, description, available, created_at)
VALUES 
    ('ru', 'Россия', 'Серверы в России', TRUE, NOW()),
    ('us', 'США', 'Серверы в США', TRUE, NOW()),
    ('eu', 'Европа', 'Серверы в странах Европы', TRUE, NOW()),
    ('asia', 'Азия', 'Серверы в странах Азии', TRUE, NOW())
ON CONFLICT (code) DO NOTHING;

-- Добавление тестового удаленного сервера
INSERT INTO remote_servers (
    server_id, 
    name, 
    location, 
    api_url, 
    geolocation_id, 
    auth_type, 
    api_key, 
    max_peers, 
    is_active
)
SELECT 
    'srv-test-001', 
    'Тестовый сервер', 
    'Москва, Россия', 
    'http://wireguard-service:5001', 
    g.id, 
    'api_key', 
    'test_api_key', 
    100, 
    TRUE
FROM 
    geolocations g 
WHERE 
    g.code = 'ru'
ON CONFLICT (server_id) DO NOTHING;

-- Обновление тестового сервера дополнительными полями
UPDATE remote_servers
SET 
    endpoint = 'wireguard-service',
    port = 51820,
    address = '10.0.0.1/24',
    public_key = 'test_public_key_placeholder',
    api_path = '/status',
    skip_api_check = FALSE
WHERE 
    server_id = 'srv-test-001';

-- Добавление тестового удаленного сервера с числовым ID для совместимости
-- Добавление тестового удаленного сервера с числовым ID для совместимости
INSERT INTO remote_servers (
   server_id, 
   name, 
   location, 
   api_url, 
   geolocation_id, 
   auth_type,
   api_key, 
   max_peers, 
   is_active,
   endpoint,
   port,
   address,
   public_key,
   api_path,
   skip_api_check
)
SELECT 
   '3', 
   'Тестовый сервер с числовым ID', 
   'Сеул, Корея', 
   'http://test-3.example.com:5000', 
   g.id, 
   'api_key',
   'test_api_key_3', 
   100, 
   TRUE,
   'test-3.example.com',
   51820,
   '10.0.0.3/24',
   'test_public_key_3',
   '/status',
   FALSE
FROM 
   geolocations g 
WHERE 
   g.code = 'asia'
ON CONFLICT (server_id) DO NOTHING;

-- Обновление существующих URL для API, если endpoint есть, но не задан api_url
UPDATE remote_servers 
SET api_url = CONCAT('http://', endpoint, ':5000')
WHERE endpoint IS NOT NULL AND (api_url IS NULL OR api_url = '');

-- Обновление API path для существующих записей без пути
UPDATE remote_servers 
SET api_path = '/status' 
WHERE api_path IS NULL;

-- Обновление информации для записей с URL порта 51820
UPDATE remote_servers 
SET api_url = REPLACE(api_url, ':51820', ':5000')
WHERE api_url LIKE '%:51820%';

-- Процедура синхронизации данных между таблицами
DO $$
DECLARE
   r RECORD;
BEGIN
   -- Для каждого удаленного сервера
   FOR r IN SELECT * FROM remote_servers WHERE endpoint IS NOT NULL AND port IS NOT NULL AND public_key IS NOT NULL LOOP
       -- Проверяем, существует ли сервер с такими же параметрами
       IF NOT EXISTS (SELECT 1 FROM servers 
                     WHERE endpoint = r.endpoint 
                       AND port = r.port 
                       AND public_key = r.public_key) THEN
           -- Вставляем новую запись в servers
           INSERT INTO servers (
               geolocation_id,
               endpoint,
               port,
               public_key,
               private_key,
               address,
               status
           ) VALUES (
               r.geolocation_id,
               r.endpoint,
               r.port,
               r.public_key,
               'placeholder_private_key', -- Заменить на реальное значение в продакшене
               r.address,
               CASE WHEN r.is_active THEN 'active' ELSE 'inactive' END
           );
       END IF;
   END LOOP;
   
   -- Обновляем маппинг между servers и remote_servers
   FOR r IN SELECT rs.id as remote_id, s.id as server_id FROM remote_servers rs 
            JOIN servers s ON rs.endpoint = s.endpoint AND rs.port = s.port AND rs.public_key = s.public_key LOOP
       -- Вставляем или обновляем запись в маппинге
       INSERT INTO server_mapping (remote_server_id, server_id)
       VALUES (r.remote_id, r.server_id)
       ON CONFLICT (remote_server_id) DO UPDATE
       SET server_id = r.server_id;
   END LOOP;
END $$;

-- Создание или обновление обертки для функций API с безопасной обработкой типов
DO $$
BEGIN
   -- Проверяем, существует ли тип user_config_input
   IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_config_input') THEN
       -- Создаем составной тип для входных параметров
       CREATE TYPE user_config_input AS (
           user_id INTEGER,
           config TEXT,
           public_key TEXT,
           geolocation_id INTEGER,
           server_id TEXT,
           active BOOLEAN,
           expiry_time TIMESTAMP
       );
   END IF;
   
   -- Проверяем, существует ли тип server_metric_input
   IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'server_metric_input') THEN
       -- Создаем составной тип для входных параметров метрик
       CREATE TYPE server_metric_input AS (
           server_id TEXT,
           latency FLOAT,
           bandwidth FLOAT,
           jitter FLOAT,
           packet_loss FLOAT,
           measured_at TIMESTAMP
       );
   END IF;
END $$;

-- Создаем оберточные функции для безопасной работы с API
CREATE OR REPLACE FUNCTION api_add_server_metrics(
   p_server_id TEXT,
   p_latency FLOAT,
   p_bandwidth FLOAT,
   p_jitter FLOAT,
   p_packet_loss FLOAT,
   p_measured_at TIMESTAMP DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
   server_id_int INTEGER;
   metric_id INTEGER;
BEGIN
   -- Проверяем, является ли p_server_id числом
   IF p_server_id ~ '^[0-9]+$' THEN
       BEGIN
           -- Если это число, ищем по id в remote_servers
           SELECT id INTO server_id_int FROM remote_servers WHERE id = p_server_id::INTEGER;
           IF server_id_int IS NULL THEN
               -- Если не найдено, значит это строка, ищем по server_id
               SELECT id INTO server_id_int FROM remote_servers WHERE server_id = p_server_id;
           END IF;
       EXCEPTION WHEN OTHERS THEN
           -- При ошибке преобразования, ищем по server_id
           SELECT id INTO server_id_int FROM remote_servers WHERE server_id = p_server_id;
       END;
   ELSE
       -- Если это строка, ищем по server_id
       SELECT id INTO server_id_int FROM remote_servers WHERE server_id = p_server_id;
   END IF;
   
   -- Если сервер не найден, создаем временную запись для метрик
   IF server_id_int IS NULL THEN
       INSERT INTO remote_servers (
           server_id,
           name,
           location,
           api_url,
           geolocation_id,
           is_active
       ) VALUES (
           p_server_id,
           'Unknown Server ' || p_server_id,
           'Unknown Location',
           'http://unknown.example.com',
           (SELECT id FROM geolocations WHERE code = 'ru' LIMIT 1),
           TRUE
       ) RETURNING id INTO server_id_int;
   END IF;
   
   -- Вставляем метрики
   INSERT INTO server_metrics (
       server_id,
       latency,
       bandwidth,
       jitter,
       packet_loss,
       measured_at
   ) VALUES (
       server_id_int,
       p_latency,
       p_bandwidth,
       p_jitter,
       p_packet_loss,
       COALESCE(p_measured_at, NOW())
   ) RETURNING id INTO metric_id;
   
   RETURN metric_id;
END;
$$ LANGUAGE plpgsql;

-- Создаем JSON-функцию для работы с API
CREATE OR REPLACE FUNCTION api_add_server_metrics_json(data JSONB)
RETURNS INTEGER AS $$
DECLARE
   metric_id INTEGER;
BEGIN
   RETURN api_add_server_metrics(
       data->>'server_id',
       (data->>'latency')::FLOAT,
       (data->>'bandwidth')::FLOAT,
       (data->>'jitter')::FLOAT,
       (data->>'packet_loss')::FLOAT,
       (data->>'measured_at')::TIMESTAMP
   );
END;
$$ LANGUAGE plpgsql;

-- Создаем обертку для search_server_by_id
CREATE OR REPLACE FUNCTION search_server_by_id(server_id_value TEXT)
RETURNS TABLE (
   id INTEGER,
   server_id TEXT,
   name TEXT,
   is_active BOOLEAN,
   found_in TEXT
) AS $$
BEGIN
   -- Сначала проверяем, есть ли сервер с таким числовым ID
   IF server_id_value ~ '^[0-9]+$' THEN
       -- Поиск в remote_servers по id
       RETURN QUERY
       SELECT rs.id, rs.server_id::TEXT, rs.name, rs.is_active, 'remote_servers (id)' AS found_in
       FROM remote_servers rs
       WHERE rs.id = server_id_value::INTEGER;
       
       -- Если найдено, выходим
       IF FOUND THEN
           RETURN;
       END IF;
   END IF;
   
   -- Поиск в remote_servers по server_id
   RETURN QUERY
   SELECT rs.id, rs.server_id::TEXT, rs.name, rs.is_active, 'remote_servers (server_id)' AS found_in
   FROM remote_servers rs
   WHERE rs.server_id = server_id_value;
   
   -- Если найдено, выходим
   IF FOUND THEN
       RETURN;
   END IF;
   
   -- Поиск в test_servers по server_id
   RETURN QUERY
   SELECT ts.id, ts.server_id::TEXT, ts.name, TRUE AS is_active, 'test_servers' AS found_in
   FROM test_servers ts
   WHERE ts.server_id = server_id_value;
   
   -- Если найдено, выходим
   IF FOUND THEN
       RETURN;
   END IF;
   
   -- Ничего не найдено, возвращаем пустой результат
   RETURN;
END;
$$ LANGUAGE plpgsql;
SQL_CONTENT

# Применение SQL-скрипта к базе данных
echo -e "${YELLOW}Применение SQL-скрипта к базе данных...${NC}"
run_psql -f "$SQL_FILE"

# Проверка результата выполнения SQL-скрипта
if [ $? -eq 0 ]; then
   echo -e "${GREEN}База данных успешно инициализирована!${NC}"
else
   echo -e "${RED}Ошибка при инициализации базы данных.${NC}"
   exit 1
fi

# Удаление временного SQL-файла
rm -f "$SQL_FILE"

echo -e "${BLUE}=== Проверка структуры базы данных ===${NC}"
echo -e "${YELLOW}Проверка наличия таблиц и новых полей...${NC}"

# Проверка наличия таблиц
TABLE_COUNT=$(run_psql -t -c "
   SELECT COUNT(*) FROM information_schema.tables 
   WHERE table_name IN ('remote_servers', 'peer_server_mapping', 'remote_server_metrics', 'server_mapping', 'user_configs', 'test_servers')
     AND table_schema = 'public';
")

if [ "$TABLE_COUNT" -eq 6 ]; then
   echo -e "${GREEN}Таблицы для работы с удаленными серверами успешно созданы!${NC}"
else
   echo -e "${YELLOW}Внимание: Не все ожидаемые таблицы были найдены (найдено $TABLE_COUNT из 6).${NC}"
fi

# Проверка наличия новых полей в таблице remote_servers
COLUMN_COUNT=$(run_psql -t -c "
   SELECT COUNT(*) FROM information_schema.columns 
   WHERE table_name = 'remote_servers' 
     AND table_schema = 'public'
     AND column_name IN ('endpoint', 'port', 'address', 'public_key', 'api_path', 'skip_api_check');
")

if [ "$COLUMN_COUNT" -eq 6 ]; then
   echo -e "${GREEN}Все необходимые поля в таблице remote_servers созданы успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Не все необходимые поля в таблице remote_servers были найдены (найдено $COLUMN_COUNT из 6).${NC}"
fi

# Проверка наличия новых полей в таблице user_configs
USER_CONFIGS_COLUMN_COUNT=$(run_psql -t -c "
   SELECT COUNT(*) FROM information_schema.columns 
   WHERE table_name = 'user_configs' 
     AND table_schema = 'public'
     AND column_name IN ('config', 'public_key', 'expiry_time', 'geolocation_id', 'active', 'updated_at', 'server_id_string');
")

if [ "$USER_CONFIGS_COLUMN_COUNT" -eq 7 ]; then
   echo -e "${GREEN}Все необходимые поля в таблице user_configs созданы успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Не все необходимые поля в таблице user_configs были найдены (найдено $USER_CONFIGS_COLUMN_COUNT из 7).${NC}"
fi

# Проверка наличия тестовых серверов
TEST_SERVERS_COUNT=$(run_psql -t -c "
   SELECT COUNT(*) FROM test_servers;
")

if [ "$TEST_SERVERS_COUNT" -ge 2 ]; then
   echo -e "${GREEN}Тестовые сервера успешно добавлены!${NC}"
else
   echo -e "${YELLOW}Внимание: Не все тестовые сервера были добавлены (найдено $TEST_SERVERS_COUNT, ожидалось не менее 2).${NC}"
fi

# Проверка наличия специальных серверов с числовыми ID
NUMERIC_ID_SERVER_COUNT=$(run_psql -t -c "
   SELECT COUNT(*) FROM remote_servers WHERE server_id = '3';
")

if [ "$NUMERIC_ID_SERVER_COUNT" -eq 1 ]; then
   echo -e "${GREEN}Тестовый сервер с числовым ID успешно добавлен!${NC}"
else
   echo -e "${YELLOW}Внимание: Тестовый сервер с числовым ID не был добавлен.${NC}"
fi

# Проверка наличия представления user_configs_view
VIEW_EXISTS=$(run_psql -t -c "
   SELECT COUNT(*) FROM information_schema.views 
   WHERE table_name = 'user_configs_view'
     AND table_schema = 'public';
")

if [ "$VIEW_EXISTS" -eq 1 ]; then
   echo -e "${GREEN}Представление user_configs_view создано успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Представление user_configs_view не было создано.${NC}"
fi

# Проверка наличия функции get_server_id
FUNC_EXISTS=$(run_psql -t -c "
   SELECT COUNT(*) FROM pg_proc
   WHERE proname = 'get_server_id';
")

if [ "$FUNC_EXISTS" -ge 1 ]; then
   echo -e "${GREEN}Функция get_server_id создана успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Функция get_server_id не была создана.${NC}"
fi

# Проверка наличия функции api_add_server_metrics
API_METRIC_FUNC_EXISTS=$(run_psql -t -c "
   SELECT COUNT(*) FROM pg_proc
   WHERE proname = 'api_add_server_metrics';
")

if [ "$API_METRIC_FUNC_EXISTS" -ge 1 ]; then
   echo -e "${GREEN}Функция api_add_server_metrics создана успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Функция api_add_server_metrics не была создана.${NC}"
fi

# Проверка наличия функции insert_user_config
FUNC_INSERT_EXISTS=$(run_psql -t -c "
   SELECT COUNT(*) FROM pg_proc
   WHERE proname = 'insert_user_config';
")

if [ "$FUNC_INSERT_EXISTS" -ge 1 ]; then
   echo -e "${GREEN}Функция insert_user_config создана успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Функция insert_user_config не была создана.${NC}"
fi

# Проверка наличия функции search_server_by_id
FUNC_SEARCH_EXISTS=$(run_psql -t -c "
   SELECT COUNT(*) FROM pg_proc
   WHERE proname = 'search_server_by_id';
")

if [ "$FUNC_SEARCH_EXISTS" -ge 1 ]; then
   echo -e "${GREEN}Функция search_server_by_id создана успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Функция search_server_by_id не была создана.${NC}"
fi

# Проверка наличия функции get_remote_server_id
FUNC_REMOTE_EXISTS=$(run_psql -t -c "
   SELECT COUNT(*) FROM pg_proc
   WHERE proname = 'get_remote_server_id';
")

if [ "$FUNC_REMOTE_EXISTS" -ge 1 ]; then
   echo -e "${GREEN}Функция get_remote_server_id создана успешно!${NC}"
else
   echo -e "${YELLOW}Внимание: Функция get_remote_server_id не была создана.${NC}"
fi

# Проверка синхронизации данных между таблицами
MAPPING_COUNT=$(run_psql -t -c "
   SELECT COUNT(*) FROM server_mapping;
")

if [ "$MAPPING_COUNT" -gt 0 ]; then
   echo -e "${GREEN}Маппинг между таблицами servers и remote_servers выполнен успешно!${NC}"
else
   echo -e "${YELLOW}Предупреждение: Маппинг между таблицами servers и remote_servers не был создан.${NC}"
fi

echo -e "${GREEN}=== Инициализация базы данных успешно завершена ===${NC}"
