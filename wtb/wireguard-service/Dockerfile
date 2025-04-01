FROM ubuntu:20.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    wireguard \
    iproute2 \
    python3 \
    python3-pip \
    iptables \
    && apt-get clean

WORKDIR /app

# First install specific versions of Werkzeug and Flask
RUN pip3 install --no-cache-dir werkzeug==2.0.3
RUN pip3 install --no-cache-dir flask==2.0.1

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /etc/wireguard
COPY ./wgup/wg0.conf /etc/wireguard/wg0.conf.backup

# Сделайте скрипт исполняемым
COPY init-iptables.sh /app/
RUN chmod +x /app/init-iptables.sh

# Запустите iptables и затем wireguard_manager.py
CMD ["/bin/bash", "-c", "/app/init-iptables.sh && python3 wireguard_manager.py"]