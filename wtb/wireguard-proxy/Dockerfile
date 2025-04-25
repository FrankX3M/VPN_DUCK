FROM python:3.9-slim

# Установка зависимостей
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt в контейнер
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p data config

# Установка прав на исполнение
RUN chmod +x setup.sh proxy_server.py

# Открытие порта для API
EXPOSE 5001

# Запуск сервера при старте контейнера
CMD ["python", "proxy_server.py"]