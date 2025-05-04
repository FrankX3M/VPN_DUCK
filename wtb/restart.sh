
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
# docker compose down --remove-orphans

# жеское удаление с томами
docker compose down -v --remove-orphans

docker compose build --no-cache
# docker buildx build --no-cache

docker compose up -d

chmod +x setup.sh
./setup.sh

# Небольшая пауза перед получением логов
print_step "Ожидание 5 секунд перед получением логов..."
sleep 5


# docker compose exec database-service bash -c "chmod +x setup_database.sh && ./setup_database.sh"

# Получение логов
print_step "Вывод логов Docker Compose"
docker compose logs

# Завершение скрипта
print_step "Скрипт завершен"

# Очистка системы Docker
print_step "Очистка системы Docker (включая неиспользуемые образы)"


# Очистка томов
print_step "Очистка неиспользуемых томов Docker"
docker system prune -a --volumes -f


# пересоздание контейнеров с удалением логов
# docker compose up --force-recreate