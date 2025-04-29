# Add this at the beginning of your app.py file, before any routes are defined

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
import secrets
import logging
import os
from forms import FilterForm, ServerForm, GeolocationForm
from utils.chart_generator import ChartGenerator
from utils.db_client import DatabaseClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database client
db_client = DatabaseClient(
    base_url=os.environ.get('API_BASE_URL', 'http://localhost:5000'),
    api_key=os.environ.get('API_KEY', 'dev_key')
)

# Import models and user loader
from models import User

@login_manager.user_loader
def load_user(user_id):
    # Fetch user from API or local storage
    try:
        response = db_client.get(f'/api/users/{user_id}')
        if response.status_code == 200:
            user_data = response.json()
            return User(
                id=user_data.get('id'),
                username=user_data.get('username'),
                email=user_data.get('email'),
                role=user_data.get('role', 'user')
            )
    except Exception as e:
        logger.exception(f"Error loading user: {str(e)}")
    
    return None

# Now, all your route definitions should come after this setup code