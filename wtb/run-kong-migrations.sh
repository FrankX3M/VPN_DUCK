#!/bin/bash
set -e

echo "Запуск миграций Kong..."

# Проверяем, запущен ли контейнер kong-gateway
if docker ps | grep -q kong-gateway; then
    docker exec kong-gateway kong migrations bootstrap || echo "Миграции могут уже быть выполнены"
else
    echo "Контейнер kong-gateway не запущен. Запускаем миграции через отдельный контейнер..."
    docker run --rm \
        --network wtb_vpn_network \
        -e "KONG_DATABASE=postgres" \
        -e "KONG_PG_HOST=kong-database" \
        -e "KONG_PG_USER=kong" \
        -e "KONG_PG_PASSWORD=${KONG_DB_PASSWORD:-kong_pass}" \
        -e "KONG_PG_DATABASE=kong" \
        kong:3.9-ubuntu kong migrations bootstrap
fi

echo "Миграции Kong завершены"
