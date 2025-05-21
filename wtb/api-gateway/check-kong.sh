#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Проверка Kong API Gateway ===${NC}"

# Параметры подключения к Kong
KONG_ADMIN_URL="http://kong:8001"

# Проверка доступности Kong
echo -e "${YELLOW}Проверка доступности Kong Admin API...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${KONG_ADMIN_URL}")
echo -e "HTTP Code: ${HTTP_CODE}"

# Проверка статуса Kong
echo -e "${YELLOW}Получение информации о Kong...${NC}"
curl -s "${KONG_ADMIN_URL}/status" | jq . || echo "Ошибка запроса статуса"

# Проверка сервисов
echo -e "${YELLOW}Получение списка сервисов...${NC}"
curl -s "${KONG_ADMIN_URL}/services" | jq . || echo "Ошибка запроса сервисов"

# Проверка маршрутов
echo -e "${YELLOW}Получение списка маршрутов...${NC}"
curl -s "${KONG_ADMIN_URL}/routes" | jq . || echo "Ошибка запроса маршрутов"

# Проверка плагинов
echo -e "${YELLOW}Получение списка плагинов...${NC}"
curl -s "${KONG_ADMIN_URL}/plugins" | jq . || echo "Ошибка запроса плагинов"

echo -e "${GREEN}Проверка Kong API Gateway завершена!${NC}"
exit 0