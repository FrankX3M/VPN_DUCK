#!/usr/bin/env python3
import os
import sys
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import threading
import time
import signal
import sys
# Добавляем текущую директорию в PYTHONPATH
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_manager import RouteManager
from server_manager import ServerManager
from cache_manager import CacheManager
from connection_manager import ConnectionManager
from utils.errors import RemoteServerError, NoAvailableServerError, DatabaseError
from app_config.settings import (
    SERVER_HOST, 
    SERVER_PORT, 
    DEBUG, 
    USE_MOCK_DATA, 
    FALLBACK_MODE_ENABLED,
    wait_for_services
)
# Импорт модуля инициализации ServerManager
from server_manager_init import initialize_server_manager
from auth.auth_handler import init_auth_handler

# Настройка логирования
logger = logging.getLogger('wireguard-proxy')

# Переменные для правильного завершения работы
shutdown_event = threading.Event()
background_threads = []

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)

# Инициализация менеджеров
cache_manager = CacheManager()
# server_manager = ServerManager(cache_manager)
# connection_manager = ConnectionManager(server_manager)
# route_manager = RouteManager(connection_manager, cache_manager)
from server_manager_init import initialize_server_manager
server_manager = initialize_server_manager(
    cache_manager=cache_manager,
    shutdown_event=shutdown_event,
    background_threads=background_threads
)
connection_manager = ConnectionManager(server_manager)
route_manager = RouteManager(connection_manager, cache_manager)

# Инициализация аутентификации
init_auth_handler()

# Обработка сигналов завершения
def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    shutdown_event.set()
    
    # Ожидание завершения фоновых потоков (не более 5 секунд)
    for thread in background_threads:
        if thread.is_alive():
            thread.join(timeout=5.0)
    
    logger.info("Exiting wireguard-proxy service")
    sys.exit(0)

# Регистрация обработчиков сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Запуск фоновых задач
# def background_server_updater():
#     """Фоновая задача для обновления информации о серверах"""
#     retry_count = 0
#     max_retry_count = 10
#     retry_delay = 5
#     
#     while not shutdown_event.is_set():
#         try:
#             # Обновление информации о серверах
#             server_manager.update_servers_info()
#             
#             # При успехе сбрасываем счетчик повторных попыток
#             retry_count = 0
#             retry_delay = 5
#             
#             # Ожидание следующего обновления (проверка на событие завершения)
#             shutdown_event.wait(60)  # 1 минута между обновлениями
#             
#         except Exception as e:
#             # Увеличиваем счетчик повторных попыток
#             retry_count += 1
#             logger.error(f"Error in server updater background task: {e}")
#             
#             if retry_count >= max_retry_count:
#                 logger.warning(f"Max retries ({max_retry_count}) exceeded in server updater, using longer interval")
#                 # Используем более длительный интервал при постоянных ошибках
#                 shutdown_event.wait(300)  # 5 минут после достижения лимита повторов
#                 retry_count = 0  # Сбрасываем счетчик
#             else:
#                 # Экспоненциальное увеличение задержки между попытками
#                 retry_delay = min(retry_delay * 2, 120)
#                 logger.info(f"Retrying in {retry_delay} seconds...")
#                 shutdown_event.wait(retry_delay)

# Запуск фоновых потоков
def start_background_threads():
    """Запуск всех фоновых потоков"""
    global background_threads
    
    # Поток обновления информации о серверах теперь запускается через initialize_server_manager
    
    logger.info("Background threads started")

# Endpoints API
@app.route('/health', methods=['GET'])
def health_check():
    """Эндпоинт для проверки работоспособности прокси-сервера"""
    # Проверка, работают ли фоновые потоки
    all_threads_alive = all(thread.is_alive() for thread in background_threads)
    
    if not all_threads_alive:
        logger.warning("Some background threads are not running")
        return jsonify({
            "status": "degraded",
            "service": "wireguard-proxy",
            "details": "Some background processes are not running"
        }), 200
    
    return jsonify({
        "status": "ok", 
        "service": "wireguard-proxy",
        "version": "1.1.0",
        "mode": "mock" if USE_MOCK_DATA else "production"
    })

