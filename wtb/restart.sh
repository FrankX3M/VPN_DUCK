
#!/bin/bash

# Функция для вывода цветных сообщений
print_step() {
    echo -e "\e[32m[STEP]\e[0m $1"
}

# Очистка системы Docker
print_step "Очистка системы Docker (включая неиспользуемые образы)"
docker system prune -a -f

# Очистка томов
print_step "Очистка неиспользуемых томов Docker"
docker system prune -a --volumes -f

# Остановка и удаление существующих контейнеров
print_step "Остановка и удаление существующих контейнеров"
docker compose down --remove-orphans

# Сборка новых образов без кэша
print_step "Сборка новых образов без использования кэша"
docker compose build --no-cache

# Запуск контейнеров в фоновом режиме
print_step "Запуск контейнеров"
docker compose up -d

# Небольшая пауза перед получением логов
print_step "Ожидание 5 секунд перед получением логов..."
sleep 5

# Получение логов
print_step "Вывод логов Docker Compose"
docker compose logs

# Завершение скрипта
print_step "Скрипт завершен"

# Очистка системы Docker
print_step "Очистка системы Docker (включая неиспользуемые образы)"
docker system prune -a -f

# Очистка томов
print_step "Очистка неиспользуемых томов Docker"
docker system prune -a --volumes -f
