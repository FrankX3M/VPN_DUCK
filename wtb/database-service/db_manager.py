import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
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
    
    # Создаем таблицу payments для хранения информации о платежах через Telegram Stars
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        config_id INTEGER REFERENCES configurations(id),
        stars_amount INTEGER NOT NULL,
        transaction_id TEXT,
        status TEXT NOT NULL,
        days_extended INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

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
            RETURNING id
            """,
            (user_id, config, public_key, expiry_time, active, datetime.now())
        )
        
        config_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "config_id": config_id}), 201
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

@app.route('/config/extend', methods=['POST'])
def extend_config():
    """Продление срока действия конфигурации WireGuard."""
    data = request.json
    
    required_fields = ['user_id', 'days', 'stars_amount', 'transaction_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    days = data.get('days')
    stars_amount = data.get('stars_amount')
    transaction_id = data.get('transaction_id')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем активную конфигурацию пользователя
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = %s AND active = TRUE",
            (user_id,)
        )
        
        config = cursor.fetchone()
        if not config:
            conn.close()
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
        
        # Проверяем, не был ли уже использован этот transaction_id
        cursor.execute(
            "SELECT id FROM payments WHERE transaction_id = %s",
            (transaction_id,)
        )
        
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Транзакция уже обработана"}), 400
        
        # Рассчитываем новое время истечения
        current_expiry = config['expiry_time']
        
        # Если срок истек, начинаем отсчет от текущего времени
        if current_expiry < datetime.now():
            new_expiry = datetime.now() + timedelta(days=days)
        else:
            new_expiry = current_expiry + timedelta(days=days)
        
        # Обновляем время истечения конфигурации
        cursor.execute(
            "UPDATE configurations SET expiry_time = %s WHERE id = %s",
            (new_expiry, config['id'])
        )
        
        # Записываем информацию о платеже
        cursor.execute(
            """
            INSERT INTO payments 
            (user_id, config_id, stars_amount, transaction_id, status, days_extended, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, config['id'], stars_amount, transaction_id, 'completed', days, datetime.now())
        )
        
        payment_id = cursor.fetchone()['id']
        
        conn.commit()
        
        # Подготавливаем данные для ответа
        result = {
            "status": "success",
            "payment_id": payment_id,
            "config_id": config['id'],
            "new_expiry_time": new_expiry.isoformat(),
            "days_extended": days
        }
        
        conn.close()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Ошибка при продлении конфигурации: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/payments/history/<int:user_id>', methods=['GET'])
def get_payment_history(user_id):
    """Получение истории платежей пользователя."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT p.*, c.expiry_time, c.public_key 
            FROM payments p
            JOIN configurations c ON p.config_id = c.id
            WHERE p.user_id = %s
            ORDER BY p.created_at DESC
            """,
            (user_id,)
        )
        
        payments = cursor.fetchall()
        
        # Преобразуем timestamp в строки для JSON-сериализации
        for payment in payments:
            payment['created_at'] = payment['created_at'].isoformat()
            payment['expiry_time'] = payment['expiry_time'].isoformat()
        
        conn.close()
        
        return jsonify({"payments": payments}), 200
    except Exception as e:
        logger.error(f"Ошибка при получении истории платежей: {str(e)}")
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

@app.route('/stats', methods=['GET'])
def get_stats():
    """Получение статистики по конфигурациям и платежам."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Общее количество конфигураций
        cursor.execute("SELECT COUNT(*) as total FROM configurations")
        total_configs = cursor.fetchone()['total']
        
        # Количество активных конфигураций
        cursor.execute("SELECT COUNT(*) as active FROM configurations WHERE active = TRUE")
        active_configs = cursor.fetchone()['active']
        
        # Количество конфигураций с истекшим сроком
        cursor.execute(
            "SELECT COUNT(*) as expired FROM configurations WHERE active = TRUE AND expiry_time < %s",
            (datetime.now(),)
        )
        expired_configs = cursor.fetchone()['expired']
        
        # Общая сумма платежей в звездах
        cursor.execute("SELECT SUM(stars_amount) as total_stars FROM payments WHERE status = 'completed'")
        result = cursor.fetchone()
        total_stars = result['total_stars'] if result['total_stars'] else 0
        
        # Количество платежей
        cursor.execute("SELECT COUNT(*) as total_payments FROM payments WHERE status = 'completed'")
        total_payments = cursor.fetchone()['total_payments']
        
        # Статистика по продлениям
        cursor.execute(
            """
            SELECT days_extended, COUNT(*) as count, SUM(stars_amount) as stars
            FROM payments 
            WHERE status = 'completed'
            GROUP BY days_extended
            ORDER BY days_extended
            """
        )
        extensions_stats = cursor.fetchall()
        
        # Статистика по пользователям
        cursor.execute(
            """
            SELECT user_id, COUNT(*) as payments_count, SUM(stars_amount) as total_stars
            FROM payments 
            WHERE status = 'completed'
            GROUP BY user_id
            ORDER BY total_stars DESC
            LIMIT 10
            """
        )
        top_users = cursor.fetchall()
        
        conn.close()
        
        stats = {
            "configurations": {
                "total": total_configs,
                "active": active_configs,
                "expired": expired_configs
            },
            "payments": {
                "total_count": total_payments,
                "total_stars": total_stars,
                "extensions_stats": extensions_stats,
                "top_users": top_users
            }
        }
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=5002)