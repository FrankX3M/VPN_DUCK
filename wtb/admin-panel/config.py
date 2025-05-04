import os
import secrets

# Flag for using mock data in development mode
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'

METRICS_SERVICE_URL = os.environ.get('METRICS_SERVICE_URL', 'http://localhost:5003')
# Import mock data for development mode
if USE_MOCK_DATA:
    from utils.mock_data import (MOCK_SERVERS, MOCK_GEOLOCATIONS, 
                              generate_mock_metrics, find_server, 
                              find_geolocation, filter_servers,
                              authenticate_user, MOCK_USERS)

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    WTF_CSRF_ENABLED = True
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # API and service URLs
    API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    API_KEY = os.environ.get('API_KEY', 'dev_key')
    DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://localhost:5001')
    WIREGUARD_SERVICE_URL = os.environ.get('WIREGUARD_SERVICE_URL', 'http://localhost:5002')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # In production, SECRET_KEY must be set as environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Ensure API keys and endpoints are configured properly
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Check for required configuration in production
        assert os.environ.get('SECRET_KEY'), "SECRET_KEY environment variable must be set"
        assert os.environ.get('API_KEY'), "API_KEY environment variable must be set"
        assert os.environ.get('DATABASE_SERVICE_URL'), "DATABASE_SERVICE_URL must be set"
        assert os.environ.get('WIREGUARD_SERVICE_URL'), "WIREGUARD_SERVICE_URL must be set"

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}