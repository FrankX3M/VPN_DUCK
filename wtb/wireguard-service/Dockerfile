FROM ubuntu:20.04

# Настраиваем apt для обхода проверки подписей и использования временного каталога для кэша
RUN echo 'Acquire::AllowInsecureRepositories "true";' > /etc/apt/apt.conf.d/90insecure && \
    echo 'Acquire::AllowDowngradeToInsecureRepositories "true";' >> /etc/apt/apt.conf.d/90insecure && \
    echo 'APT::Get::AllowUnauthenticated "true";' >> /etc/apt/apt.conf.d/90insecure && \
    echo 'Dir::Cache::Archives "/tmp/apt-cache";' > /etc/apt/apt.conf.d/80tempdir

# Устанавливаем минимально необходимые пакеты
RUN mkdir -p /tmp/apt-cache && \
    apt-get update --allow-insecure-repositories && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-unauthenticated --no-install-recommends \
    wireguard \
    iproute2 \
    python3 \
    python3-pip \
    iptables && \
    rm -rf /tmp/apt-cache && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем python-зависимости
RUN pip3 install --no-cache-dir werkzeug==2.0.3 flask==2.0.1

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /etc/wireguard
COPY ./wgup/wg0.conf /etc/wireguard/wg0.conf.backup

# Делаем скрипт исполняемым
COPY init-iptables.sh /app/
RUN chmod +x /app/init-iptables.sh

# Запускаем iptables и затем wireguard_manager.py
CMD ["/bin/bash", "-c", "/app/init-iptables.sh && python3 wireguard_manager.py"]