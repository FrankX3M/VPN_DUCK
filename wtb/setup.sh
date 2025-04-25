#!/bin/bash
# setup.sh - Скрипт для первичной настройки системы управления удаленными серверами WireGuard

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Первичная настройка системы управления удаленными серверами WireGuard ===${NC}"

# Проверка наличия необходимых инструментов
for cmd in docker docker compose curl git; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Ошибка: Команда $cmd не найдена. Пожалуйста, установите $cmd и попробуйте снова.${NC}"
        exit 1
    fi
done

echo -e "${GREEN}Все необходимые инструменты установлены.${NC}"

chmod +x database-service/setup_database.sh

chmod +x database-service/wait-for-postgres.sh

chmod +x wireguard-proxy/setup.sh

chmod +x wireguard-proxy/proxy_server.py

docker compose exec db psql -U postgres -d wireguard -c 

echo -e "${GREEN}Все файлы успешно созданы и настроены.${NC}"

# Запуск системы
echo -e "${YELLOW}Запуск контейнеров Docker...${NC}"
docker compose up -d db

# Ожидание запуска БД
echo -e "${YELLOW}Ожидание запуска PostgreSQL...${NC}"
sleep 10

# Инициализация БД
echo -e "${YELLOW}Инициализация базы данных...${NC}"
docker compose run --rm database-service ./setup_database.sh

# Запуск остальных сервисов
echo -e "${YELLOW}Запуск всех сервисов...${NC}"
docker compose up -d

echo -e "${GREEN}=== Первичная настройка системы успешно завершена ===${NC}"

# docker compose exec database-service bash -c "chmod +x setup_database.sh && ./setup_database.sh"




