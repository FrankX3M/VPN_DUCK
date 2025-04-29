"""
Mock data for development and testing when the API is not available.
This should NOT be used in production.
"""
import datetime
import random
import uuid
import math

# Mock servers
MOCK_SERVERS = [
    {
        "id": 1,
        "name": "US-East Server",
        "endpoint": "us-east.vpnduck.example.com",
        "port": 51820,
        "address": "10.0.1.1/24",
        "public_key": "mK56Xc59gh2QI0U7K7YXpnV1aEIJK6qYYQ/mKQg9rVE=",
        "geolocation_id": 1,
        "geolocation_name": "United States",
        "max_peers": 100,
        "status": "active",
        "api_key": "mock-api-key-us-east",
        "api_url": "http://us-east.api.example.com"
    },
    {
        "id": 2,
        "name": "EU-West Server",
        "endpoint": "eu-west.vpnduck.example.com",
        "port": 51820,
        "address": "10.0.2.1/24",
        "public_key": "jQnXpZ4tB7QkEh6D8KcOPOj2W/YQtR8Lx5cNhsM6rwQ=",
        "geolocation_id": 2,
        "geolocation_name": "Germany",
        "max_peers": 150,
        "status": "active",
        "api_key": "mock-api-key-eu-west",
        "api_url": "http://eu-west.api.example.com"
    },
    {
        "id": 3,
        "name": "AS-SG Server",
        "endpoint": "as-sg.vpnduck.example.com",
        "port": 51820,
        "address": "10.0.3.1/24",
        "public_key": "KvCkdEF7hYGqjL5IuCX2d9LdKhNgbPtScUZ8j34c5rk=",
        "geolocation_id": 3,
        "geolocation_name": "Singapore",
        "max_peers": 120,
        "status": "degraded",
        "api_key": "mock-api-key-as-sg",
        "api_url": "http://as-sg.api.example.com"
    },
    {
        "id": 4,
        "name": "US-West Server",
        "endpoint": "us-west.vpnduck.example.com",
        "port": 51820,
        "address": "10.0.4.1/24",
        "public_key": "z9GhT7JfKcs2AyQv+UmgPT7rLtJNRkfBm7cHPo76TkY=",
        "geolocation_id": 1,
        "geolocation_name": "United States",
        "max_peers": 100,
        "status": "inactive",
        "api_key": "mock-api-key-us-west",
        "api_url": "http://us-west.api.example.com"
    }
]

# Mock geolocations
MOCK_GEOLOCATIONS = [
    {
        "id": 1,
        "code": "US",
        "name": "United States",
        "available": True,
        "description": "Servers located in the United States"
    },
    {
        "id": 2,
        "code": "DE",
        "name": "Germany",
        "available": True,
        "description": "Servers located in Germany"
    },
    {
        "id": 3,
        "code": "SG",
        "name": "Singapore",
        "available": True,
        "description": "Servers located in Singapore"
    },
    {
        "id": 4,
        "code": "JP",
        "name": "Japan",
        "available": False,
        "description": "Servers located in Japan (currently unavailable)"
    }
]

def generate_mock_metrics(server_id, hours=24):
    """Generate mock metrics data for a server."""
    now = datetime.datetime.now()
    history = []
    
    # Base metrics values
    base_latency = 30 + (server_id * 10)  # Different baseline for each server
    base_packet_loss = 0.5 + (server_id * 0.2) 
    base_cpu = 20 + (server_id * 5)
    base_memory = 30 + (server_id * 7)
    
    # Generate history points
    for i in range(hours):
        timestamp = (now - datetime.timedelta(hours=hours-i)).isoformat() + 'Z'
        
        # Add some randomness and periodic fluctuation
        time_factor = math.sin(i / 6) * 0.5  # 6-hour cycle
        random_factor = random.random() * 0.3
        
        # Generate metrics with variation
        latency = max(1, base_latency * (1 + time_factor + random_factor))
        packet_loss = max(0, base_packet_loss * (1 + time_factor + random_factor))
        cpu = min(95, base_cpu * (1 + (time_factor * 0.5) + random_factor))
        memory = min(95, base_memory * (1 + (time_factor * 0.3) + random_factor))
        
        # More peers during "peak hours"
        peak_factor = 0.5 + (0.5 * math.sin((i % 24) / 3.82))
        peers = int(25 * peak_factor * (1 + random_factor))
        
        history.append({
            "timestamp": timestamp,
            "avg_latency": round(latency, 2),
            "avg_packet_loss": round(packet_loss, 2),
            "cpu_usage": round(cpu, 2),
            "memory_usage": round(memory, 2),
            "peers_count": peers,
            "load": round(random.random() * 2, 2)
        })
    
    # Current metrics (slightly different from last history point)
    last = history[-1] if history else {}
    current = {
        "avg_latency": round(last.get("avg_latency", 30) * (1 + (random.random() * 0.1 - 0.05)), 2),
        "avg_packet_loss": round(last.get("avg_packet_loss", 0.5) * (1 + (random.random() * 0.1 - 0.05)), 2),
        "cpu_usage": round(last.get("cpu_usage", 20) * (1 + (random.random() * 0.1 - 0.05)), 2),
        "memory_usage": round(last.get("memory_usage", 30) * (1 + (random.random() * 0.1 - 0.05)), 2),
        "peers_count": last.get("peers_count", 10) + random.randint(-2, 2),
        "load": round(last.get("load", 1.0) * (1 + (random.random() * 0.1 - 0.05)), 2)
    }
    
    return {
        "server_id": server_id,
        "current": current,
        "history": history
    }

# Mock user data
MOCK_USERS = [
    {
        "id": 1,
        "username": "admin",
        "email": "admin@vpnduck.example.com",
        "role": "admin",
        "password": "admin"  # In a real app, this would be hashed
    }
]

# Helper functions for finding mock data
def find_server(server_id):
    """Find a server by ID."""
    return next((s for s in MOCK_SERVERS if s["id"] == server_id), None)

def find_geolocation(geo_id):
    """Find a geolocation by ID."""
    return next((g for g in MOCK_GEOLOCATIONS if g["id"] == geo_id), None)

def find_user(username):
    """Find a user by username."""
    return next((u for u in MOCK_USERS if u["username"] == username), None)

def authenticate_user(username, password):
    """Mock authentication function."""
    user = find_user(username)
    if user and user["password"] == password:
        return user
    return None

def filter_servers(filters=None):
    """Filter servers based on criteria."""
    if not filters:
        return MOCK_SERVERS.copy()
        
    result = MOCK_SERVERS.copy()
    
    # Apply filters
    if 'search' in filters and filters['search']:
        search = filters['search'].lower()
        result = [s for s in result if 
                  search in s.get('name', '').lower() or
                  search in s.get('endpoint', '').lower() or
                  search in str(s.get('id', '')).lower()]
    
    if 'geolocation_id' in filters and filters['geolocation_id'] != 'all':
        geo_id = int(filters['geolocation_id'])
        result = [s for s in result if s.get('geolocation_id') == geo_id]
    
    if 'status' in filters and filters['status'] != 'all':
        status = filters['status']
        result = [s for s in result if s.get('status') == status]
        
    return result