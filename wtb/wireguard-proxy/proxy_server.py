#!/usr/bin/env python3

import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import threading
import time

from route_manager import RouteManager
from server_manager import ServerManager
from cache_manager import CacheManager
from connection_manager import ConnectionManager
from utils.errors import RemoteServerError, NoAvailableServerError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('wireguard-proxy')

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)

# Инициализация менеджеров
cache_manager = CacheManager()
server_manager = ServerManager(cache_manager)
connection_manager = ConnectionManager(server_manager)
route_manager = RouteManager(connection_manager, cache_manager)

# Запуск фоновых задач
def background_tasks():
    while True:
        try:
            server_manager.update_servers_info()
            time.sleep(60)  # Обновляем информацию о серверах каждую минуту
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            time.sleep(10)  # При ошибке пробуем через 10 секунд

background_thread = threading.Thread(target=background_tasks, daemon=True)
background_thread.start()

@app.route('/health', methods=['GET'])
def health_check():
    """Эндпоинт для проверки работоспособности прокси-сервера"""
    return jsonify({"status": "ok", "service": "wireguard-proxy"})

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
        return jsonify({"servers": servers})
    except Exception as e:
        logger.exception(f"Error getting servers: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Получение статуса работы прокси-сервера и удаленных серверов"""
    try:
        status = server_manager.get_servers_status()
        return jsonify({
            "proxy_status": "active",
            "servers_status": status,
            "connected_servers": len([s for s in status if s["status"] == "online"]),
            "total_servers": len(status)
        })
    except Exception as e:
        logger.exception(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Получение метрик работы прокси-сервера"""
    try:
        metrics = {
            "cache_hits": cache_manager.get_stats()["hits"],
            "cache_misses": cache_manager.get_stats()["misses"],
            "request_count": route_manager.get_request_count(),
            "error_count": route_manager.get_error_count(),
            "server_stats": server_manager.get_server_metrics()
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

if __name__ == '__main__':
    # Инициализация при запуске
    try:
        server_manager.update_servers_info()
        logger.info("Initial server information updated successfully")
    except Exception as e:
        logger.error(f"Failed to update initial server information: {e}")
    
    # Запуск сервера
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)