# Базовые утилиты и системные инструменты
apt install -y sudo                # Запуск команд с привилегиями
apt install -y curl wget           # Утилиты для загрузки файлов
apt install -y vim                 # Текстовый редактор
apt install -y htop                # Интерактивный просмотр процессов
apt install -y tmux                # Терминальный мультиплексор
apt install -y mc                  # Midnight Commander - файловый менеджер
apt install -y ncdu                # Анализатор использования диска
apt install -y net-tools           # Сетевые утилиты (ifconfig, netstat, и т.д.)
apt install -y dnsutils            # DNS-утилиты (dig, nslookup)
apt install -y apt-transport-https # Для работы с HTTPS-репозиториями

# Безопасность
apt install -y ufw                 # Упрощенный фаервол
apt install -y fail2ban            # Защита от брутфорс-атак
apt install -y unattended-upgrades # Автоматические обновления безопасности

# Мониторинг и диагностика
apt install -y iotop               # Мониторинг I/O-операций дисков
apt install -y sysstat             # Системная статистика (iostat, mpstat, sar)
apt install -y htop                # Усовершенствованный top
apt install -y atop                # Расширенный монитор системы
apt install -y nmon                # Монитор ресурсов
apt install -y lsof                # Список открытых файлов
apt install -y strace              # Трассировка системных вызовов
apt install -y tcpdump             # Анализатор сетевого трафика

# Архивация и сжатие
apt install -y zip unzip           # Работа с zip-архивами
apt install -y p7zip-full          # Поддержка 7z-архивов
apt install -y tar                 # Работа с tar-архивами
apt install -y bzip2               # Утилита сжатия bzip2

# Разработка (если требуется)
apt install -y git                 # Система контроля версий
apt install -y build-essential     # Компиляторы и базовые инструменты разработки
apt install -y python3-pip         # Менеджер пакетов Python

# Анализ логов
apt install -y goaccess            # Анализатор логов Apache/Nginx в реальном времени
apt install -y logwatch            # Анализатор системных логов

# Сетевые инструменты
apt install -y nmap                # Сканер портов
apt install -y traceroute          # Трассировка маршрута пакетов
apt install -y whois               # Информация о доменах
apt install -y iperf3              # Тестирование пропускной способности сети
apt install -y mtr                 # Комбинированный traceroute и ping
apt install -y iproute2            # Инструменты управления сетью (ip, ss)

# Утилиты для выполнения задач по расписанию
apt install -y cron                # Планировщик задач

# Инструменты для резервного копирования
apt install -y rsync               # Эффективное копирование файлов

# Производительность и оптимизация
apt install -y preload             # Адаптивное кэширование часто используемых программ
apt install -y tuned               # Система тонкой настройки

# Для серверов баз данных
apt install -y postgresql-client   # Клиент PostgreSQL
apt install -y mysql-client        # Клиент MySQL/MariaDB

# Установка всех пакетов одной командой
apt install -y sudo curl wget vim htop tmux mc ncdu net-tools dnsutils apt-transport-https ufw fail2ban unattended-upgrades iotop sysstat htop atop nmon lsof strace tcpdump zip unzip p7zip-full tar bzip2 git build-essential python3-pip goaccess logwatch nmap traceroute whois iperf3 mtr iproute2 cron rsync preload tuned postgresql-client mysql-client
