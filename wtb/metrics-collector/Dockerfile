FROM python:3.9-slim

WORKDIR /app

# Устанавливаем необходимые пакеты для мониторинга сети
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    net-tools \
    iproute2 \
    dnsutils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Установка требуемых Python-пакетов
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт в контейнер
COPY server_metrics_collector.py .
RUN chmod +x server_metrics_collector.py

CMD ["python", "server_metrics_collector.py"]