FROM python:3.9-slim

WORKDIR /app

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

# Делаем скрипты исполняемыми
RUN chmod +x setup_database.sh wait-for-postgres.sh

# Создаем директорию для данных
RUN mkdir -p data

# Ждем запуска PostgreSQL и запускаем сервис
CMD ["./wait-for-postgres.sh", "db", "python", "db_manager.py"]