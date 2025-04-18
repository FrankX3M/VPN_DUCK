# Структура проекта WireGuard Telegram Bot (WTB)

```
wtb/
├── .env.example                          # Пример конфигурационного файла с переменными окружения
├── restart.sh                           # Скрипт для перезапуска Docker-контейнеров
├── docker-compose.yml                   # Файл конфигурации Docker Compose
│
├── admin-panel/                         # Административная панель
│   ├── Dockerfile                       # Dockerfile для сборки админ-панели
│   ├── app.py                           # Основное Flask-приложение админ-панели
│   ├── requirements.txt                 # Зависимости Python для админ-панели
│   └── templates/                       # Шаблоны HTML для admin-panel
│       ├── base.html                    # Базовый шаблон
│       ├── dashboard.html               # Шаблон для страницы мониторинга
│       ├── geolocations.html            # Шаблон для управления геолокациями
│       ├── index.html                   # Шаблон главной страницы
│       ├── login.html                   # Шаблон страницы входа
│       └── servers.html                 # Шаблон для управления серверами
│
├── config/                              # Директория конфигурации
│   └── config.yml                       # Конфигурационный файл
│
├── database-service/                    # Сервис базы данных
│   ├── Dockerfile                       # Dockerfile для сборки сервиса БД
│   ├── db_manager.py                    # Менеджер БД и API для работы с базой данных
│   ├── requirements.txt                 # Зависимости Python для сервиса БД
│   └── wait-for-postgres.sh             # Скрипт ожидания доступности PostgreSQL
│
├── metrics-collector/                   # Сервис сбора метрик серверов
│   ├── Dockerfile                       # Dockerfile для сборки сервиса метрик
│   ├── README.md                        # Описание сервиса сбора метрик
│   ├── requirements.txt                 # Зависимости Python для сервиса метрик
│   └── server_metrics_collector.py      # Скрипт сбора метрик серверов
│
├── migration-service/                   # Сервис миграции пользователей
│   ├── Dockerfile                       # Dockerfile для сборки сервиса миграции
│   ├── README.md                        # Описание сервиса миграции
│   ├── automatic_migration.py           # Скрипт автоматической миграции
│   └── requirements.txt                 # Зависимости Python для сервиса миграции
│
├── telegram-service/                    # Telegram-бот сервис
│   ├── Dockerfile                       # Dockerfile для сборки сервиса Telegram-бота
│   ├── README.md                        # Описание Telegram-бота
│   ├── bot.py                           # Точка входа в бота
│   ├── create_structure.py              # Скрипт создания структуры бота
│   ├── requirements.txt                 # Зависимости Python для Telegram-бота
│   ├── core/                            # Ядро бота
│   │   ├── __init__.py
│   │   ├── callback_middleware.py       # Middleware для обработки колбэков
│   │   └── settings.py                  # Настройки бота
│   ├── handlers/                        # Обработчики команд и сообщений
│   │   ├── __init__.py
│   │   ├── callback_handlers.py         # Обработчики callback-запросов
│   │   ├── cancel.py                    # Обработчик отмены
│   │   ├── config.py                    # Обработчики файлов конфигураций
│   │   ├── create.py                    # Создание новой конфигурации
│   │   ├── create_all.py                # Расширенное создание конфигураций
│   │   ├── direct_callbacks.py          # Прямые обработчики колбэков
│   │   ├── extend.py                    # Обработчики продления
│   │   ├── geolocation.py               # Обработчики геолокаций
│   │   ├── help.py                      # Обработчик команды /help
│   │   ├── init.py                      # Инициализация обработчиков
│   │   ├── payments.py                  # Обработчики платежей
│   │   ├── recreate.py                  # Пересоздание конфигурации
│   │   ├── stars_info.py                # Информация о Telegram Stars
│   │   ├── start.py                     # Обработчик команды /start
│   │   ├── status.py                    # Проверка статуса
│   │   └── unknown.py                   # Обработчик неизвестных сообщений
│   ├── keyboards/                       # Клавиатуры
│   │   ├── __init__.py
│   │   └── keyboards.py                 # Определение клавиатур
│   ├── states/                          # Состояния
│   │   ├── __init__.py
│   │   └── states.py                    # Определение состояний
│   └── utils/                           # Утилиты
│       ├── __init__.py
│       ├── bd.py                        # Работа с базой данных/API
│       ├── payment.py                   # Работа с платежами
│       └── qr.py                        # Генерация QR-кодов
│
└── wireguard-service/                   # Сервис WireGuard
    ├── Dockerfile                       # Dockerfile для сборки сервиса WireGuard
    ├── init-iptables.sh                 # Скрипт инициализации iptables
    ├── requirements.txt                 # Зависимости Python для сервиса WireGuard
    ├── wireguard_manager.py             # Менеджер WireGuard и API
    └── wgup/                            # Директория для конфигурации WireGuard
        └── start.py                     # Скрипт запуска
```

## Основные компоненты системы:

1. **Admin Panel** - Административная панель для управления серверами и геолокациями.
2. **Database Service** - API для работы с базой данных PostgreSQL.
3. **Metrics Collector** - Сервис для сбора метрик производительности серверов.
4. **Migration Service** - Сервис для автоматической миграции пользователей между серверами.
5. **Telegram Bot Service** - Интерфейс для пользователей через Telegram.
6. **WireGuard Service** - API для управления конфигурациями WireGuard.

## Описание архитектуры

Архитектура представляет собой комплексную микросервисную систему для управления VPN-сервисом с использованием WireGuard. Основные особенности:

- **Мультигеолокационность**: поддержка нескольких геолокаций для оптимального подключения пользователей
- **Автоматическая миграция**: перемещение пользователей между серверами при проблемах с доступностью
- **Мониторинг серверов**: сбор и анализ метрик производительности для оптимизации работы
- **Telegram-интерфейс**: удобный способ создания и управления VPN-конфигурациями
- **Административная панель**: web-интерфейс для управления инфраструктурой

## Взаимодействие компонентов

- **Telegram Bot Service** → **Database Service**: запросы информации о пользователях и конфигурациях
- **Telegram Bot Service** → **WireGuard Service**: создание/удаление конфигураций
- **Metrics Collector** → **Database Service**: сохранение метрик
- **Migration Service** → **Database Service** + **WireGuard Service**: миграция пользователей
- **Admin Panel** → **Database Service**: управление геолокациями и серверами

Все компоненты системы работают в контейнерах Docker и управляются через Docker Compose, что обеспечивает простоту развертывания и масштабирования.
