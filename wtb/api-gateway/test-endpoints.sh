#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Тестирование Kong API Gateway endpoints ===${NC}"

# Параметры подключения к Kong
KONG_PROXY_URL="http://kong:8000"
ADMIN_SECRET_KEY="${ADMIN_SECRET_KEY:-fvcfq9d3ycefnvmftiaso}"

# Функция для тестирования endpoint
test_endpoint() {
    local url=$1
    local name=$2
    
    echo -e "${YELLOW}Тестирование $name: $url ${NC}"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "apikey: $ADMIN_SECRET_KEY" "${url}")
    echo -e "HTTP Code: ${HTTP_CODE}"
    
    if [ "${HTTP_CODE}" = "200" ]; then
        echo -e "${GREEN}Успех!${NC}"
        curl -s -H "apikey: $ADMIN_SECRET_KEY" "${url}" | head -c 300
        echo -e "\n${GREEN}(показаны первые 300 символов ответа)${NC}"
    else
        echo -e "${RED}Ошибка!${NC}"
        curl -s -H "apikey: $ADMIN_SECRET_KEY" "${url}" || echo "Ошибка выполнения запроса"
    fi
    echo -e "\n"
}

# Тестирование endpoints
test_endpoint "${KONG_PROXY_URL}/api/servers" "Database Servers API"
test_endpoint "${KONG_PROXY_URL}/api/servers/all" "Database All Servers API"
test_endpoint "${KONG_PROXY_URL}/api/servers/active" "Database Active Servers API"
test_endpoint "${KONG_PROXY_URL}/vpn/servers" "Wireguard Servers API"
test_endpoint "${KONG_PROXY_URL}/vpn/health" "Wireguard Health API"
test_endpoint "${KONG_PROXY_URL}/health" "Health API"

echo -e "${GREEN}Тестирование Kong API Gateway endpoints завершено!${NC}"
exit 0