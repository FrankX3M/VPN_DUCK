# Руководство по завершению миграции VPN Duck на мульти-геолокационную архитектуру

Данное руководство предназначено для завершения процесса миграции VPN Duck на новую мульти-геолокационную архитектуру после обновления `db_manager.py`. Все необходимые таблицы уже созданы, но требуется заполнить их начальными данными и связать существующие конфигурации с серверами.

## Подключение к базе данных PostgreSQL

Для выполнения SQL-команд необходимо подключиться к контейнеру PostgreSQL:

```bash
# Подключение к контейнеру PostgreSQL
docker exec -it wtb-postgres-1 psql -U postgres -d wireguard
```

Если у вас изменилось имя контейнера, вы можете найти его с помощью команды:

```bash
docker compose ps
```

## Шаг 1: Заполнение таблицы геолокаций

Добавьте основные геолокации в таблицу:

```sql
-- Добавление базовых геолокаций
INSERT INTO geolocations (code, name, description, available, created_at)
VALUES 
    ('ru', 'Россия', 'Серверы в России', TRUE, NOW()),
    ('us', 'США', 'Серверы в США', TRUE, NOW()),
    ('eu', 'Европа', 'Серверы в странах Европы', TRUE, NOW()),
    ('asia', 'Азия', 'Серверы в странах Азии', TRUE, NOW())
ON CONFLICT (code) DO NOTHING;

-- Проверка результата
SELECT * FROM geolocations;
```

## Шаг 2: Добавление существующего сервера

Для добавления существующего WireGuard-сервера в таблицу `servers`, вам нужно получить его текущие настройки из переменных окружения или конфигурационных файлов:

```sql
-- Получение ID геолокации России
DO $$
DECLARE
    geo_id INTEGER;
    server_endpoint TEXT := 'your-server-endpoint.com';  -- Замените на реальный эндпоинт
    server_port INTEGER := 51820;  -- Замените на реальный порт
    -- Получите публичный ключ из конфигурации или WireGuard
    server_public_key TEXT := 'your-public-key';  -- Замените на реальный ключ
    server_private_key TEXT := 'your-private-key';  -- Замените на реальный ключ
    server_address TEXT := '10.0.0.1/24';  -- Замените на реальный адрес
BEGIN
    -- Получаем ID геолокации для России
    SELECT id INTO geo_id FROM geolocations WHERE code = 'ru' LIMIT 1;
    
    -- Добавляем сервер, если он еще не существует
    IF NOT EXISTS (SELECT 1 FROM servers) THEN
        INSERT INTO servers 
            (geolocation_id, endpoint, port, public_key, private_key, address, status, last_check, created_at)
        VALUES
            (geo_id, server_endpoint, server_port, server_public_key, server_private_key, server_address, 'active', NOW(), NOW());
    END IF;
END $$;

-- Проверка результата
SELECT * FROM servers;
```

## Шаг 3: Получение реальных параметров сервера

Для получения реальных параметров вашего WireGuard-сервера выполните следующие команды в терминале:

```bash
# Подключение к контейнеру wireguard-service
docker exec -it wtb-wireguard-service-1 /bin/bash

# Посмотреть содержимое конфигурационного файла
cat /etc/wireguard/wg0.conf

# Получить публичный ключ
cat /etc/wireguard/public.key

# Получить приватный ключ
cat /etc/wireguard/private.key
```

Также можно проверить переменные окружения:

```bash
# Проверка переменных окружения контейнера
docker exec wtb-wireguard-service-1 env | grep -E 'ENDPOINT|PORT|ADDRESS'
```

После получения этих данных замените заполнители в SQL-запросе шага 2 реальными значениями.

## Шаг 4: Обновление существующих конфигураций

Свяжите существующие конфигурации с сервером и геолокацией:

```sql
-- Обновление существующих конфигураций
UPDATE configurations c
SET server_id = s.id, geolocation_id = s.geolocation_id
FROM servers s
WHERE c.server_id IS NULL AND s.id = (SELECT MIN(id) FROM servers);

-- Проверка результата
SELECT 
    c.id, 
    c.user_id, 
    c.active, 
    g.code AS geolocation_code, 
    g.name AS geolocation_name,
    s.endpoint AS server_endpoint
FROM configurations c
JOIN servers s ON c.server_id = s.id
JOIN geolocations g ON c.geolocation_id = g.id;
```

## Шаг 5: Создание записей в user_configurations

Создайте записи в таблице user_configurations для существующих пользователей:

```sql
-- Создание записей в user_configurations
INSERT INTO user_configurations (
    user_id, config_id, server_id, config_text, created_at
)
SELECT 
    c.user_id,
    c.id,
    c.server_id,
    c.config,
    c.created_at
FROM configurations c
WHERE c.active = TRUE 
AND NOT EXISTS (
    SELECT 1 FROM user_configurations uc 
    WHERE uc.user_id = c.user_id AND uc.config_id = c.id
);

-- Проверка результата
SELECT * FROM user_configurations;
```

## Шаг 6: Добавление местоположения сервера

Добавьте географические координаты вашего сервера для улучшения алгоритма выбора:

```sql
-- Добавление географических координат сервера
INSERT INTO server_locations (
    server_id,
    latitude,
    longitude,
    city,
    country,
    updated_at
)
SELECT 
    s.id,
    55.755826,  -- Широта (пример - Москва)
    37.617300,  -- Долгота (пример - Москва)
    'Москва',   -- Город
    'Россия',   -- Страна
    NOW()
FROM servers s
WHERE NOT EXISTS (
    SELECT 1 FROM server_locations sl WHERE sl.server_id = s.id
);

-- Проверка результата
SELECT * FROM server_locations;
```

