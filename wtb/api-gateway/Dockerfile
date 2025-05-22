# Путь: wtb/api-gateway/Dockerfile
FROM kong:3.9-ubuntu

USER root

# Установка необходимых пакетов
RUN apt-get update && \
    apt-get install -y curl postgresql-client jq && \
    rm -rf /var/lib/apt/lists/*

# Создание custom entrypoint скрипта с исправленной логикой
COPY <<EOF /docker-entrypoint.sh
#!/bin/bash
set -e

# Функция для проверки подключения к базе данных
wait_for_db() {
    echo "Ожидание подключения к базе данных..."
    local max_attempts=30
    local attempt=1
    
    while [ \$attempt -le \$max_attempts ]; do
        if pg_isready -h \${KONG_PG_HOST} -p 5432 -U \${KONG_PG_USER} > /dev/null 2>&1; then
            echo "База данных доступна!"
            return 0
        fi
        echo "Попытка \$attempt/\$max_attempts: База данных недоступна - ожидание..."
        sleep 2
        attempt=\$((attempt + 1))
    done
    
    echo "Не удалось подключиться к базе данных после \$max_attempts попыток"
    return 1
}

# Функция для проверки статуса миграций
check_migrations_status() {
    echo "Проверка статуса миграций Kong..."
    if kong migrations list 2>/dev/null | grep -q "Database is up-to-date"; then
        echo "Миграции уже выполнены"
        return 0
    else
        echo "Миграции требуют выполнения"
        return 1
    fi
}

# Если команда не указана или это стандартный запуск Kong
if [ "\$1" = "kong" ] && [ "\$2" = "start" ]; then
    echo "Запуск Kong Gateway..."
    wait_for_db
    
    # Проверяем статус миграций, но не выполняем их
    # (миграции должны быть выполнены отдельным контейнером)
    if ! check_migrations_status; then
        echo "ВНИМАНИЕ: Миграции не выполнены. Kong может не запуститься корректно."
        echo "Убедитесь, что сервис kong-migration завершился успешно."
    fi
fi

# Выполняем оригинальную команду
exec "\$@"
EOF

# Делаем скрипт исполняемым
RUN chmod +x /docker-entrypoint.sh

# Копирование конфигурации Kong (опционально, закомментировано для отладки)
# COPY kong.yml /etc/kong/kong.yml

# Установка правильных прав доступа
RUN chown -R kong:kong /etc/kong

USER kong

# Переменные окружения Kong
ENV KONG_DATABASE=postgres
ENV KONG_ADMIN_LISTEN=0.0.0.0:8001
ENV KONG_PROXY_LISTEN=0.0.0.0:8000
ENV KONG_LOG_LEVEL=info

EXPOSE 8000 8001 8443 8444

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["kong", "start", "--vv"]