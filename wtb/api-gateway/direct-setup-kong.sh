#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Настройка Kong API Gateway напрямую ===${NC}"

# Параметры подключения к Kong
KONG_ADMIN_URL="http://kong:8001"
CONFIG_FILE="/app/api-gateway/kong.yml"

# Проверка доступности Kong
echo -e "${YELLOW}Проверка доступности Kong Admin API...${NC}"
for i in {1..30}; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${KONG_ADMIN_URL}")
  if [ "${HTTP_CODE}" = "200" ]; then
    echo -e "${GREEN}Kong Admin API доступен!${NC}"
    break
  else
    echo -e "${YELLOW}Попытка $i: Kong Admin API недоступен (${HTTP_CODE}), ожидание 5 секунд...${NC}"
    sleep 5
  fi

  if [ $i -eq 30 ]; then
    echo -e "${RED}Kong Admin API недоступен после 30 попыток. Выход.${NC}"
    exit 1
  fi
done

# Создание сервисов напрямую через API
echo -e "${YELLOW}Настройка сервиса database-service...${NC}"
curl -s -X PUT ${KONG_ADMIN_URL}/services/database-service \
  -d name=database-service \
  -d url=http://database-service:5002 \
  -d retries=5 \
  -d connect_timeout=5000 \
  -d write_timeout=10000 \
  -d read_timeout=10000

echo -e "${YELLOW}Настройка маршрутов для database-service...${NC}"
curl -s -X PUT ${KONG_ADMIN_URL}/services/database-service/routes/database-api-route \
  -d protocols=http,https \
  -d paths=/api \
  -d strip_path=false \
  -d preserve_host=true \
  -d regex_priority=200

curl -s -X PUT ${KONG_ADMIN_URL}/services/database-service/routes/database-root-route \
  -d protocols=http,https \
  -d paths=/ \
  -d strip_path=false \
  -d preserve_host=true \
  -d regex_priority=100

echo -e "${YELLOW}Настройка сервиса wireguard-proxy...${NC}"
curl -s -X PUT ${KONG_ADMIN_URL}/services/wireguard-proxy \
  -d name=wireguard-proxy \
  -d url=http://wireguard-proxy:5001 \
  -d retries=5 \
  -d connect_timeout=5000 \
  -d write_timeout=10000 \
  -d read_timeout=10000

echo -e "${YELLOW}Настройка маршрутов для wireguard-proxy...${NC}"
curl -s -X PUT ${KONG_ADMIN_URL}/services/wireguard-proxy/routes/wireguard-api-route \
  -d protocols=http,https \
  -d paths=/vpn \
  -d strip_path=false \
  -d preserve_host=true \
  -d regex_priority=200

curl -s -X PUT ${KONG_ADMIN_URL}/services/wireguard-proxy/routes/wireguard-health-route \
  -d protocols=http,https \
  -d paths=/health \
  -d strip_path=false \
  -d preserve_host=true \
  -d regex_priority=100

# Настройка плагина key-auth глобально
echo -e "${YELLOW}Настройка аутентификации...${NC}"
curl -s -X PUT ${KONG_ADMIN_URL}/plugins/key-auth-global \
  -d name=key-auth \
  -d config.key_names=apikey \
  -d config.hide_credentials=true

# Проверка настройки
echo -e "${YELLOW}Проверка настроенных сервисов Kong...${NC}"
SERVICES=$(curl -s "${KONG_ADMIN_URL}/services" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g')

if [ -z "${SERVICES}" ]; then
  echo -e "${RED}Сервисы не настроены!${NC}"
  exit 1
else
  echo -e "${GREEN}Настроенные сервисы:${NC}"
  echo "${SERVICES}" | while read -r SERVICE; do
    echo -e "  - ${SERVICE}"
  done
fi

echo -e "${YELLOW}Проверка настроенных маршрутов Kong...${NC}"
ROUTES=$(curl -s "${KONG_ADMIN_URL}/routes" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g')

if [ -z "${ROUTES}" ]; then
  echo -e "${RED}Маршруты не настроены!${NC}"
  exit 1
else
  echo -e "${GREEN}Настроенные маршруты:${NC}"
  echo "${ROUTES}" | while read -r ROUTE; do
    echo -e "  - ${ROUTE}"
  done
fi

echo -e "${GREEN}Настройка Kong API Gateway успешно завершена!${NC}"
exit 0