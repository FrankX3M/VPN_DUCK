FROM python:3.9-slim

WORKDIR /app

# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы приложения
COPY . .

# Создаем директории для шаблонов и статических файлов
RUN mkdir -p templates static

# Переменные окружения (могут быть переопределены в docker-compose)
ENV ADMIN_USERNAME=admin
ENV ADMIN_PASSWORD=admin
ENV ADMIN_SECRET_KEY=development_secret_key
ENV DATABASE_SERVICE_URL=http://database-service:5002
ENV WIREGUARD_SERVICE_URL=http://wireguard-service:5001

# Открываем порт
EXPOSE 5003

# Запускаем приложение
CMD ["python", "app.py"]