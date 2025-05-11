import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flag for using mock data in development mode
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'

# Get configuration from environment variables
ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'fvcfq9d3ycefnvmftiaso')
METRICS_SERVICE_URL = os.environ.get('METRICS_SERVICE_URL', 'http://metrics-collector:5003')
DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:5002')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '5YE2w8bxd9')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

# Import mock data for development mode
if USE_MOCK_DATA:
    from utils.mock_data import (MOCK_SERVERS, MOCK_GEOLOCATIONS, 
                              generate_mock_metrics, find_server, 
                              find_geolocation, filter_servers,
                              authenticate_user, MOCK_USERS)

class Config:
    """Base configuration class."""
    # Use the ADMIN_SECRET_KEY from environment variables
    SECRET_KEY = ADMIN_SECRET_KEY
    WTF_CSRF_ENABLED = True
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # API and service URLs
    # API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5003')
    API_BASE_URL = os.environ.get('API_BASE_URL', 'http://database-service:5002')
    # Use ADMIN_SECRET_KEY as the API_KEY for authentication
    API_KEY = ADMIN_SECRET_KEY
    DATABASE_SERVICE_URL = DATABASE_SERVICE_URL
    WIREGUARD_SERVICE_URL = os.environ.get('WIREGUARD_SERVICE_URL', 'http://wireguard-proxy:5001')
    
    # Database configuration
    DB_HOST = os.environ.get('DB_HOST', 'db')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'vpn_duck')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = POSTGRES_PASSWORD
    
    # Construct database URI
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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
    SECRET_KEY = ADMIN_SECRET_KEY
    
    # Ensure API keys and endpoints are configured properly
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Check for required configuration in production
        assert ADMIN_SECRET_KEY, "ADMIN_SECRET_KEY environment variable must be set"
        assert DATABASE_SERVICE_URL, "DATABASE_SERVICE_URL must be set"
        assert os.environ.get('WIREGUARD_SERVICE_URL'), "WIREGUARD_SERVICE_URL must be set"

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}