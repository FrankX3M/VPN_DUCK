#!/bin/bash
set -e

# Создаем VIEW для эмуляции колонки consrc
echo "Создание представления для эмуляции колонки consrc..."

# Подключаемся к контейнеру базы данных и создаем функцию и представление
docker exec kong-database psql -U kong -d konga << 'EOSQL'
-- Создаем функцию, которая эмулирует старое поведение pg_get_constraintdef
CREATE OR REPLACE FUNCTION pg_get_constraintdef_backwards_compat(oid) RETURNS text AS $$
SELECT pg_get_constraintdef($1);
$$ LANGUAGE SQL;

-- Создаем представление, которое добавляет колонку consrc
CREATE OR REPLACE VIEW pg_constraint_with_consrc AS
SELECT 
    r.oid,
    r.conrelid,
    r.confrelid,
    r.conname,
    r.contype,
    r.conkey,
    r.confkey,
    r.convalidated,
    r.conindid,
    r.conexclop,
    r.conbin,
    pg_get_constraintdef_backwards_compat(r.oid) AS consrc
FROM 
    pg_constraint r;

-- Предоставляем права на представление
GRANT SELECT ON pg_constraint_with_consrc TO PUBLIC;
EOSQL

echo "Создание представления и функции для совместимости завершено"
