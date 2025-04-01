#!/bin/bash

# Обновление системы
apt update && apt upgrade -y

# Установка необходимых пакетов
apt install -y sudo curl wget gnupg2 ca-certificates lsb-release ufw git

# Настройка файрвола
ufw allow 22/tcp      # или ваш custom порт SSH
ufw allow 443/tcp     # HTTPS для API Gateway
ufw allow 51820/udp   # WireGuard
ufw enable

# Подготовка к установке Docker
apt install -y apt-transport-https software-properties-common
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновление и установка Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Включение автозапуска Docker
systemctl enable docker
systemctl start docker

# Установка Docker Compose
apt install -y docker-compose-plugin

# Проверка установки
docker --version
docker compose version

# Создание сети Docker
docker network create vpn-network



# Настройка SWAP
echo "Настройка SWAP-файла..."
# Проверка текущего состояния swap
free -h

# Создание swap-файла размером 2GB
fallocate -l 2G /swapfile
# Если fallocate не работает, раскомментировать следующую строку:
# dd if=/dev/zero of=/swapfile bs=1024 count=2097152

# Установка правильных разрешений
chmod 600 /swapfile

# Настройка файла как swap-пространства
mkswap /swapfile

# Активация swap
swapon /swapfile

# Настройка автоматической активации при загрузке
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab

# Настройка параметров использования swap
# Установка swappiness на 10 (лучше для серверов)
sysctl vm.swappiness=10
echo 'vm.swappiness=10' | tee -a /etc/sysctl.conf

# Настройка cache pressure
sysctl vm.vfs_cache_pressure=50
echo 'vm.vfs_cache_pressure=50' | tee -a /etc/sysctl.conf

# Проверка настройки swap
echo "Проверка настройки SWAP:"
free -h
swapon --show

echo "Настройка системы завершена!"

# # Создание docker-compose.yml
# cat > docker-compose.yml << 'EOL'
# services:
#   wireguard:
#     image: linuxserver/wireguard
#     container_name: wireguard
#     cap_add:
#       - NET_ADMIN
#       - SYS_MODULE
#     environment:
#       - PUID=1000
#       - PGID=1000
#       - TZ=Europe/Moscow
#       - SERVERURL=auto
#       - SERVERPORT=51820
#       - PEERS=1
#       - PEERDNS=auto
#       - INTERNAL_SUBNET=10.13.13.0
#     volumes:
#       - ./config:/config
#       - /lib/modules:/lib/modules
#     ports:
#       - 51820:51820/udp
#     sysctls:
#       - net.ipv4.conf.all.src_valid_mark=1
#     restart: unless-stopped
# EOL

# # Запуск контейнера
# docker compose up -d



# Генерация приватного ключа

# docker compose exec -it wireguard wg genkey