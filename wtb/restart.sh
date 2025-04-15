docker system prune -a
docker system prune -a --volumes
docker compose down --remove-orphans
docker compose build --no-cache database-service
docker compose up -d
docker compose logs