import os
import logging
import json
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from forms import LoginForm
from models import User
from config import USE_MOCK_DATA

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)

def load_local_users():
    """Load local users as a fallback mechanism."""
    users_file = os.environ.get('USERS_FILE', '/app/config/users.json')
    try:
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                return json.load(f)
        else:
            # Create default admin user if file doesn't exist
            default_admin = {
                'admin': {
                    'id': 1,
                    'username': 'admin',
                    'password_hash': generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin')),
                    'email': 'admin@example.com',
                    'role': 'admin'
                }
            }
            # Ensure directory exists
            os.makedirs(os.path.dirname(users_file), exist_ok=True)
            # Write default user to file
            with open(users_file, 'w') as f:
                json.dump(default_admin, f, indent=2)
            return default_admin
    except Exception as e:
        logger.exception(f"Error loading users: {str(e)}")
        # Return default admin user as fallback
        return {
            'admin': {
                'id': 1,
                'username': 'admin',
                'password_hash': generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin')),
                'email': 'admin@example.com',
                'role': 'admin'
            }
        }

def authenticate_local_user(username, password):
    """Authenticate user against local storage as fallback."""
    users = load_local_users()
    
    if username in users:
        user_data = users[username]
        # Check if using password_hash or fallback to plain text comparison
        if 'password_hash' in user_data:
            if check_password_hash(user_data['password_hash'], password):
                return User(
                    id=user_data.get('id', 1),
                    username=user_data.get('username'),
                    email=user_data.get('email', f"{username}@example.com"),
                    role=user_data.get('role', 'user')
                )
        elif user_data.get('password') == password:
            # Legacy plain text password support (not recommended)
            return User(
                id=user_data.get('id', 1),
                username=user_data.get('username'),
                email=user_data.get('email', f"{username}@example.com"),
                role=user_data.get('role', 'user')
            )
    
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    error = None
    
    if form.validate_on_submit():
        try:
            # Get admin credentials from environment
            admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
            
            # Simplified direct authentication
            if form.username.data == admin_username and form.password.data == admin_password:
                # Create user object
                user = User(
                    id=1,
                    username=admin_username,
                    email='admin@example.com',
                    role='admin'
                )
                
                # Login the user
                login_user(user, remember=form.remember.data)
                session['logged_in'] = True
                session['username'] = user.username
                
                # Redirect to next page or home
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.index'))
            else:
                error = 'Invalid username or password'
                flash('Invalid username or password', 'danger')
        except Exception as e:
            logger.exception(f"Login error: {str(e)}")
            error = 'Service unavailable. Please try again later.'
            flash('Service unavailable. Please try again later.', 'danger')
    
    return render_template('login.html', form=form, error=error)

@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    logout_user()
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))