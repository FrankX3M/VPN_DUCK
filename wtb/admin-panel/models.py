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
    """Server model for WireGuard servers."""
    
    def __init__(self, id, name, endpoint, port, address, public_key, geolocation_id, 
                 status='active', api_key=None, api_url=None, api_path=None, 
                 max_peers=None, geolocation_name=None, skip_api_check=False):
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
        self.api_path = api_path or '/status'
        self.max_peers = max_peers
        self.skip_api_check = skip_api_check
    
    @classmethod
    def from_dict(cls, data):
        """Create server object from dictionary."""
        # Check that data is a dictionary
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data)}")
            
        # If dictionary has a 'server' key, use it as the source
        if 'server' in data and isinstance(data['server'], dict):
            data = data['server']
            
        # Get server ID
        server_id = data.get('id')
        if server_id is None and 'server_id' in data:
            server_id = data.get('server_id')  # Alternative field name
            
        # Convert data types if needed
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
                
        # Handle boolean fields
        skip_api_check = data.get('skip_api_check', False)
        if isinstance(skip_api_check, str):
            skip_api_check = skip_api_check.lower() in ('true', 'yes', '1', 'y')
                
        # Create server object
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
            api_path=data.get('api_path', '/status'),
            max_peers=data.get('max_peers'),
            geolocation_name=data.get('geolocation_name'),
            skip_api_check=skip_api_check
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