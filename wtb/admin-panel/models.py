from flask_login import UserMixin

class User(UserMixin):
    """User model for authentication."""
    
    def __init__(self, id, username, email, role='user'):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
    
    def get_id(self):
        """Required for Flask-Login."""
        return str(self.id)
    
    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def __repr__(self):
        return f"<User {self.username}>"

class Server:
    """Server model for WireGuard remote servers."""
    
    def __init__(self, id, server_id, name, endpoint, port, address, public_key, geolocation_id, 
                 location=None, geolocation_name=None, status='active', api_key=None, 
                 api_url=None, api_path=None, max_peers=None, skip_api_check=False):
        self.id = id
        self.server_id = server_id  # Уникальный идентификатор сервера в таблице remote_servers
        self.name = name
        self.endpoint = endpoint
        self.port = port
        self.address = address
        self.public_key = public_key
        self.geolocation_id = geolocation_id
        self.location = location  # Соответствует полю location в remote_servers
        self.geolocation_name = geolocation_name
        self.status = status  # 'active' соответствует is_active=TRUE в remote_servers
        self.api_key = api_key
        self.api_url = api_url
        self.api_path = api_path or '/status'
        self.max_peers = max_peers
        self.skip_api_check = skip_api_check
        
    @classmethod
    def from_dict(cls, data):
        """Create server object from dictionary."""
        if not data:
            return None
            
        return cls(
            id=data.get('id'),
            server_id=data.get('server_id'),
            name=data.get('name'),
            endpoint=data.get('endpoint'),
            port=data.get('port'),
            address=data.get('address'),
            public_key=data.get('public_key'),
            geolocation_id=data.get('geolocation_id'),
            location=data.get('location'),
            geolocation_name=data.get('geolocation_name'),
            status=data.get('status', 'active'),
            api_key=data.get('api_key'),
            api_url=data.get('api_url'),
            api_path=data.get('api_path'),
            max_peers=data.get('max_peers'),
            skip_api_check=data.get('skip_api_check', False)
        )
    
    @classmethod
    def from_remote_server(cls, remote_server):
        """Создание объекта Server из данных remote_servers
        
        Args:
            remote_server (dict): Данные из таблицы remote_servers
            
        Returns:
            Server: Объект Server
        """
        return cls(
            id=remote_server.get('id'),
            server_id=remote_server.get('server_id'),
            name=remote_server.get('name'),
            endpoint=remote_server.get('endpoint'),
            port=remote_server.get('port'),
            address=remote_server.get('address'),
            public_key=remote_server.get('public_key'),
            geolocation_id=remote_server.get('geolocation_id'),
            location=remote_server.get('location'),
            geolocation_name=remote_server.get('geolocation_name'),
            status='active' if remote_server.get('is_active', True) else 'inactive',
            api_key=remote_server.get('api_key'),
            api_url=remote_server.get('api_url'),
            api_path=remote_server.get('api_path'),
            max_peers=remote_server.get('max_peers'),
            skip_api_check=remote_server.get('skip_api_check', False)
        )
    
    def to_dict(self):
        """Convert server object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'endpoint': self.endpoint,
            'port': self.port,
            'address': self.address,
            'public_key': self.public_key,
            'geolocation_id': self.geolocation_id,
            'status': self.status,
            'api_key': self.api_key,
            'api_url': self.api_url,
            'api_path': self.api_path,
            'max_peers': self.max_peers,
            'geolocation_name': self.geolocation_name,
            'skip_api_check': self.skip_api_check
        }
    
    def __repr__(self):
        return f"<Server {self.name} ({self.endpoint}:{self.port})>"

class Geolocation:
    """Geolocation model for server locations."""
    
    def __init__(self, id, code, name, available=True, description=None):
        self.id = id
        self.code = code
        self.name = name
        self.available = available
        self.description = description
    
    @classmethod
    def from_dict(cls, data):
        """Create geolocation object from dictionary."""
        return cls(
            id=data.get('id'),
            code=data.get('code'),
            name=data.get('name'),
            available=data.get('available', True),
            description=data.get('description')
        )
    
    def to_dict(self):
        """Convert geolocation object to dictionary."""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'available': self.available,
            'description': self.description
        }
    
    def __repr__(self):
        return f"<Geolocation {self.code} - {self.name}>"