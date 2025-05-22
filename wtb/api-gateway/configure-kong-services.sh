#!/bin/bash
# Новый файл: wtb/configure-kong-services.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Настройка сервисов Kong ===${NC}"

# Параметры подключения к Kong
KONG_ADMIN_URL="http://localhost:8001"
ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY:-fvcfq9d3ycefnvmftiaso}

# Функция для проверки доступности Kong Admin API
check_kong_admin() {
    echo -e "${YELLOW}Проверка доступности Kong Admin API...${NC}"
    
    for i in {1..30}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${KONG_ADMIN_URL}/status")
        if [ "${HTTP_CODE}" = "200" ]; then
            echo -e "${GREEN}Kong Admin API доступен!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Попытка $i: Kong Admin API недоступен (код: ${HTTP_CODE}), ожидание 5 секунд...${NC}"
        sleep 5
    done
    
    echo -e "${RED}Kong Admin API недоступен после 30 попыток${NC}"
    return 1
}

# Функция для создания сервиса
create_service() {
    local service_name=$1
    local service_url=$2
    local service_host=$3
    local service_port=$4
    
    echo -e "${YELLOW}Создание сервиса: ${service_name}${NC}"
    
    # Удаляем существующий сервис, если есть
    curl -s -X DELETE "${KONG_ADMIN_URL}/services/${service_name}" > /dev/null 2>&1 || true
    
    # Создаем новый сервис
    RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/services" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"${service_name}\",
            \"url\": \"${service_url}\",
            \"protocol\": \"http\",
            \"host\": \"${service_host}\",
            \"port\": ${service_port},
            \"path\": \"/\",
            \"retries\": 5,
            \"connect_timeout\": 10000,
            \"write_timeout\": 10000,
            \"read_timeout\": 10000
        }")
    
    if echo "${RESPONSE}" | grep -q "error"; then
        echo -e "${RED}Ошибка создания сервиса ${service_name}: ${RESPONSE}${NC}"
        return 1
    else
        echo -e "${GREEN}Сервис ${service_name} создан успешно${NC}"
        return 0
    fi
}

# Функция для создания маршрута
create_route() {
    local service_name=$1
    local route_name=$2
    local route_path=$3
    local strip_path=${4:-false}
    local priority=${5:-100}
    
    echo -e "${YELLOW}Создание маршрута: ${route_name} для сервиса ${service_name}${NC}"
    
    # Удаляем существующий маршрут, если есть
    curl -s -X DELETE "${KONG_ADMIN_URL}/routes/${route_name}" > /dev/null 2>&1 || true
    
    # Создаем новый маршрут
    RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/services/${service_name}/routes" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"${route_name}\",
            \"protocols\": [\"http\", \"https\"],
            \"paths\": [\"${route_path}\"],
            \"strip_path\": ${strip_path},
            \"preserve_host\": false,
            \"regex_priority\": ${priority}
        }")
    
    if echo "${RESPONSE}" | grep -q "error"; then
        echo -e "${RED}Ошибка создания маршрута ${route_name}: ${RESPONSE}${NC}"
        return 1
    else
        echo -e "${GREEN}Маршрут ${route_name} создан успешно${NC}"
        return 0
    fi
}

# Функция для создания потребителя (consumer)
create_consumer() {
    local consumer_name=$1
    local api_key=$2
    
    echo -e "${YELLOW}Создание потребителя: ${consumer_name}${NC}"
    
    # Удаляем существующего потребителя, если есть
    curl -s -X DELETE "${KONG_ADMIN_URL}/consumers/${consumer_name}" > /dev/null 2>&1 || true
    
    # Создаем нового потребителя
    RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/consumers" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"${consumer_name}\"
        }")
    
    if echo "${RESPONSE}" | grep -q "error"; then
        echo -e "${RED}Ошибка создания потребителя ${consumer_name}: ${RESPONSE}${NC}"
        return 1
    fi
    
    # Добавляем API ключ для потребителя
    RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/consumers/${consumer_name}/key-auth" \
        -H "Content-Type: application/json" \
        -d "{
            \"key\": \"${api_key}\"
        }")
    
    if echo "${RESPONSE}" | grep -q "error"; then
        echo -e "${RED}Ошибка добавления API ключа для ${consumer_name}: ${RESPONSE}${NC}"
        return 1
    else
        echo -e "${GREEN}Потребитель ${consumer_name} создан с API ключом${NC}"
        return 0
    fi
}

