#!/bin/bash

# Добавьте правила FORWARD для wg0
iptables -A FORWARD -i wg0 -j ACCEPT
iptables -A FORWARD -o wg0 -j ACCEPT

# Добавьте правило MASQUERADE для сети WireGuard
# Получите имя внешнего интерфейса автоматически
MAIN_INTERFACE=$(ip route | grep default | awk '{print $5}')
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o $MAIN_INTERFACE -j MASQUERADE

# Сохраните правила
echo "Правила iptables настроены:"
iptables -L -v
iptables -t nat -L -v