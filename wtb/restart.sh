docker system prune -a
docker system prune -a --volumes
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose logs