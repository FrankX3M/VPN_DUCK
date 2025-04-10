<html>
<body>
<!--StartFragment--><html><head></head><body><h1>Команды для управления сервером WireGuard в Docker</h1>

Команда | Описание
-- | --
docker compose up -d | Запускает все сервисы, определенные в docker-compose.yml, в фоновом режиме.
docker compose down | Останавливает и удаляет все контейнеры, созданные с помощью docker-compose.yml.
docker compose pull wireguard | Загружает последнюю версию образа WireGuard.
docker compose up -d wireguard | Обновляет и перезапускает только контейнер WireGuard.
docker stop wireguard | Останавливает работающий контейнер WireGuard.
docker start wireguard | Запускает ранее остановленный контейнер WireGuard.
docker restart wireguard | Перезапускает контейнер WireGuard.
docker logs wireguard | Отображает логи контейнера WireGuard.
docker exec -it wireguard /bin/bash | Открывает интерактивную оболочку внутри контейнера WireGuard.
docker image prune | Удаляет неиспользуемые образы Docker, включая старые версии образа WireGuard.
docker exec -it wireguard wg-quick down wg0 | Отключает интерфейс WireGuard внутри контейнера.
docker exec -it wireguard wg-quick up wg0 | Включает интерфейс WireGuard внутри контейнера.
docker exec -it wireguard wg show | Отображает текущие соединения и статистику WireGuard.
docker exec -it wireguard systemctl restart wg-quick@wg0 | Перезапускает службу WireGuard внутри контейнера.
docker cp wireguard:/config /backup/wireguard | Копирует конфигурационные файлы из контейнера на хост для резервного копирования.
docker exec -it wireguard cat /config/wg0.conf | Показывает конфигурацию WireGuard-сервера.
docker stats wireguard | Показывает использование ресурсов контейнером в реальном времени.
docker inspect wireguard | Отображает подробную информацию о контейнере, включая сетевые настройки.
docker exec -it wireguard iptables -L | Показывает правила брандмауэра внутри контейнера.
docker volume ls | Отображает список томов Docker, включая тома WireGuard.


<h2>Полезные советы</h2>
<h3>Мониторинг и управление</h3>
<ul>
<li>Чтобы проверить статус контейнера WireGuard: <code>docker ps -a | grep wireguard</code></li>
<li>Для просмотра логов в режиме реального времени: <code>docker logs -f wireguard</code></li>
<li>Для непрерывного мониторинга соединений: <code>watch -n 1 "docker exec wireguard wg show"</code></li>
<li>Для удобного управления можно создать алиасы в <code>.bashrc</code> или <code>.zshrc</code>:
<pre><code class="language-bash">alias wg-start='docker start wireguard'alias wg-stop='docker stop wireguard'alias wg-restart='docker restart wireguard'alias wg-logs='docker logs -f wireguard'alias wg-status='docker exec wireguard wg show'
</code></pre></li>
</ul>
<h3>Безопасность и бэкапы</h3>
<ul>
<li>Регулярно делайте резервные копии конфигурации: <code>docker cp wireguard:/config /path/to/backup/$(date +%Y%m%d)</code></li>
<li>Проверяйте журналы на подозрительную активность: <code>docker exec wireguard grep -i error /var/log/syslog</code></li>
<li>Ограничьте доступ к порту WireGuard только с доверенных IP-адресов, добавив правила в iptables хоста</li>
<li>Обновляйте контейнер регулярно, чтобы получать исправления безопасности: <code>docker compose pull wireguard &amp;&amp; docker compose up -d wireguard</code></li>
</ul>
<h3>Устранение неполадок</h3>
<ul>
<li>Если клиенты не могут подключиться, проверьте, открыт ли порт: <code>docker exec wireguard netstat -tulpn | grep 51820</code></li>
<li>Проверьте маршрутизацию внутри контейнера: <code>docker exec wireguard ip route</code></li>
<li>При проблемах с DNS для клиентов, проверьте настройки DNS в контейнере: <code>docker exec wireguard cat /etc/resolv.conf</code></li>
<li>Для более подробной отладки включите логирование: <code>docker exec wireguard wg set wg0 log-level verbose</code></li>
</ul></body></html><!--EndFragment-->
</body>
</html>