docker system prune -a
docker system prune -a --volumes
docker compose down --remove-orphans
docker compose build --no-cache admin-panel
docker compose up -d
docker compose logs