@app.route('/create', methods=['POST'])
def create_configuration():
    """Создание новой конфигурации WireGuard на удаленном сервере"""
    try:
        data = request.json
        logger.info(f"Received create request with data: {data}")
        
        # Получение параметров
        user_id = data.get('user_id')
        geolocation_id = data.get('geolocation_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
            
        # Получение подходящего сервера через менеджер маршрутизации
        result = route_manager.handle_create_request(data)
        return jsonify(result)
        
    except NoAvailableServerError as e:
        logger.error(f"No available server: {e}")
        return jsonify({"error": "No available server found", "details": str(e)}), 503
    except RemoteServerError as e:
        logger.error(f"Remote server error: {e}")
        return jsonify({"error": "Error communicating with remote server", "details": str(e)}), 502
    except Exception as e:
        logger.exception(f"Unexpected error in create_configuration: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/remove/<public_key>', methods=['DELETE'])
def remove_peer(public_key):
    """Удаление пира с удаленного сервера по публичному ключу"""
    try:
        logger.info(f"Received remove request for public key: {public_key}")
        
        # Маршрутизация запроса на удаление через менеджер
        result = route_manager.handle_remove_request(public_key)
        return jsonify(result)
        
    except RemoteServerError as e:
        logger.error(f"Remote server error: {e}")
        return jsonify({"error": "Error communicating with remote server", "details": str(e)}), 502
    except Exception as e:
        logger.exception(f"Unexpected error in remove_peer: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/servers', methods=['GET'])
def get_servers():
    """Получение списка доступных серверов"""
    try:
        servers = server_manager.get_available_servers()
        
        # Удаляем конфиденциальную информацию из ответа
        sanitized_servers = []
        for server in servers:
            server_copy = server.copy()
            # Удаляем API ключи и другие секретные данные
            server_copy.pop('api_key', None)
            server_copy.pop('oauth_client_secret', None)
            server_copy.pop('hmac_secret', None)
            sanitized_servers.append(server_copy)
            
        return jsonify({"servers": sanitized_servers})
    except Exception as e:
        logger.exception(f"Error getting servers: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Получение статуса работы прокси-сервера и удаленных серверов"""
    try:
        status = server_manager.get_servers_status()
        
        # Информация о фоновых процессах
        threads_status = {
            thread.name: "running" if thread.is_alive() else "stopped"
            for thread in background_threads
        }
        
        # Информация о времени последнего обновления
        last_update = None
        if server_manager.last_update:
            last_update = server_manager.last_update.strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            "proxy_status": "active",
            "servers_status": status,
            "connected_servers": len([s for s in status if s["status"] == "online"]),
            "total_servers": len(status),
            "background_processes": threads_status,
            "last_update": last_update,
            "mode": "mock" if USE_MOCK_DATA else "production",
            "fallback_mode": server_manager.fallback_mode
        })
    except Exception as e:
        logger.exception(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Получение метрик работы прокси-сервера"""
    try:
        metrics = {
            "cache": cache_manager.get_stats(),
            "request_count": route_manager.get_request_count(),
            "error_count": route_manager.get_error_count(),
            "server_stats": server_manager.get_server_metrics(),
            "uptime": {
                "proxy_service": "unknown",  # Здесь можно добавить время работы сервиса
                "background_processes": {
                    thread.name: "running" if thread.is_alive() else "stopped"
                    for thread in background_threads
                }
            }
        }
        return jsonify(metrics)
    except Exception as e:
        logger.exception(f"Error getting metrics: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/admin/servers', methods=['POST'])
def add_server():
    """Добавление нового удаленного сервера (только для админов)"""
    try:
        data = request.json
        # Здесь должна быть проверка аутентификации админа
        
        result = server_manager.add_server(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error adding server: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/admin/servers/<server_id>', methods=['DELETE'])
def remove_server(server_id):
    """Удаление удаленного сервера (только для админов)"""
    try:
        # Здесь должна быть проверка аутентификации админа
        
        result = server_manager.remove_server(server_id)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error removing server: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/admin/reset-cache', methods=['POST'])
def reset_cache():
    """Сброс кэша (только для админов)"""
    try:
        cache_manager.clear()
        return jsonify({"status": "success", "message": "Cache cleared successfully"})
    except Exception as e:
        logger.exception(f"Error clearing cache: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/debug/config', methods=['GET'])
def get_debug_config():
    """Возвращает текущую конфигурацию (только для отладки)"""
    if not DEBUG:
        return jsonify({"error": "Debug endpoints are disabled in production mode"}), 403
        
    config = {
        "server": {
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "debug": DEBUG
        },
        "mock_mode": USE_MOCK_DATA,
        "fallback_mode": {
            "enabled": FALLBACK_MODE_ENABLED,
            "active": server_manager.fallback_mode
        },
        "services": {
            "database_url": DATABASE_SERVICE_URL
        },
        "background_processes": {
            thread.name: "running" if thread.is_alive() else "stopped"
            for thread in background_threads
        }
    }
    
    return jsonify(config)

# Ожидание запуска зависимых сервисов перед запуском приложения
def initialize_services():
    """Инициализация всех необходимых сервисов и зависимостей"""
    logger.info("Initializing wireguard-proxy service...")
    
    # Проверка доступности зависимых сервисов
    if not USE_MOCK_DATA:
        services_available = wait_for_services()
        
        if not services_available and FALLBACK_MODE_ENABLED:
            logger.warning("Services not available, starting in fallback mode")
            server_manager.fallback_mode = True
    
    # Начальное обновление происходит автоматически в фоновом потоке
    # Не нужно вызывать server_manager.update_servers_info() здесь
    
    # Запуск фоновых потоков (если есть другие потоки, кроме серверного)
    # start_background_threads()
    
    logger.info("Service initialization complete")

if __name__ == '__main__':
    # Инициализация при запуске
    initialize_services()
    
    # Запуск сервера
    port = int(os.environ.get('PORT', SERVER_PORT))
    logger.info(f"Starting wireguard-proxy server on {SERVER_HOST}:{port}")
    app.run(host=SERVER_HOST, port=port, debug=DEBUG)