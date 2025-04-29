from flask_login import UserMixin

class User(UserMixin):
    """
    User model for authentication.
    This is a simple implementation for use with Flask-Login.
    """
    
    def __init__(self, id, username, email, role='user'):
        """
        Initialize a User object.
        
        Args:
            id (int): User ID
            username (str): Username
            email (str): User email
            role (str): User role ('admin', 'user', etc.)
        """
        self.id = id
        self.username = username
        self.email = email
        self.role = role
    
    def get_id(self):
        """Required for Flask-Login."""
        return str(self.id)
    
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role == 'admin'
    
    def is_active(self):
        """Required for Flask-Login."""
        return True
    
    def is_anonymous(self):
        """Required for Flask-Login."""
        return False
    
    def is_authenticated(self):
        """Required for Flask-Login."""
        return True