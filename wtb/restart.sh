docker system prune -a
docker system prune -a --volumes
docker compose down
docker compose build --no-cache telegram-service
docker compose up -d
docker compose logs telegram-service