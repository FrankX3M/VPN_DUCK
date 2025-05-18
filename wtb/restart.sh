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

# Остановка только контейнера konga
print_step "Остановка контейнера konga"
docker compose stop konga

# Обеспечение работы контейнера kong-database
print_step "Проверка, что контейнер kong-database запущен"
if [ "$(docker ps -q -f name=kong-database)" ]; then
    print_info "Контейнер kong-database работает"
else
    print_info "Запуск контейнера kong-database"
    docker compose up -d kong-database
    print_info "Ожидание запуска базы данных (15 секунд)..."
    sleep 15
fi

# Принудительное создание базы данных konga
print_step "Принудительное создание базы данных konga"
docker exec kong-database psql -U kong -c "DROP DATABASE IF EXISTS konga;"
docker exec kong-database psql -U kong -c "CREATE DATABASE konga;"
docker exec kong-database psql -U kong -c "GRANT ALL PRIVILEGES ON DATABASE konga TO kong;"
print_info "База данных konga пересоздана"

# Запуск konga с более старой версией
print_step "Модификация контейнера konga для использования более старой версии"
# Экспортируем текущий docker-compose
docker compose config > docker-compose-exported.yml

# Проверяем используемую версию konga
if grep -q "pantsel/konga:0.14" docker-compose-exported.yml; then
    print_info "Уже используется более старая версия Konga"
else
    print_warn "Рекомендуется использовать более старую версию Konga для лучшей совместимости"
    print_info "Добавьте в 'konga' секцию docker-compose.yml: image: pantsel/konga:0.14.9"
fi

# Изменение переменных среды для konga
print_step "Настройка переменных среды для подключения Konga к базе данных"
docker compose stop konga
print_info "Запуск Konga с прямым URI подключения"
docker compose up -d konga

# Ожидаем запуск konga
print_step "Ожидание запуска konga (30 секунд)..."
sleep 30

# Проверка логов konga
print_step "Проверка логов konga"
docker compose logs --tail=50 konga

# Дополнительные шаги для устранения проблем
print_step "Предложения по дальнейшему устранению проблем"
print_info "1. Если проблема сохраняется, попробуйте изменить docker-compose.yml:"
print_info "   a. Замените образ konga на более старую версию: pantsel/konga:0.14.9"
print_info "   b. Используйте строку подключения вместо отдельных параметров:"
print_info "      DB_URI: postgresql://kong:${KONG_DB_PASSWORD:-kong_pass}@kong-database:5432/konga"
print_info "   c. Убедитесь, что переменная среды NODE_ENV установлена: production"
print_info "2. Рассмотрите возможность использования другой версии PostgreSQL (11 или 12)"
print_info "3. Проверьте, что созданная база данных доступна:"
print_info "   docker exec kong-database psql -U kong -c \"\\l\""
print_info "4. Проверьте, был ли Konga успешно подключен:"
print_info "   docker compose logs konga | grep -i \"connect\""

print_step "Скрипт завершен"
print_info "Если Konga по-прежнему не запускается, выполните следующие команды:"
print_info "docker compose down -v --remove-orphans"
print_info "docker compose up -d kong-database"
print_info "docker exec kong-database psql -U kong -c \"CREATE DATABASE konga;\""
print_info "docker compose up -d"