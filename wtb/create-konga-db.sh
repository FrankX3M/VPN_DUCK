#!/bin/bash
set -e

echo "Создание базы данных konga вручную..."
docker exec kong-database psql -U kong -c "CREATE DATABASE konga;" || echo "База данных может уже существовать"
docker exec kong-database psql -U kong -c "GRANT ALL PRIVILEGES ON DATABASE konga TO kong;" || echo "Привилегии могут уже быть установлены"
echo "База данных konga создана или уже существует"
