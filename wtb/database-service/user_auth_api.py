import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
users_api = Blueprint('users_api', __name__)

# Path to users file
USERS_FILE = os.environ.get('USERS_FILE', '/app/data/users.json')

def get_users():
    """Get users from JSON file or create default if not exists."""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default admin user if file doesn't exist
            default_users = {
                "1": {
                    "id": 1,
                    "username": os.environ.get('ADMIN_USERNAME', 'admin'),
                    "password_hash": generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin')),
                    "email": "admin@example.com",
                    "role": "admin"
                }
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
            
            # Write default users to file
            with open(USERS_FILE, 'w') as f:
                json.dump(default_users, f, indent=2)
                
            return default_users
    except Exception as e:
        logger.exception(f"Error getting users: {str(e)}")
        return {}

def save_users(users):
    """Save users to JSON file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        
        # Write users to file
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
            
        return True
    except Exception as e:
        logger.exception(f"Error saving users: {str(e)}")
        return False

def authenticate_user(username, password):
    """Authenticate user with username and password."""
    users = get_users()
    
    # Find user by username
    user_id = None
    user_data = None
    
    for uid, user in users.items():
        if user.get('username') == username:
            user_id = uid
            user_data = user
            break
    
    if user_data:
        # Check password
        if 'password_hash' in user_data and check_password_hash(user_data['password_hash'], password):
            # Create response without password hash
            response_data = {k: v for k, v in user_data.items() if k != 'password_hash'}
            response_data['id'] = user_id
            return response_data
    
    return None

def require_auth(f):
    """Decorator to require API key authentication."""
    def decorated(*args, **kwargs):
        # Get API key from request
        api_key = request.headers.get('Authorization')
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key[7:]  # Remove 'Bearer ' prefix
        
        # Check API key against environment variable
        expected_key = os.environ.get('ADMIN_SECRET_KEY')
        
        if not api_key or api_key != expected_key:
            return jsonify({"error": "Unauthorized - Invalid API key"}), 401
        
        return f(*args, **kwargs)
    
    return decorated

@users_api.route('/api/users/authenticate', methods=['POST'])
@require_auth
def api_authenticate():
    """Authenticate user API endpoint."""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Missing username or password"}), 400
        
        user = authenticate_user(data['username'], data['password'])
        
        if user:
            return jsonify(user), 200
        else:
            return jsonify({"error": "Invalid username or password"}), 401
    except Exception as e:
        logger.exception(f"Error in authentication: {str(e)}")
        return jsonify({"error": "Authentication error"}), 500

@users_api.route('/api/users', methods=['GET'])
@require_auth
def get_all_users():
    """Get all users API endpoint."""
    try:
        users = get_users()
        
        # Remove password hashes from response
        response_data = {}
        for user_id, user in users.items():
            user_copy = {k: v for k, v in user.items() if k != 'password_hash'}
            user_copy['id'] = user_id
            response_data[user_id] = user_copy
        
        return jsonify({"users": response_data}), 200
    except Exception as e:
        logger.exception(f"Error getting all users: {str(e)}")
        return jsonify({"error": "Failed to get users"}), 500

@users_api.route('/api/users/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """Get user by ID API endpoint."""
    try:
        users = get_users()
        
        if user_id in users:
            user = users[user_id]
            
            # Remove password hash from response
            response_data = {k: v for k, v in user.items() if k != 'password_hash'}
            response_data['id'] = user_id
            
            return jsonify(response_data), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        logger.exception(f"Error getting user: {str(e)}")
        return jsonify({"error": "Failed to get user"}), 500

@users_api.route('/api/users', methods=['POST'])
@require_auth
def create_user():
    """Create new user API endpoint."""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Get existing users
        users = get_users()
        
        # Check if username already exists
        for _, user in users.items():
            if user.get('username') == data['username']:
                return jsonify({"error": "Username already exists"}), 409
        
        # Generate new user ID
        user_id = str(len(users) + 1)
        while user_id in users:
            user_id = str(int(user_id) + 1)
        
        # Create new user
        new_user = {
            "username": data['username'],
            "password_hash": generate_password_hash(data['password']),
            "email": data.get('email', f"{data['username']}@example.com"),
            "role": data.get('role', 'user')
        }
        
        # Add user to collection
        users[user_id] = new_user
        
        # Save users
        if save_users(users):
            # Return created user without password hash
            response_data = {k: v for k, v in new_user.items() if k != 'password_hash'}
            response_data['id'] = user_id
            
            return jsonify(response_data), 201
        else:
            return jsonify({"error": "Failed to save user"}), 500
    except Exception as e:
        logger.exception(f"Error creating user: {str(e)}")
        return jsonify({"error": "Failed to create user"}), 500

@users_api.route('/api/users/<user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """Update user API endpoint."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get existing users
        users = get_users()
        
        if user_id not in users:
            return jsonify({"error": "User not found"}), 404
        
        # Update user data
        user = users[user_id]
        
        # Update fields
        if 'username' in data:
            # Check if new username already exists for another user
            for uid, u in users.items():
                if uid != user_id and u.get('username') == data['username']:
                    return jsonify({"error": "Username already exists"}), 409
            
            user['username'] = data['username']
        
        if 'password' in data:
            user['password_hash'] = generate_password_hash(data['password'])
        
        if 'email' in data:
            user['email'] = data['email']
        
        if 'role' in data:
            user['role'] = data['role']
        
        # Save users
        if save_users(users):
            # Return updated user without password hash
            response_data = {k: v for k, v in user.items() if k != 'password_hash'}
            response_data['id'] = user_id
            
            return jsonify(response_data), 200
        else:
            return jsonify({"error": "Failed to save user"}), 500
    except Exception as e:
        logger.exception(f"Error updating user: {str(e)}")
        return jsonify({"error": "Failed to update user"}), 500

@users_api.route('/api/users/<user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id):
    """Delete user API endpoint."""
    try:
        # Get existing users
        users = get_users()
        
        if user_id not in users:
            return jsonify({"error": "User not found"}), 404
        
        # Don't allow deleting the last admin user
        if users[user_id].get('role') == 'admin':
            admin_count = sum(1 for u in users.values() if u.get('role') == 'admin')
            if admin_count <= 1:
                return jsonify({"error": "Cannot delete the last admin user"}), 403
        
        # Delete user
        del users[user_id]
        
        # Save users
        if save_users(users):
            return jsonify({"message": "User deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to save users"}), 500
    except Exception as e:
        logger.exception(f"Error deleting user: {str(e)}")
        return jsonify({"error": "Failed to delete user"}), 500

# Register blueprint in your app
# In your main app file (db_manager.py), add:
# from user_auth_api import users_api
# app.register_blueprint(users_api)