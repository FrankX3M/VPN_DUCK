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

# class Server:
#     """Server model for WireGuard servers."""
    
#     def __init__(self, id, name, endpoint, port, address, public_key, geolocation_id, 
#                  status='active', api_key=None, api_url=None, max_peers=None, 
#                  geolocation_name=None):
#         self.id = id
#         self.name = name
#         self.endpoint = endpoint
#         self.port = port
#         self.address = address
#         self.public_key = public_key
#         self.geolocation_id = geolocation_id
#         self.geolocation_name = geolocation_name
#         self.status = status
#         self.api_key = api_key
#         self.api_url = api_url
#         self.max_peers = max_peers
    
#     @classmethod
#     def from_dict(cls, data):
#         """Create server object from dictionary."""
#         return cls(
#             id=data.get('id'),
#             name=data.get('name'),
#             endpoint=data.get('endpoint'),
#             port=data.get('port'),
#             address=data.get('address'),
#             public_key=data.get('public_key'),
#             geolocation_id=data.get('geolocation_id'),
#             status=data.get('status', 'active'),
#             api_key=data.get('api_key'),
#             api_url=data.get('api_url'),
#             max_peers=data.get('max_peers'),
#             geolocation_name=data.get('geolocation_name')
#         )
    
#     def to_dict(self):
#         """Convert server object to dictionary."""
#         return {
#             'id': self.id,
#             'name': self.name,
#             'endpoint': self.endpoint,
#             'port': self.port,
#             'address': self.address,
#             'public_key': self.public_key,
#             'geolocation_id': self.geolocation_id,
#             'status': self.status,
#             'api_key': self.api_key,
#             'api_url': self.api_url,
#             'max_peers': self.max_peers,
#             'geolocation_name': self.geolocation_name
#         }
    
#     def __repr__(self):
#         return f"<Server {self.name} ({self.endpoint}:{self.port})>"
class Server:
    """Server model for WireGuard servers."""
    
    def __init__(self, id, name, endpoint, port, address, public_key, geolocation_id, 
                 status='active', api_key=None, api_url=None, max_peers=None, 
                 geolocation_name=None):
        self.id = id
        self.name = name
        self.endpoint = endpoint
        self.port = port
        self.address = address
        self.public_key = public_key
        self.geolocation_id = geolocation_id
        self.geolocation_name = geolocation_name
        self.status = status
        self.api_key = api_key
        self.api_url = api_url
        self.max_peers = max_peers
    
    @classmethod
    def from_dict(cls, data):
        """Create server object from dictionary."""
        # Проверяем, что data - словарь
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data)}")
            
        # Если в словаре есть ключ 'server', используем его как источник данных
        if 'server' in data and isinstance(data['server'], dict):
            data = data['server']
            
        # Получаем идентификатор сервера
        server_id = data.get('id')
        if server_id is None and 'server_id' in data:
            server_id = data.get('server_id')  # Альтернативное имя поля
            
        # Преобразование типов данных при необходимости
        port = data.get('port')
        if port is not None and isinstance(port, str):
            try:
                port = int(port)
            except ValueError:
                port = None
                
        geolocation_id = data.get('geolocation_id')
        if geolocation_id is not None and isinstance(geolocation_id, str):
            try:
                geolocation_id = int(geolocation_id)
            except ValueError:
                geolocation_id = None
                
        # Создаем объект сервера
        return cls(
            id=server_id,
            name=data.get('name'),
            endpoint=data.get('endpoint'),
            port=port,
            address=data.get('address'),
            public_key=data.get('public_key'),
            geolocation_id=geolocation_id,
            status=data.get('status', 'active'),
            api_key=data.get('api_key'),
            api_url=data.get('api_url'),
            max_peers=data.get('max_peers'),
            geolocation_name=data.get('geolocation_name')
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
            'max_peers': self.max_peers,
            'geolocation_name': self.geolocation_name
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