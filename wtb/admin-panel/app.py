import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

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

    # Настройка кэширования статических файлов
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 43200  # 12 часов по умолчанию
    
    # Конфигурация типов файлов и их времени кэширования
    app.config['STATIC_CACHE_CONFIG'] = {
        'css': 86400,     # CSS файлы - 1 день
        'js': 86400,      # JS файлы - 1 день
        'images': 604800, # Изображения - 7 дней
        'fonts': 2592000, # Шрифты - 30 дней 
        'favicon': 2592000, # Favicon - 30 дней
        'maps': 3600      # Source maps - 1 час
    }

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

    @app.route('/static/<path:filename>')
    def custom_static(filename):
        try:
            from flask import send_from_directory, current_app
            
            # Определите максимальное время кэширования в зависимости от типа файла
            cache_config = current_app.config.get('STATIC_CACHE_CONFIG', {})
            
            # Определяем категорию файла и соответствующее время кэширования
            if filename.endswith(('.css')):
                cache_timeout = cache_config.get('css', 86400)  # CSS файлы
            elif filename.endswith(('.js')):
                cache_timeout = cache_config.get('js', 86400)  # JS файлы
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp')):
                cache_timeout = cache_config.get('images', 604800)  # Изображения
            elif filename.endswith(('.woff', '.woff2', '.ttf', '.eot', '.otf')):
                cache_timeout = cache_config.get('fonts', 2592000)  # Шрифты
            elif filename.endswith('.ico'):
                cache_timeout = cache_config.get('favicon', 2592000)  # Favicon
            else:
                # Для остальных файлов используем стандартные настройки приложения
                cache_timeout = current_app.config.get('SEND_FILE_MAX_AGE_DEFAULT', 43200)
            
            # Проверка существования файла и директорий
            filepath = os.path.join(current_app.root_path, 'static', filename)
            dirpath = os.path.dirname(filepath)
            
            # Проверяем, существует ли директория, и создаем её при необходимости
            if not os.path.exists(dirpath):
                os.makedirs(dirpath, exist_ok=True)
                logger.info(f"Created directory for static file: {dirpath}")
            
            # Проверяем, существует ли файл и имеет ли он содержимое
            if not os.path.exists(filepath):
                logger.warning(f"Static file not found: {filename}")
                # Для критичных файлов можно создать пустые заглушки
                if filename.endswith('.css'):
                    with open(filepath, 'w') as f:
                        f.write('/* Placeholder CSS file */\n')
                    logger.info(f"Created placeholder CSS file: {filename}")
                elif filename.endswith('.js'):
                    with open(filepath, 'w') as f:
                        f.write('// Placeholder JS file\n')
                    logger.info(f"Created placeholder JS file: {filename}")
                else:
                    return '', 404
            elif os.path.getsize(filepath) == 0:
                logger.warning(f"Static file is empty: {filename}")
                # Обеспечить, чтобы файл не был пустым
                if filename.endswith('.css'):
                    with open(filepath, 'w') as f:
                        f.write('/* Placeholder CSS file */\n')
                elif filename.endswith('.js'):
                    with open(filepath, 'w') as f:
                        f.write('// Placeholder JS file\n')
            
            # Отправляем файл клиенту с правильными заголовками кэширования
            return send_from_directory('static', filename, cache_timeout=cache_timeout)
        except Exception as e:
            logger.exception(f"Error serving static file {filename}: {str(e)}")
            return '', 404
            
    # Handler for source map files
    @app.route('/static/<path:filename>.map')
    def serve_sourcemap(filename):
        try:
            from flask import send_from_directory, current_app
            
            # Получаем время кэширования из конфигурации
            cache_config = current_app.config.get('STATIC_CACHE_CONFIG', {})
            cache_timeout = cache_config.get('maps', 3600)  # Source maps - 1 час по умолчанию
            
            # Проверка существования файла
            path_parts = filename.split('/')
            if len(path_parts) > 1:
                # Если путь содержит подкаталоги
                basedir = os.path.join(current_app.root_path, 'static', *path_parts[:-1])
                basename = path_parts[-1] + '.map'
                filepath = os.path.join(basedir, basename)
                
                # Убедимся, что каталог существует
                if not os.path.exists(basedir):
                    os.makedirs(basedir, exist_ok=True)
                    logger.info(f"Created directory for source map file: {basedir}")
                
                # Проверим существование файла
                if not os.path.exists(filepath):
                    logger.warning(f"Source map file not found: {filename}.map")
                    return '', 404
                
                return send_from_directory(basedir, basename, cache_timeout=cache_timeout)
            else:
                # Если файл находится непосредственно в статической директории
                filepath = os.path.join(current_app.root_path, 'static', filename + '.map')
                
                # Проверим существование файла
                if not os.path.exists(filepath):
                    logger.warning(f"Source map file not found: {filename}.map")
                    return '', 404
                
                return send_from_directory('static', filename + '.map', cache_timeout=cache_timeout)
        except Exception as e:
            logger.exception(f"Error serving source map file {filename}.map: {str(e)}")
            return '', 404

    # Add favicon handler to prevent 404 errors
    @app.route('/favicon.ico')
    def favicon():
        try:
            from flask import send_from_directory, current_app
            
            # Получаем время кэширования из конфигурации
            cache_config = current_app.config.get('STATIC_CACHE_CONFIG', {})
            cache_timeout = cache_config.get('favicon', 2592000)  # 30 дней по умолчанию
            
            # Путь к файлу favicon.ico
            favicon_dir = os.path.join(current_app.root_path, 'static', 'img')
            favicon_path = os.path.join(favicon_dir, 'favicon.ico')
            
            # Проверяем существование директории и создаем при необходимости
            if not os.path.exists(favicon_dir):
                os.makedirs(favicon_dir, exist_ok=True)
                logger.info(f"Created directory for favicon: {favicon_dir}")
            
            # Проверяем существование файла или создаем стандартный
            if not os.path.exists(favicon_path) or os.path.getsize(favicon_path) == 0:
                # Если файл не существует или пуст, создаем базовый favicon
                from utils.template_utils import create_favicon
                create_favicon()
                logger.info("Created default favicon.ico")
            
            # Отправляем файл с кэшированием
            return send_from_directory(os.path.join('static', 'img'), 'favicon.ico',
                                    mimetype='image/vnd.microsoft.icon',
                                    cache_timeout=cache_timeout)
        except Exception as e:
            logger.exception(f"Error serving favicon.ico: {str(e)}")
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

    # Добавляем контекстный процессор для всех шаблонов
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

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
    # Проверяем, имеет ли value метод strftime
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    else:
        # Если value не имеет метода strftime, вернем значение как есть
        return value

# Run application
if __name__ == '__main__':
    # Set debug mode
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Run the app
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)