# Функция для создания плагина key-auth
create_key_auth_plugin() {
    echo -e "${YELLOW}Настройка плагина key-auth...${NC}"
    
    # Удаляем существующий плагин, если есть
    EXISTING_PLUGINS=$(curl -s "${KONG_ADMIN_URL}/plugins" | grep -o '"name":"key-auth"' || true)
    if [ ! -z "${EXISTING_PLUGINS}" ]; then
        echo -e "${YELLOW}Удаление существующих плагинов key-auth...${NC}"
        curl -s "${KONG_ADMIN_URL}/plugins" | grep -B10 -A10 '"name":"key-auth"' | grep '"id"' | cut -d'"' -f4 | while read plugin_id; do
            curl -s -X DELETE "${KONG_ADMIN_URL}/plugins/${plugin_id}" > /dev/null 2>&1 || true
        done
    fi
    
    # Создаем глобальный плагин key-auth
    RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/plugins" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "key-auth",
            "config": {
                "key_names": ["apikey"],
                "hide_credentials": true,
                "key_in_body": false,
                "run_on_preflight": true
            }
        }')
    
    if echo "${RESPONSE}" | grep -q "error"; then
        echo -e "${RED}Ошибка создания плагина key-auth: ${RESPONSE}${NC}"
        return 1
    else
        echo -e "${GREEN}Плагин key-auth настроен успешно${NC}"
        return 0
    fi
}

# Главная функция настройки
main() {
    # Проверяем доступность Kong
    if ! check_kong_admin; then
        echo -e "${RED}Kong Admin API недоступен. Убедитесь, что Kong запущен.${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Начало настройки сервисов Kong...${NC}"
    
    # 1. Создаем сервис database-service
    if create_service "database-service" "http://database-service:5002" "database-service" "5002"; then
        # Создаем маршруты для database-service
        create_route "database-service" "database-api-route" "/api" "false" "200"
        create_route "database-service" "database-health-route" "/health" "false" "100"
    fi
    
    # 2. Создаем сервис wireguard-proxy
    if create_service "wireguard-proxy" "http://wireguard-proxy:5001" "wireguard-proxy" "5001"; then
        # Создаем маршруты для wireguard-proxy
        create_route "wireguard-proxy" "wireguard-vpn-route" "/vpn" "true" "200"
        create_route "wireguard-proxy" "wireguard-health-route" "/wg-health" "true" "100"
    fi
    
    # 3. Настраиваем аутентификацию
    echo -e "${YELLOW}Настройка аутентификации...${NC}"
    
    # Создаем потребителя admin
    create_consumer "admin" "${ADMIN_SECRET_KEY}"
    
    # Настраиваем плагин key-auth
    create_key_auth_plugin
    
    # 4. Проверяем настроенные сервисы
    echo -e "${YELLOW}Проверка настроенных сервисов...${NC}"
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
    
    # 5. Проверяем настроенные маршруты
    echo -e "${YELLOW}Проверка настроенных маршрутов...${NC}"
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
    
    echo -e "${GREEN}Настройка Kong завершена успешно!${NC}"
    echo -e "${BLUE}Теперь можно тестировать endpoints:${NC}"
    echo -e "  curl -H \"apikey: ${ADMIN_SECRET_KEY}\" http://localhost:8000/api/servers"
    echo -e "  curl -H \"apikey: ${ADMIN_SECRET_KEY}\" http://localhost:8000/vpn/servers"
    echo -e "  curl -H \"apikey: ${ADMIN_SECRET_KEY}\" http://localhost:8000/health"
}

# Запуск главной функции
main "$@"