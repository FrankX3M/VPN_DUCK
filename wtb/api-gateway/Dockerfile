# api-gateway/Dockerfile
FROM kong:3.9-ubuntu

USER root

# Установка необходимых пакетов
RUN apt-get update && \
    apt-get install -y curl postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Создание custom entrypoint скрипта
COPY <<EOF /docker-entrypoint.sh
#!/bin/bash
set -e

# Функция для проверки подключения к базе данных
wait_for_db() {
    echo "Ожидание подключения к базе данных..."
    until pg_isready -h \${KONG_PG_HOST} -p 5432 -U \${KONG_PG_USER}; do
        echo "База данных недоступна - ожидание..."
        sleep 2
    done
    echo "База данных доступна!"
}

# Функция для выполнения миграций
run_migrations() {
    echo "Проверка и выполнение миграций..."
    kong migrations bootstrap || echo "Bootstrap уже выполнен"
    kong migrations up || echo "Миграции уже актуальны"
    kong migrations finish || echo "Финализация миграций завершена"
}

# Если команда не указана, запускаем Kong
if [ "\$1" = "kong" ] && [ "\$2" = "docker-start" ]; then
    wait_for_db
    run_migrations
fi

# Выполняем оригинальную команду
exec "\$@"
EOF

# Делаем скрипт исполняемым
RUN chmod +x /docker-entrypoint.sh

# Копирование конфигурации Kong (опционально)
COPY kong.yml /etc/kong/kong.yml

# Установка правильных прав доступа
RUN chown -R kong:kong /etc/kong

USER kong

ENV KONG_DATABASE=postgres
ENV KONG_ADMIN_LISTEN=0.0.0.0:8001
ENV KONG_PROXY_LISTEN=0.0.0.0:8000

EXPOSE 8000 8001 8443 8444

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["kong", "docker-start"]