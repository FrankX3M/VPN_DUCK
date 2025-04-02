import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры подключения к PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'wireguard')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')

def init_db():
    """Инициализация базы данных."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Создаем таблицу configurations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configurations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        config TEXT NOT NULL,
        public_key TEXT NOT NULL,
        expiry_time TIMESTAMP NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Получение соединения с базой данных PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

@app.route('/config', methods=['POST'])
def create_config():
    """Сохранение новой конфигурации WireGuard в базе данных."""
    data = request.json
    
    required_fields = ['user_id', 'config', 'expiry_time']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    config = data.get('config')
    expiry_time = data.get('expiry_time')
    active = data.get('active', True)
    
    # Извлекаем публичный ключ из конфига
    public_key = None
    for line in config.split('\n'):
        if line.startswith('[Peer]'):
            for peer_line in config.split('\n'):
                if peer_line.startswith('PublicKey'):
                    public_key = peer_line.split('=')[1].strip()
                    break
            break
    
    if not public_key:
        return jsonify({"error": "Не удалось извлечь публичный ключ из конфигурации"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Деактивируем существующие конфигурации для этого пользователя
        cursor.execute(
            "UPDATE configurations SET active = FALSE WHERE user_id = %s",
            (user_id,)
        )
        
        # Вставляем новую конфигурацию
        cursor.execute(
            """
            INSERT INTO configurations 
            (user_id, config, public_key, expiry_time, active, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, config, public_key, expiry_time, active, datetime.now())
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success"}), 201
    except Exception as e:
        logger.error(f"Ошибка при сохранении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/config/<int:user_id>', methods=['GET'])
def get_user_config(user_id):
    """Получение активной конфигурации для пользователя."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = %s AND active = TRUE",
            (user_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Преобразуем timestamp в строку для JSON-сериализации
            row['expiry_time'] = row['expiry_time'].isoformat()
            row['created_at'] = row['created_at'].isoformat()
            
            return jsonify(row), 200
        else:
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
    except Exception as e:
        logger.error(f"Ошибка при получении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cleanup_expired', methods=['POST'])
def cleanup_expired():
    """Очистка истекших конфигураций."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем истекшие конфигурации
        cursor.execute(
            "SELECT * FROM configurations WHERE active = TRUE AND expiry_time < %s",
            (datetime.now(),)
        )
        
        expired_configs = cursor.fetchall()
        
        # Деактивируем истекшие конфигурации
        cursor.execute(
            "UPDATE configurations SET active = FALSE WHERE active = TRUE AND expiry_time < %s",
            (datetime.now(),)
        )
        
        conn.commit()
        
        # Для каждой истекшей конфигурации вызываем сервис WireGuard для удаления пира
        import requests
        wireguard_service_url = os.getenv('WIREGUARD_SERVICE_URL', 'http://wireguard-service:5001')
        
        for config in expired_configs:
            requests.delete(f"{wireguard_service_url}/remove/{config['public_key']}")
        
        conn.close()
        
        return jsonify({"status": "success", "cleaned": len(expired_configs)}), 200
    except Exception as e:
        logger.error(f"Ошибка при очистке истекших конфигураций: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=5002)