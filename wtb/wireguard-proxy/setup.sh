#!/bin/bash
# setup.sh - Скрипт для инициализации wireguard-proxy

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Инициализация wireguard-proxy ===${NC}"

# Создание необходимых директорий
echo -e "${YELLOW}Создание структуры директорий...${NC}"
mkdir -p utils auth config data
mkdir -p utils/logs

# Копирование файлов конфигурации
echo -e "${YELLOW}Настройка конфигурационных файлов...${NC}"

# Создание config/__init__.py
cat > config/__init__.py << 'PYINIT'
from config.settings import (
    SERVER_HOST, 
    SERVER_PORT, 
    DEBUG,
    DATABASE_SERVICE_URL,
    CACHE_MAX_SIZE,
    CACHE_TTL,
    HTTP_TIMEOUT,
    HTTP_MAX_RETRIES,
    HTTP_RETRY_BACKOFF,
    ROUTING_STRATEGY,
    ROUTING_GEOLOCATION_PRIORITY,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE
)

__all__ = [
    "SERVER_HOST", 
    "SERVER_PORT", 
    "DEBUG",
    "DATABASE_SERVICE_URL",
    "CACHE_MAX_SIZE",
    "CACHE_TTL",
    "HTTP_TIMEOUT",
    "HTTP_MAX_RETRIES",
    "HTTP_RETRY_BACKOFF",
    "ROUTING_STRATEGY",
    "ROUTING_GEOLOCATION_PRIORITY",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_FILE"
]
PYINIT

# Создание auth/__init__.py
cat > auth/__init__.py << 'PYINIT'
from auth.auth_handler import get_auth_headers, revoke_auth_token, init_auth_handler, get_auth_status

__all__ = ["get_auth_headers", "revoke_auth_token", "init_auth_handler", "get_auth_status"]
PYINIT

# Создание utils/__init__.py
cat > utils/__init__.py << 'PYINIT'
# Инициализация модуля utils
PYINIT

echo -e "${GREEN}Структура директорий и конфигурационные файлы созданы.${NC}"

# Установка прав доступа
chmod +x proxy_server.py
echo -e "${GREEN}Права доступа установлены.${NC}"

echo -e "${GREEN}=== Инициализация wireguard-proxy успешно завершена ===${NC}"
echo -e "${YELLOW}Для запуска сервиса выполните: python proxy_server.py${NC}"