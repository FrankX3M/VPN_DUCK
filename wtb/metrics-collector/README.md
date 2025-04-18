# Metrics Collector для VPN Duck

Сервис для сбора и анализа метрик производительности серверов VPN Duck в мульти-геолокационной архитектуре.

## Функциональность

Сервис выполняет следующие задачи:

1. **Сбор метрик производительности:**
   - Измерение задержки (latency)
   - Измерение джиттера (jitter)
   - Измерение процента потери пакетов (packet loss)
   - Симуляция измерения пропускной способности (bandwidth)

2. **Обслуживание инфраструктуры:**
   - Анализ собранных метрик и обновление рейтингов серверов
   - Проверка доступности геолокаций
   - Миграция пользователей с неактивных серверов на активные
   - Балансировка нагрузки между серверами
   - Очистка истекших конфигураций

3. **Автоматическая регистрация сервера:**
   - Определение собственного IP-адреса и геолокации
   - Регистрация сервера в базе данных, если он еще не зарегистрирован

## Настройка

Сервис поддерживает следующие переменные окружения:

- `DATABASE_SERVICE_URL` - URL сервиса базы данных (по умолчанию: `http://database-service:5002`)
- `WIREGUARD_SERVICE_URL` - URL сервиса WireGuard (по умолчанию: `http://wireguard-service:5001`)
- `COLLECTION_INTERVAL` - Интервал сбора метрик в секундах (по умолчанию: `900` - 15 минут)
- `MAINTENANCE_INTERVAL` - Интервал обслуживания в секундах (по умолчанию: `3600` - 1 час)
- `PING_COUNT` - Количество пингов для измерения задержки (по умолчанию: `10`)
- `GEO_SERVICE_URL` - URL сервиса геолокации (по умолчанию: `https://ipapi.co`)

## Интеграция с VPN Duck

Сервис интегрируется с существующей инфраструктурой VPN Duck через API:

- Использует `/servers/metrics/add` для отправки собранных метрик
- Использует `/servers/metrics/analyze` для анализа метрик и обновления рейтингов
- Использует `/configs/migrate_users` для миграции пользователей с неактивных серверов
- Использует `/geolocations/check` для проверки доступности геолокаций
- Использует `/cleanup_expired` для очистки истекших конфигураций

## Развертывание

Сервис настроен для автоматического запуска в составе Docker Compose. Он будет автоматически собираться и запускаться вместе с остальными сервисами.

```bash
docker-compose up -d
```

## Мониторинг

Для мониторинга работы сервиса можно использовать журналы Docker:

```bash
docker-compose logs -f metrics-collector
```