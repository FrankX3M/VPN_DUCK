FROM python:3.9-slim

WORKDIR /app

# Настраиваем apt для обхода проверки подписей
RUN echo 'Acquire::AllowInsecureRepositories "true";' > /etc/apt/apt.conf.d/90insecure && \
    echo 'Acquire::AllowDowngradeToInsecureRepositories "true";' >> /etc/apt/apt.conf.d/90insecure && \
    echo 'APT::Get::AllowUnauthenticated "true";' >> /etc/apt/apt.conf.d/90insecure && \
    echo 'Dir::Cache::Archives "/tmp/apt-cache";' > /etc/apt/apt.conf.d/80tempdir

# Устанавливаем необходимые пакеты с оптимизацией для экономии места
RUN mkdir -p /tmp/apt-cache && \
    apt-get update --allow-insecure-repositories && \
    apt-get install -y --allow-unauthenticated --no-install-recommends \
    libpq-dev \
    gcc \
    postgresql-client && \
    rm -rf /tmp/apt-cache && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем python-зависимости
RUN pip install --no-cache-dir werkzeug==2.0.3 flask==2.0.1 psycopg2-binary==2.9.3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data

# Делаем wait-for-postgres.sh исполняемым
RUN chmod +x wait-for-postgres.sh

CMD ["python", "db_manager.py"]