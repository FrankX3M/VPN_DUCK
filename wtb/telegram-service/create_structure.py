#!/usr/bin/env python3
import os
import sys

def create_file(path, content=""):
    """Создает файл с заданным содержимым."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Создан файл: {path}")

def create_directory(path):
    """Создает директорию, если она не существует."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Создана директория: {path}")
    else:
        print(f"Директория уже существует: {path}")

def create_bot_structure(base_path="."):
    """Создает структуру директорий и файлов для Telegram бота."""
    # Создаем основные директории
    directories = [
        "core",
        "data",
        "handlers",
        "keyboards",
        "states",
        "utils"
    ]
    
    for directory in directories:
        create_directory(os.path.join(base_path, directory))
    
    # Создаем __init__.py файлы в каждой директории
    for directory in directories:
        create_file(os.path.join(base_path, directory, "__init__.py"), "# Пустой __init__.py файл для превращения директории в пакет")
    
    # Создаем основные файлы
    files = {
        "bot.py": "# Точка входа в приложение",
        "core/settings.py": "# Настройки приложения",
        "handlers/cancel.py": "# Обработчик команды /cancel",
        "handlers/callback_handlers.py": "# Обработчики callback-запросов",
        "handlers/config.py": "# Обработчики файлов конфигураций",
        "handlers/create.py": "# Создание новой конфигурации",
        "handlers/extend.py": "# Продление конфигурации",
        "handlers/help.py": "# Обработчик команды /help",
        "handlers/init.py": "# Инициализация обработчиков",
        "handlers/payments.py": "# Обработчики для платежей",
        "handlers/recreate.py": "# Пересоздание конфигурации",
        "handlers/stars_info.py": "# Информация о Telegram Stars",
        "handlers/start.py": "# Обработчик команды /start",
        "handlers/status.py": "# Проверка статуса",
        "handlers/unknown.py": "# Обработчик неизвестных сообщений",
        "keyboards/keyboards.py": "# Определение клавиатур",
        "states/states.py": "# Определение состояний",
        "utils/bd.py": "# Работа с базой данных/API",
        "utils/payment.py": "# Работа с платежами",
        "utils/qr.py": "# Генерация QR-кодов",
        "README.md": "# VPN Duck - Telegram Bot\n\nVPN Duck - это Telegram бот для создания и управления личными VPN-конфигурациями на базе WireGuard.",
        "requirements.txt": "aiogram==2.25.1\nqrcode==7.4.2\nrequests==2.31.0\npython-dotenv==1.0.0\nPillow==10.0.0"
    }
    
    for file_path, content in files.items():
        create_file(os.path.join(base_path, file_path), content)

if __name__ == "__main__":
    # Если указан аргумент командной строки, используем его как базовый путь
    base_path = sys.argv[1] if len(sys.argv) > 1 else "."
    create_bot_structure(base_path)
    print(f"Структура бота успешно создана в директории: {os.path.abspath(base_path)}")