#!/bin/bash

# Функция для вывода цветных сообщений
print_step() {
    echo -e "\e[32m[STEP]\e[0m $1"
}

print_error() {
    echo -e "\e[31m[ERROR]\e[0m $1"
}

print_info() {
    echo -e "\e[34m[INFO]\e[0m $1"
}

print_warn() {
    echo -e "\e[33m[WARNING]\e[0m $1"
}

# Остановка всех контейнеров
print_step "Остановка всех контейнеров"
docker compose down
docker compose build --no-cache 

# Запуск контейнеров в правильном порядке
print_step "Запуск контейнеров в правильном порядке"
print_info "1. Запуск базы данных Kong"
docker compose up -d kong-database
print_info "Ожидание запуска базы данных (30 секунд)..."
sleep 30

# Запуск миграции Kong
print_step "Запуск миграции Kong"
docker compose up -d kong-migration
print_info "Ожидание завершения миграции (20 секунд)..."
sleep 20

# Запуск Kong
print_step "Запуск Kong"
docker compose up -d kong
print_info "Ожидание запуска Kong (15 секунд)..."
sleep 15

# Запуск Konga
print_step "Запуск Konga с memory-adapter"
docker compose up -d konga
print_info "Ожидание запуска Konga (30 секунд)..."
sleep 30

# Проверка логов konga
print_step "Проверка логов konga"
docker compose logs --tail=30 konga

# Проверка статуса контейнера
print_step "Проверка статуса контейнера konga"
KONGA_STATUS=$(docker ps -f name=konga --format '{{.Status}}')
if echo "$KONGA_STATUS" | grep -q "Up"; then
    print_info "Konga с memory-adapter работает: $KONGA_STATUS"
    print_warn "Обратите внимание, что Konga использует хранение в памяти и все данные будут потеряны при перезапуске контейнера"
else
    print_error "Konga с memory-adapter не запущен: $KONGA_STATUS"
fi

# Запуск остальных контейнеров
print_step "Запуск остальных контейнеров"
docker compose up -d

print_step "Скрипт завершен"
docker system prune -a --volumes -f