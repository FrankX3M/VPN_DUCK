#!/bin/bash
set -e

echo "Запуск миграций Kong..."
docker exec kong-gateway kong migrations bootstrap || echo "Миграции могут уже быть выполнены"
echo "Миграции Kong завершены"
