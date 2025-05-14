import random
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np  # Use NumPy instead of math
import uuid

# Mock user data for development mode
MOCK_USERS = [
    {
        'id': 1,
        'username': 'admin',
        'password_hash': generate_password_hash('admin'),
        'email': 'admin@example.com',
        'role': 'admin'
    },
    {
        'id': 2,
        'username': 'user',
        'password_hash': generate_password_hash('user'),
        'email': 'user@example.com',
        'role': 'user'
    }
]

# Mock geolocation data
MOCK_GEOLOCATIONS = [
    {'id': 1, 'code': 'ru', 'name': 'Россия', 'available': True, 'description': 'Серверы в России'},
    {'id': 2, 'code': 'nl', 'name': 'Нидерланды', 'available': True, 'description': 'Серверы в Нидерландах'},
    {'id': 3, 'code': 'us', 'name': 'США', 'available': True, 'description': 'Серверы в США'},
    {'id': 4, 'code': 'jp', 'name': 'Япония', 'available': True, 'description': 'Серверы в Японии'},
    {'id': 5, 'code': 'de', 'name': 'Германия', 'available': False, 'description': 'Серверы в Германии (временно недоступны)'}
]

# Mock server data
MOCK_SERVERS = [
    {'id': 1, 'server_id': 'srv-123456', 'name': 'Москва-1', 'endpoint': 'msc01.example.com', 'port': 51820,
     'address': '10.0.0.1/24', 'public_key': 'abcdefghijklmnopqrstuvwxyz12345678901234=',
     'geolocation_id': 1, 'geolocation_name': 'Россия', 'status': 'active',
     'api_key': '1234567890abcdef', 'api_url': 'http://msc01.example.com:5000', 'api_path': '/status',
     'max_peers': 100, 'skip_api_check': True},
    
    {'id': 2, 'server_id': 'srv-4b31d66b', 'name': '5.180.137.197', 'endpoint': '5.180.137.197', 'port': 51820,
     'address': '10.66.66.1/24', 'public_key': 'nUEmAixEDPJemHxUEim2G6oQvoSxU94grV7WhrnVumc=',
     'geolocation_id': 4, 'geolocation_name': 'Япония', 'status': 'active',
     'api_key': '41273e25380ac6354636e22ff40a586f', 'api_url': 'http://5.180.137.197:5000', 'api_path': '/status',
     'max_peers': None, 'skip_api_check': False},
    
    {'id': 3, 'server_id': 'srv-789012', 'name': 'Амстердам-1', 'endpoint': 'ams01.example.com', 'port': 51820,
     'address': '10.0.2.1/24', 'public_key': 'zyxwvutsrqponmlkjihgfedcba12345678901234=',
     'geolocation_id': 2, 'geolocation_name': 'Нидерланды', 'status': 'degraded',
     'api_key': 'fedcba0987654321', 'api_url': 'http://ams01.example.com:5000', 'api_path': '/status',
     'max_peers': 50, 'skip_api_check': False}
]

def authenticate_user(username, password):
    """Authenticate user with mock data."""
    for user in MOCK_USERS:
        if user['username'] == username and check_password_hash(user['password_hash'], password):
            return user
    return None

def find_server(server_id):
    """Find server by ID in mock data."""
    for server in MOCK_SERVERS:
        if isinstance(server, dict) and 'id' in server and server['id'] == server_id:
            return server
    return None

def find_geolocation(geo_id):
    """Find geolocation by ID in mock data."""
    for geo in MOCK_GEOLOCATIONS:
        if isinstance(geo, dict) and 'id' in geo and geo['id'] == geo_id:
            return geo
    return None

def filter_servers(filters=None):
    """Filter servers based on criteria."""
    if not filters:
        return MOCK_SERVERS
    
    filtered_servers = []
    for server in MOCK_SERVERS:
        match = True
        
        # Проверка поискового запроса
        if 'search' in filters and filters['search']:
            search_term = filters['search'].lower()
            if (search_term not in server.get('name', '').lower() and 
                search_term not in server.get('endpoint', '').lower() and
                search_term not in server.get('address', '').lower()):
                match = False
        
        # Проверка геолокации
        if 'geolocation_id' in filters and filters['geolocation_id']:
            if server.get('geolocation_id') != filters['geolocation_id']:
                match = False
        
        # Проверка статуса
        if 'status' in filters and filters['status'] != 'all':
            if server.get('status') != filters['status']:
                match = False
        
        if match:
            filtered_servers.append(server)
    
    return filtered_servers

def generate_mock_metrics(server_id):
    """Generate mock metrics data for a server."""
    server = find_server(server_id)
    if not server:
        return None
    
    # Текущие показатели
    current = {
        'timestamp': datetime.now().isoformat(),
        'latency': random.uniform(5, 100),  # ms
        'packet_loss': random.uniform(0, 5),  # %
        'cpu_usage': random.uniform(5, 80),  # %
        'memory_usage': random.uniform(10, 90),  # %
        'disk_usage': random.uniform(20, 95),  # %
        'bandwidth_in': random.uniform(1, 50),  # Mbps
        'bandwidth_out': random.uniform(1, 50),  # Mbps
        'connected_clients': random.randint(0, server.get('max_peers', 50)),
        'uptime': random.randint(3600, 2592000),  # seconds (1 hour to 30 days)
        'is_available': random.choices([True, False], weights=[0.95, 0.05])[0]
    }
    
    # История метрик за последние 24 часа
    history = []
    now = datetime.now()
    
    for hour in range(24, 0, -1):
        timestamp = now - timedelta(hours=hour)
        is_available = random.choices([True, False], weights=[0.95, 0.05])[0]
        
        # Базовые значения для каждой метрики
        base_latency = random.uniform(5, 50)
        base_packet_loss = random.uniform(0, 2)
        base_cpu = random.uniform(10, 60)
        base_memory = random.uniform(20, 80)
        base_disk = random.uniform(30, 90)
        base_bw_in = random.uniform(5, 30)
        base_bw_out = random.uniform(5, 30)
        base_clients = random.randint(0, int(server.get('max_peers', 50) * 0.8))
        
        # Имитация нагрузки в зависимости от времени суток
        hour_of_day = timestamp.hour
        time_factor = 1.0
        
        # Повышенная нагрузка в рабочие часы
        if 9 <= hour_of_day <= 18:
            time_factor = 1.5
        # Ночное затишье
        elif 0 <= hour_of_day <= 6:
            time_factor = 0.7
            
        entry = {
            'timestamp': timestamp.isoformat(),
            'latency': base_latency * time_factor * (1.2 if not is_available else 1.0),
            'packet_loss': base_packet_loss * time_factor * (5 if not is_available else 1.0),
            'cpu_usage': base_cpu * time_factor,
            'memory_usage': base_memory,
            'disk_usage': base_disk,
            'bandwidth_in': base_bw_in * time_factor,
            'bandwidth_out': base_bw_out * time_factor,
            'connected_clients': base_clients,
            'is_available': is_available
        }
        
        history.append(entry)
    
    return {
        'current': current,
        'history': history
    }

def find_user_by_id(user_id):
    """Find user by ID in mock data."""
    for user in MOCK_USERS:
        if str(user.get('id')) == str(user_id):
            return user
    return None