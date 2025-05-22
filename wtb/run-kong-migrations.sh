#!/bin/bash
# Путь: wtb/run-kong-migrations.sh
set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Запуск миграций Kong ===${NC}"

# Переменные окружения
KONG_DB_PASSWORD=${KONG_DB_PASSWORD:-kong_pass}
NETWORK_NAME=${COMPOSE_PROJECT_NAME:-wtb}_vpn_network

# Функция для проверки доступности базы данных Kong
check_kong_db() {
    echo -e "${YELLOW}Проверка доступности базы данных Kong...${NC}"
    
    docker run --rm \
        --network ${NETWORK_NAME} \
        postgres:11 \
        pg_isready -h kong-database -U kong
        
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}База данных Kong доступна!${NC}"
        return 0
    else
        echo -e "${RED}База данных Kong недоступна!${NC}"
        return 1
    fi
}

# Функция для выполнения миграций
run_migrations() {
    echo -e "${YELLOW}Выполнение миграций Kong...${NC}"
    
    # Bootstrap миграций (создание схемы)
    echo -e "${YELLOW}Выполнение bootstrap миграций...${NC}"
    docker run --rm \
        --network ${NETWORK_NAME} \
        -e "KONG_DATABASE=postgres" \
        -e "KONG_PG_HOST=kong-database" \
        -e "KONG_PG_USER=kong" \
        -e "KONG_PG_PASSWORD=${KONG_DB_PASSWORD}" \
        -e "KONG_PG_DATABASE=kong" \
        kong:3.9-ubuntu kong migrations bootstrap --yes
    
    # Up миграций (применение всех миграций)
    echo -e "${YELLOW}Применение миграций...${NC}"
    docker run --rm \
        --network ${NETWORK_NAME} \
        -e "KONG_DATABASE=postgres" \
        -e "KONG_PG_HOST=kong-database" \
        -e "KONG_PG_USER=kong" \
        -e "KONG_PG_PASSWORD=${KONG_DB_PASSWORD}" \
        -e "KONG_PG_DATABASE=kong" \
        kong:3.9-ubuntu kong migrations up --yes
    
    # Finish миграций (завершение процесса)
    echo -e "${YELLOW}Завершение миграций...${NC}"
    docker run --rm \
        --network ${NETWORK_NAME} \
        -e "KONG_DATABASE=postgres" \
        -e "KONG_PG_HOST=kong-database" \
        -e "KONG_PG_USER=kong" \
        -e "KONG_PG_PASSWORD=${KONG_DB_PASSWORD}" \
        -e "KONG_PG_DATABASE=kong" \
        kong:3.9-ubuntu kong migrations finish --yes
}

# Функция для проверки статуса миграций
check_migrations_status() {
    echo -e "${YELLOW}Проверка статуса миграций...${NC}"
    
    docker run --rm \
        --network ${NETWORK_NAME} \
        -e "KONG_DATABASE=postgres" \
        -e "KONG_PG_HOST=kong-database" \
        -e "KONG_PG_USER=kong" \
        -e "KONG_PG_PASSWORD=${KONG_DB_PASSWORD}" \
        -e "KONG_PG_DATABASE=kong" \
        kong:3.9-ubuntu kong migrations list
}

# Основная логика
main() {
    # Проверяем доступность базы данных
    if ! check_kong_db; then
        echo -e "${RED}Не удалось подключиться к базе данных Kong${NC}"
        exit 1
    fi
    
    # Выполняем миграции
    if run_migrations; then
        echo -e "${GREEN}Миграции Kong успешно выполнены!${NC}"
    else
        echo -e "${RED}Ошибка при выполнении миграций Kong${NC}"
        exit 1
    fi
    
    # Проверяем статус миграций
    echo -e "${YELLOW}Финальная проверка статуса миграций:${NC}"
    check_migrations_status
    
    echo -e "${GREEN}Миграции Kong завершены успешно!${NC}"
}

# Запуск основной функции
main "$@"