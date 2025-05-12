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

-- Таблица для хранения информации о конфигурациях пользователей
CREATE TABLE IF NOT EXISTS user_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    config_id INTEGER REFERENCES configurations(id),
    server_id INTEGER REFERENCES servers(id),
    config_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

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
    WHERE table_name IN ('remote_servers', 'peer_server_mapping', 'remote_server_metrics')
      AND table_schema = 'public';
")

if [ "$TABLE_COUNT" -eq 3 ]; then
    echo -e "${GREEN}Таблицы для работы с удаленными серверами успешно созданы!${NC}"
else
    echo -e "${RED}Ошибка: Некоторые таблицы не были созданы. Проверьте журнал ошибок PostgreSQL.${NC}"
    exit 1
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
    echo -e "${RED}Ошибка: Некоторые поля в таблице remote_servers не были созданы. Проверьте журнал ошибок PostgreSQL.${NC}"
    exit 1
fi

# Проверка наличия тестовых данных
echo -e "${YELLOW}Проверка наличия тестовых данных...${NC}"
SERVER_COUNT=$(run_psql -t -c "
    SELECT COUNT(*) FROM remote_servers;
")

if [ "$SERVER_COUNT" -gt 0 ]; then
    echo -e "${GREEN}Тестовые данные успешно добавлены!${NC}"
else
    echo -e "${YELLOW}Предупреждение: Тестовые данные не были добавлены.${NC}"
fi

echo -e "${GREEN}=== Инициализация базы данных успешно завершена ===${NC}"
