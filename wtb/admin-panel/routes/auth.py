import os
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, current_user

from forms import LoginForm
from models import User
from config import USE_MOCK_DATA

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    error = None
    
    if form.validate_on_submit():
        try:
            # Use mock data in development mode
            if USE_MOCK_DATA:
                from utils.mock_data import authenticate_user
                user_data = authenticate_user(form.username.data, form.password.data)
                if user_data:
                    user = User(
                        id=user_data.get('id'),
                        username=user_data.get('username'),
                        email=user_data.get('email'),
                        role=user_data.get('role', 'user')
                    )
                    login_user(user, remember=form.remember.data)
                    session['logged_in'] = True
                    session['username'] = user.username
                    
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.index'))
                else:
                    error = 'Invalid username or password'
                    flash('Invalid username or password', 'danger')
            else:
                # For development/testing environment, allow a hardcoded admin account
                # In production, this should be removed and authenticate against a proper backend
                if os.environ.get('FLASK_ENV', 'production') != 'production' and \
                   form.username.data == 'admin' and form.password.data == 'admin':
                    user = User(
                        id=1,
                        username='admin',
                        email='admin@example.com',
                        role='admin'
                    )
                    login_user(user, remember=form.remember.data)
                    session['logged_in'] = True
                    session['username'] = user.username
                    
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.index'))
                
                # Normal authentication with API
                try:
                    from utils.db_client import DatabaseClient
                    from flask import current_app

                    db_client = DatabaseClient(
                        base_url=current_app.config['API_BASE_URL'],
                        api_key=current_app.config['API_KEY']
                    )
                    
                    response = db_client.post('/api/auth/login', json={
                        'username': form.username.data,
                        'password': form.password.data
                    })
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        user = User(
                            id=user_data.get('id'),
                            username=user_data.get('username'),
                            email=user_data.get('email'),
                            role=user_data.get('role', 'user')
                        )
                        login_user(user, remember=form.remember.data)
                        session['logged_in'] = True
                        session['username'] = user.username
                        
                        # Redirect to the page they were trying to access or home
                        next_page = request.args.get('next')
                        return redirect(next_page or url_for('main.index'))
                    else:
                        error = 'Invalid username or password'
                        flash('Invalid username or password', 'danger')
                except Exception as e:
                    logger.exception(f"API communication error: {str(e)}")
                    error = 'Service unavailable. Please try again later.'
                    flash('Service unavailable. Please try again later.', 'danger')
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