## Шаг 7: Добавление начальных метрик сервера

Добавьте начальные метрики для сервера:

```sql
-- Добавление начальных метрик
INSERT INTO server_metrics (
    server_id,
    latency,
    bandwidth,
    jitter,
    packet_loss,
    measured_at
)
SELECT 
    s.id,
    30.0,    -- Задержка в мс
    100.0,   -- Пропускная способность в Мбит/с
    5.0,     -- Джиттер в мс
    0.5,     -- Потеря пакетов в %
    NOW()
FROM servers s
WHERE NOT EXISTS (
    SELECT 1 FROM server_metrics sm WHERE sm.server_id = s.id
);

-- Проверка результата
SELECT * FROM server_metrics;
```

## Шаг 8: Обновление метрик сервера и рейтинга

Обновите рейтинг сервера на основе метрик:

```sql
-- Обновление метрик и рейтинга сервера
WITH server_avg_metrics AS (
    SELECT 
        server_id,
        AVG(latency) as avg_latency,
        AVG(jitter) as avg_jitter,
        AVG(packet_loss) as avg_packet_loss,
        AVG(bandwidth) as avg_bandwidth,
        COUNT(*) as measurement_count
    FROM server_metrics
    GROUP BY server_id
)
UPDATE servers s
SET 
    metrics_rating = (
        (1 - LEAST(sam.avg_latency / 500, 1)) * 0.4 +
        (1 - LEAST(COALESCE(sam.avg_jitter, 50) / 100, 1)) * 0.2 +
        (1 - LEAST(COALESCE(sam.avg_packet_loss, 5) / 20, 1)) * 0.2 +
        LEAST(COALESCE(sam.avg_bandwidth, 10) / 100, 1) * 0.2
    ) * 100
FROM server_avg_metrics sam
WHERE s.id = sam.server_id;

-- Проверка результата
SELECT id, endpoint, metrics_rating FROM servers;
```

## Шаг 9: Проверка итоговой конфигурации

Проверьте общее состояние базы данных:

```sql
-- Проверка количества записей в таблицах
SELECT 'geolocations' as table_name, COUNT(*) as count FROM geolocations
UNION ALL
SELECT 'servers', COUNT(*) FROM servers
UNION ALL
SELECT 'server_locations', COUNT(*) FROM server_locations
UNION ALL
SELECT 'server_metrics', COUNT(*) FROM server_metrics
UNION ALL
SELECT 'configs без сервера', COUNT(*) FROM configurations WHERE server_id IS NULL
UNION ALL
SELECT 'user_configurations', COUNT(*) FROM user_configurations;
```

## Шаг 10: Настройка периодического обслуживания (опционально)

Создайте хранимую процедуру для периодического обслуживания базы данных:

```sql
-- Создание хранимой процедуры для обслуживания
CREATE OR REPLACE PROCEDURE maintenance_procedure()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Обновление метрик серверов
    WITH server_avg_metrics AS (
        SELECT 
            server_id,
            AVG(latency) as avg_latency,
            AVG(jitter) as avg_jitter,
            AVG(packet_loss) as avg_packet_loss,
            AVG(bandwidth) as avg_bandwidth
        FROM server_metrics
        WHERE measured_at > NOW() - INTERVAL '24 hours'
        GROUP BY server_id
    )
    UPDATE servers s
    SET 
        metrics_rating = CASE
            WHEN sam.avg_latency IS NULL THEN 0
            ELSE (
                (1 - LEAST(sam.avg_latency / 500, 1)) * 0.4 +
                (1 - LEAST(COALESCE(sam.avg_jitter, 50) / 100, 1)) * 0.2 +
                (1 - LEAST(COALESCE(sam.avg_packet_loss, 5) / 20, 1)) * 0.2 +
                LEAST(COALESCE(sam.avg_bandwidth, 10) / 100, 1) * 0.2
            ) * 100
        END
    FROM server_avg_metrics sam
    WHERE s.id = sam.server_id;
    
    -- Обновление доступности геолокаций
    WITH geo_servers AS (
        SELECT 
            g.id,
            COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_servers_count,
            AVG(s.metrics_rating) FILTER (WHERE s.status = 'active') AS avg_metrics_rating
        FROM geolocations g
        LEFT JOIN servers s ON g.id = s.geolocation_id
        GROUP BY g.id
    )
    UPDATE geolocations g
    SET 
        available = (gs.active_servers_count > 0),
        avg_rating = COALESCE(gs.avg_metrics_rating, 0)
    FROM geo_servers gs
    WHERE g.id = gs.id;
    
    -- Очистка старых метрик (старше 30 дней)
    DELETE FROM server_metrics WHERE measured_at < NOW() - INTERVAL '30 days';
END;
$$;

-- Запуск процедуры обслуживания (при необходимости)
-- CALL maintenance_procedure();
```

## Заключение

После выполнения всех шагов ваша база данных будет полностью настроена для работы с мульти-геолокационной архитектурой VPN Duck. Теперь приложение сможет использовать расширенные функции:

- Выбор оптимального сервера для пользователя
- Переключение между серверами при недоступности
- Мониторинг производительности серверов
- Управление геолокациями

Для проверки работоспособности новых функций можно протестировать API-эндпоинты, настроенные в обновленном `db_manager.py`, например:

- `/geolocations/available` - получение списка доступных геолокаций
- `/servers/geolocation/{geolocation_id}` - получение серверов для конкретной геолокации
- `/servers/select_optimal` - выбор оптимального сервера для пользователя
