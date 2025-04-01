import os
import json
import sqlite3
from datetime import datetime
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "wireguard.db")

def init_db():
    """Initialize the database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create configurations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configurations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        config TEXT NOT NULL,
        public_key TEXT NOT NULL,
        expiry_time TEXT NOT NULL,
        active BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/config', methods=['POST'])
def create_config():
    """Save a new WireGuard configuration to the database."""
    data = request.json
    
    required_fields = ['user_id', 'config', 'expiry_time']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    user_id = data.get('user_id')
    config = data.get('config')
    expiry_time = data.get('expiry_time')
    active = data.get('active', True)
    
    # Extract public key from config
    public_key = None
    for line in config.split('\n'):
        if line.startswith('[Peer]'):
            for peer_line in config.split('\n'):
                if peer_line.startswith('PublicKey'):
                    public_key = peer_line.split('=')[1].strip()
                    break
            break
    
    if not public_key:
        return jsonify({"error": "Could not extract public key from config"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Deactivate existing configurations for this user
        cursor.execute(
            "UPDATE configurations SET active = 0 WHERE user_id = ?",
            (user_id,)
        )
        
        # Insert new configuration
        cursor.execute(
            """
            INSERT INTO configurations 
            (user_id, config, public_key, expiry_time, active, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, config, public_key, expiry_time, active, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success"}), 201
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/config/<int:user_id>', methods=['GET'])
def get_user_config(user_id):
    """Get the active configuration for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = ? AND active = 1",
            (user_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                "id": row['id'],
                "user_id": row['user_id'],
                "config": row['config'],
                "public_key": row['public_key'],
                "expiry_time": row['expiry_time'],
                "active": bool(row['active']),
                "created_at": row['created_at']
            }), 200
        else:
            return jsonify({"error": "No active configuration found"}), 404
    except Exception as e:
        logger.error(f"Error retrieving configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cleanup_expired', methods=['POST'])
def cleanup_expired():
    """Cleanup expired configurations."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get expired configurations
        cursor.execute(
            "SELECT * FROM configurations WHERE active = 1 AND expiry_time < ?",
            (datetime.now().isoformat(),)
        )
        
        expired_configs = cursor.fetchall()
        
        # Deactivate expired configurations
        cursor.execute(
            "UPDATE configurations SET active = 0 WHERE active = 1 AND expiry_time < ?",
            (datetime.now().isoformat(),)
        )
        
        conn.commit()
        
        # For each expired configuration, call the WireGuard service to remove the peer
        import requests
        wireguard_service_url = os.getenv('WIREGUARD_SERVICE_URL', 'http://wireguard-service:5001')
        
        for config in expired_configs:
            requests.delete(f"{wireguard_service_url}/remove/{config['public_key']}")
        
        conn.close()
        
        return jsonify({"status": "success", "cleaned": len(expired_configs)}), 200
    except Exception as e:
        logger.error(f"Error cleaning up expired configurations: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5002)