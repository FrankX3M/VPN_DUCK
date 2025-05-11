import os
import logging
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect

# Import configuration
from config import Config

# Import blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.servers import servers_bp
from routes.geolocations import geolocations_bp
from routes.api import api_bp

# Import models and user loader
from models import User

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    # Initialize Flask-application
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.from_object(config_class)

    # Initialize extensions
    csrf = CSRFProtect(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(servers_bp, url_prefix='/servers')
    app.register_blueprint(geolocations_bp, url_prefix='/geolocations')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Ensure static directories exist
    for static_dir in ['css', 'js', 'img']:
        os.makedirs(os.path.join('static', static_dir), exist_ok=True)

    # Create error templates and favicon
    from utils.template_utils import create_error_templates, create_favicon
    create_error_templates()
    create_favicon()

    # Custom static file handling to prevent sendfile issues
    # @app.route('/static/<path:filename>')
    # def custom_static(filename):
    #     try:
    #         cache_timeout = app.get_send_file_max_age(filename)
    #         from flask import send_from_directory
    #         return send_from_directory('static', filename, cache_timeout=cache_timeout)
    #     except Exception as e:
    #         logger.warning(f"Static file not found: {filename}, Error: {str(e)}")
    #         return '', 404
    @app.route('/static/<path:filename>')
    def custom_static(filename):
        try:
            cache_timeout = app.get_send_file_max_age(filename)
            from flask import send_from_directory
            
            # Check if file exists and has content
            filepath = os.path.join(app.root_path, 'static', filename)
            if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
                logger.warning(f"Static file is empty: {filename}")
                # Return a simple response for empty files instead of using send_file
                return '', 204  # No Content status code
            
            return send_from_directory('static', filename, cache_timeout=cache_timeout)
        except Exception as e:
            logger.warning(f"Static file not found: {filename}, Error: {str(e)}")
            return '', 404
            
    # Add favicon handler to prevent 404 errors
    @app.route('/favicon.ico')
    def favicon():
        try:
            from flask import send_from_directory
            return send_from_directory(os.path.join('static', 'img'), 'favicon.ico',
                                    mimetype='image/vnd.microsoft.icon')
        except:
            logger.warning("Favicon.ico not found")
            return '', 404

    # Handler for source map files
    @app.route('/static/<path:filename>.map')
    def serve_sourcemap(filename):
        try:
            from flask import send_from_directory
            path_parts = filename.split('/')
            if len(path_parts) > 1:
                # If path contains subdirectories
                basedir = os.path.join('static', *path_parts[:-1])
                basename = path_parts[-1] + '.map'
                return send_from_directory(basedir, basename)
            else:
                # If file is directly in static
                return send_from_directory('static', filename + '.map')
        except:
            return '', 404

    # Custom error handlers with fallbacks
    @app.errorhandler(404)
    def page_not_found(e):
        try:
            from flask import render_template
            return render_template('errors/404.html', now=datetime.now()), 404
        except Exception as error:
            logger.error(f"Error rendering 404 template: {str(error)}")
            error_html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>404 - Page Not Found</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                    h1 { color: #333; }
                    .error-container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .back-link { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
                    .back-link:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>404 - Page Not Found</h1>
                    <p>The page you are looking for does not exist or has been moved.</p>
                    <a href="/" class="back-link">Return to Home</a>
                </div>
            </body>
            </html>
            '''
            return error_html, 404

    @app.errorhandler(500)
    def server_error(e):
        try:
            from flask import render_template
            return render_template('errors/500.html', now=datetime.now()), 500
        except Exception as error:
            logger.error(f"Error rendering 500 template: {str(error)}")
            error_html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>500 - Server Error</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
                    h1 { color: #333; }
                    .error-container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .back-link { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
                    .back-link:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>500 - Server Error</h1>
                    <p>Sorry, something went wrong on our end. Please try again later.</p>
                    <a href="/" class="back-link">Return to Home</a>
                </div>
            </body>
            </html>
            '''
            return error_html, 500

    # # User loader for login manager
    # @login_manager.user_loader
    # def load_user(user_id):
    #     from utils.db_client import DatabaseClient
    #     from config import USE_MOCK_DATA, MOCK_USERS
        
    #     try:
    #         if USE_MOCK_DATA:
    #             # Find user in mock data
    #             for user in MOCK_USERS:
    #                 if str(user.get('id')) == str(user_id):
    #                     return User(
    #                         id=user.get('id'),
    #                         username=user.get('username'),
    #                         email=user.get('email'),
    #                         role=user.get('role', 'user')
    #                     )
    #         else:
    #             db_client = DatabaseClient(
    #                 base_url=app.config['API_BASE_URL'],
    #                 api_key=app.config['API_KEY']
    #             )
    #             response = db_client.get(f'/api/users/{user_id}')
    #             if response and response.status_code == 200:
    #                 user_data = response.json()
    #                 return User(
    #                     id=user_data.get('id'),
    #                     username=user_data.get('username'),
    #                     email=user_data.get('email'),
    #                     role=user_data.get('role', 'user')
    #                 )
    #     except Exception as e:
    #         logger.exception(f"Error loading user: {str(e)}")
        
    #     return None

    # # Health check endpoint for container orchestration

    @login_manager.user_loader
    def load_user(user_id):
        """Simplified user loader that only loads the admin user."""
        try:
            # Only load user with ID 1 (admin)
            if str(user_id) == '1':
                return User(
                    id=1,
                    username=os.environ.get('ADMIN_USERNAME', 'admin'),
                    email='admin@example.com',
                    role='admin'
                )
        except Exception as e:
            logger.exception(f"Error loading user: {str(e)}")
        
        return None

    @app.route('/health')
    def health_check():
        from flask import jsonify
        return jsonify({"status": "ok", "version": "1.0.0"}), 200

    return app

# Create app instance
app = create_app()


@app.template_filter('datetime')
def datetime_filter(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
    return value.strftime(format)

# Run application
if __name__ == '__main__':
    # Set debug mode
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Run the app
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)