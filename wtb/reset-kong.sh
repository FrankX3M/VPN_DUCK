#!/bin/bash
# Новый файл: wtb/reset-kong.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Сброс и перезапуск Kong ===${NC}"

# Остановка и удаление контейнеров Kong
echo -e "${YELLOW}Остановка контейнеров Kong...${NC}"
docker compose stop kong konga kong-migration konga-prepare 2>/dev/null || true
docker compose rm -f kong konga kong-migration konga-prepare 2>/dev/null || true

# Очистка orphan контейнеров
echo -e "${YELLOW}Очистка orphan контейнеров...${NC}"
docker compose down --remove-orphans 2>/dev/null || true

# Удаление данных Kong (опционально)
read -p "Удалить данные Kong и Konga? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Удаление томов данных Kong и Konga...${NC}"
    docker volume rm wtb_kong-data wtb_konga-data 2>/dev/null || true
fi

# Пересборка образов Kong
echo -e "${YELLOW}Пересборка образа Kong...${NC}"
docker compose build --no-cache kong

# Запуск базы данных Kong
echo -e "${YELLOW}Запуск базы данных Kong...${NC}"
docker compose up -d kong-database konga-database

# Ожидание готовности базы данных
echo -e "${YELLOW}Ожидание готовности базы данных Kong...${NC}"
sleep 10

# Запуск миграций
echo -e "${YELLOW}Запуск миграций Kong...${NC}"
docker compose up kong-migration

# Проверка статуса миграций
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Миграции выполнены успешно!${NC}"
else
    echo -e "${RED}Ошибка выполнения миграций${NC}"
    exit 1
fi

# Запуск Kong Gateway
echo -e "${YELLOW}Запуск Kong Gateway...${NC}"
docker compose up -d kong

# Ожидание готовности Kong
echo -e "${YELLOW}Ожидание готовности Kong Gateway...${NC}"
sleep 15

# Подготовка и запуск Konga
echo -e "${YELLOW}Подготовка и запуск Konga...${NC}"
docker compose up konga-prepare
docker compose up -d konga

echo -e "${GREEN}Сброс и перезапуск Kong завершен успешно!${NC}"
echo -e "${BLUE}Проверьте доступность сервисов:${NC}"
echo -e "  Kong Admin API: http://localhost:8001"
echo -e "  Kong Proxy: http://localhost:8000"
echo -e "  Konga UI: http://localhost:1337"