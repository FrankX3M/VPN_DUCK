#!/usr/bin/env python3
"""
Мок-сервер для тестирования WireGuard прокси-сервера
Запускается на порту 5002 и имитирует работу удаленного WireGuard сервера
"""

from flask import Flask, jsonify, request
import logging
import uuid
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mock-wireguard-server')

app = Flask(__name__)
PEERS = {}  # Для хранения созданных пиров

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": "mock-wireguard-server"})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online",
        "peers_count": len(PEERS),
        "load": 0.1,
        "version": "1.0.0-mock"
    })

@app.route('/create', methods=['POST'])
def create_peer():
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
            
        # Генерация ключей
        private_key = f"private_{str(uuid.uuid4()).replace('-', '')}"
        public_key = f"public_{str(uuid.uuid4()).replace('-', '')}"
        
        # Имитация задержки для более реалистичного поведения
        time.sleep(0.2)
        
        # Сохраняем пир в локальной "базе данных"
        PEERS[public_key] = {
            "user_id": user_id,
            "created_at": time.time()
        }
        
        return jsonify({
            "public_key": public_key,
            "private_key": private_key,
            "server_endpoint": "mock-server.example.com:51820",
            "allowed_ips": "0.0.0.0/0",
            "dns": "1.1.1.1",
            "config": f"# WireGuard configuration\n[Interface]\nPrivateKey = {private_key}\nAddress = 10.0.0.2/24\nDNS = 1.1.1.1\n\n[Peer]\nPublicKey = {public_key}\nAllowedIPs = 0.0.0.0/0\nEndpoint = mock-server.example.com:51820",
            "server_id": "mock-server-1"
        })
        
    except Exception as e:
        logger.exception(f"Error in create_peer: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/remove/<public_key>', methods=['DELETE'])
def remove_peer(public_key):
    # Имитация задержки
    time.sleep(0.1)
    
    # Проверяем, существует ли пир
    if public_key in PEERS:
        # Удаляем пир
        del PEERS[public_key]
        return jsonify({
            "success": True,
            "message": f"Peer {public_key} successfully removed"
        })
    else:
        # Если пир не найден, возвращаем ошибку
        return jsonify({
            "success": False,
            "message": f"Peer {public_key} not found"
        }), 404

@app.route('/api/servers', methods=['GET'])
def get_servers():
    # Имитация ответа database-service со списком серверов
    return jsonify({
        "servers": [
            {
                "id": "mock-server-1",
                "name": "Mock Server 1",
                "location": "Mock/Location",
                "geolocation_id": 1,
                "api_url": "http://localhost:5002",  # URL этого мок-сервера
                "auth_type": "api_key",
                "api_key": "mock-api-key"
            }
        ]
    })

@app.route('/api/servers/add', methods=['POST'])
def add_server():
    data = request.json
    server_id = f"mock-server-{uuid.uuid4().hex[:8]}"
    
    return jsonify({
        "success": True,
        "message": "Server added successfully",
        "server_id": server_id
    })

@app.route('/api/peers/find', methods=['GET'])
def find_peer():
    public_key = request.args.get('public_key')
    
    if public_key in PEERS:
        return jsonify({
            "server_id": "mock-server-1"
        })
    else:
        return jsonify({
            "error": "Peer not found"
        }), 404

if __name__ == '__main__':
    logger.info("Starting mock WireGuard server on port 5002")
    app.run(host='0.0.0.0', port=5002)