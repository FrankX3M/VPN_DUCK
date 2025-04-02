FROM python:3.9-slim

WORKDIR /app

# Установка библиотек клиента PostgreSQL
RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    apt-get clean

# Устанавливаем специфические версии Werkzeug и Flask
RUN pip install --no-cache-dir werkzeug==2.0.3
RUN pip install --no-cache-dir flask==2.0.1

# Установка psycopg2 напрямую
RUN pip install --no-cache-dir psycopg2-binary==2.9.3

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data

CMD ["python", "db_manager.py"]