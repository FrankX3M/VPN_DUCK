import random
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import math

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
    {
        'id': 1,
        'code': 'US',
        'name': 'United States',
        'available': True,
        'description': 'United States data centers'
    },
    {
        'id': 2,
        'code': 'EU',
        'name': 'Europe',
        'available': True,
        'description': 'European data centers'
    },
    {
        'id': 3,
        'code': 'AP',
        'name': 'Asia Pacific',
        'available': True,
        'description': 'Asia Pacific data centers'
    },
    {
        'id': 4,
        'code': 'SA',
        'name': 'South America',
        'available': False,
        'description': 'South American data centers (coming soon)'
    }
]

# Mock server data
MOCK_SERVERS = [
    {
        'id': 1,
        'name': 'US Server 1',
        'endpoint': 'us1.example.com',
        'port': 51820,
        'address': '10.0.0.1/24',
        'public_key': 'AcB6deHgjkR9zZR5yJnX0RBLa1KLMj/tU+SrM8Tx8DA=',
        'geolocation_id': 1,
        'geolocation_name': 'United States',
        'status': 'active',
        'api_key': 'a1b2c3d4e5f6',
        'api_url': 'http://us1.example.com:51820/api',
        'max_peers': 100
    },
    {
        'id': 2,
        'name': 'EU Server 1',
        'endpoint': 'eu1.example.com',
        'port': 51820,
        'address': '10.0.1.1/24',
        'public_key': 'FgD9uVsGIJm3bOHWnWCqSq0KLdkq0gFhVWB0yZ9lGlA=',
        'geolocation_id': 2,
        'geolocation_name': 'Europe',
        'status': 'active',
        'api_key': 'f6e5d4c3b2a1',
        'api_url': 'http://eu1.example.com:51820/api',
        'max_peers': 100
    },
    {
        'id': 3,
        'name': 'AP Server 1',
        'endpoint': 'ap1.example.com',
        'port': 51820,
        'address': '10.0.2.1/24',
        'public_key': 'JkL8mnoPqRs0tUv1wXyZ2AbC3dEfGhIjKlM+nOpQrSt=',
        'geolocation_id': 3,
        'geolocation_name': 'Asia Pacific',
        'status': 'inactive',
        'api_key': '1a2b3c4d5e6f',
        'api_url': 'http://ap1.example.com:51820/api',
        'max_peers': 50
    }
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
        if server['id'] == server_id:
            return server
    return None

def find_geolocation(geo_id):
    """Find geolocation by ID in mock data."""
    for geo in MOCK_GEOLOCATIONS:
        if geo['id'] == geo_id:
            return geo
    return None

def filter_servers(filters):
    """Filter servers based on criteria."""
    result = MOCK_SERVERS.copy()
    
    # Apply filters
    if 'search' in filters and filters['search']:
        search_term = filters['search'].lower()
        result = [s for s in result if search_term in s.get('name', '').lower() or 
                                      search_term in s.get('endpoint', '').lower()]
    
    if 'geolocation_id' in filters:
        result = [s for s in result if s.get('geolocation_id') == filters['geolocation_id']]
    
    if 'status' in filters:
        result = [s for s in result if s.get('status') == filters['status']]
    
    return result

def generate_mock_metrics(server_id, hours=24):
    """Generate mock metrics data for a server."""
    # Seed random with server_id to get consistent data for the same server
    random.seed(server_id)
    
    # Generate history data points
    history = []
    now = datetime.now()
    
    # Different baseline values for different servers
    base_latency = 20 + (server_id * 5)  # ms
    base_packet_loss = 0.5 + (server_id * 0.2)  # %
    base_resource_usage = 10 + (server_id * 3)  # %
    
    # Generate data points at 5-minute intervals
    for i in range(hours * 12):  # 12 points per hour (5-minute intervals)
        timestamp = now - timedelta(minutes=5 * i)
        
        # Add some random variation
        latency = max(1, base_latency + random.uniform(-10, 10))
        packet_loss = max(0, min(100, base_packet_loss + random.uniform(-0.5, 1.5)))
        resource_usage = max(0, min(100, base_resource_usage + random.uniform(-5, 15)))
        
        # Add periodic patterns
        time_factor = i / 12  # Convert to hours
        latency += 5 * math.sin(time_factor * math.pi / 6)  # 12-hour cycle
        resource_usage += 10 * math.sin(time_factor * math.pi / 12)  # 24-hour cycle
        
        # Occasional spikes
        if random.random() < 0.05:  # 5% chance of spike
            latency *= random.uniform(1.5, 3)
            packet_loss *= random.uniform(2, 5)
        
        history.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ping_ms': round(latency, 1),
            'packet_loss_percent': round(packet_loss, 2),
            'resource_usage_percent': round(resource_usage, 1),
            'connected_peers': random.randint(5, 20)
        })
    
    # Ensure history is in chronological order (oldest to newest)
    history.reverse()
    
    # Current stats (latest values)
    current = history[-1] if history else {
        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
        'ping_ms': 0,
        'packet_loss_percent': 0,
        'resource_usage_percent': 0,
        'connected_peers': 0
    }
    
    # Calculate aggregates
    latency_values = [entry['ping_ms'] for entry in history]
    packet_loss_values = [entry['packet_loss_percent'] for entry in history]
    resource_usage_values = [entry['resource_usage_percent'] for entry in history]
    
    aggregates = {
        'avg_latency': round(sum(latency_values) / len(latency_values), 1) if latency_values else 0,
        'min_latency': round(min(latency_values), 1) if latency_values else 0,
        'max_latency': round(max(latency_values), 1) if latency_values else 0,
        'avg_packet_loss': round(sum(packet_loss_values) / len(packet_loss_values), 2) if packet_loss_values else 0,
        'avg_resource_usage': round(sum(resource_usage_values) / len(resource_usage_values), 1) if resource_usage_values else 0
    }
    
    return {
        'server_id': server_id,
        'current': current,
        'history': history,
        'aggregates': aggregates
    }