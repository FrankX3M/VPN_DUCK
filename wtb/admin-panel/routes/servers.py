import os
import logging
import secrets
import requests
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required

from forms import ServerForm, FilterForm
from utils.chart_generator import ChartGenerator
from config import USE_MOCK_DATA
from config import DATABASE_SERVICE_URL

logger = logging.getLogger(__name__)

# Create blueprint
servers_bp = Blueprint('servers', __name__)

@servers_bp.route('/')
@login_required
def index():
    """Display list of servers with filtering options."""
    # Initialize filter form
    filter_form = FilterForm()
    
    # Get query parameters for filtering
    search = request.args.get('search', '')
    geolocation = request.args.get('geolocation', 'all')
    status = request.args.get('status', 'all')
    view_mode = request.args.get('view', 'table')
    
    if USE_MOCK_DATA:
        # Use mock data for development
        from utils.mock_data import MOCK_GEOLOCATIONS, filter_servers
        geolocations = MOCK_GEOLOCATIONS
        
        # Update filter form choices
        filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
            (str(geo['id']), geo['name']) for geo in geolocations if isinstance(geo, dict)
        ]
        
        # Prepare filter params
        filters = {}
        if search:
            filters['search'] = search
        if geolocation != 'all':
            try:
                filters['geolocation_id'] = int(geolocation)
            except (ValueError, TypeError):
                pass
        if status != 'all':
            filters['status'] = status
            
        # Filter servers
        servers = filter_servers(filters)
    else:
        # Load geolocations for the filter dropdown from API
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            geo_response = db_client.get('/api/geolocations')
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                # Проверяем формат данных
                if isinstance(geo_data, dict) and 'geolocations' in geo_data:
                    geolocations = geo_data['geolocations']
                elif isinstance(geo_data, list):
                    geolocations = geo_data
                else:
                    logger.warning(f"Неожиданный формат данных от API (geolocations): {geo_data}")
                    geolocations = []
                    
                # Обновляем список выбора после проверки данных
                filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
                    (str(geo['id']), geo['name']) for geo in geolocations 
                    if isinstance(geo, dict) and 'id' in geo and 'name' in geo
                ]
            else:
                filter_form.geolocation.choices = [('all', 'All Geolocations')]
                flash('Failed to load geolocation filter options', 'warning')
        except Exception as e:
            logger.exception(f"Error loading geolocations: {str(e)}")
            filter_form.geolocation.choices = [('all', 'All Geolocations')]
        
        # Prepare filter params for API request
        filter_params = {}
        if search:
            filter_params['search'] = search
        if geolocation != 'all':
            filter_params['geolocation_id'] = geolocation
        if status != 'all':
            filter_params['status'] = status

        # Fetch servers from API
        try:
            response = db_client.get('/api/servers', params=filter_params)
            if response.status_code == 200:
                data = response.json()
                # Проверяем формат данных
                if isinstance(data, dict) and 'servers' in data:
                    servers = data['servers']
                elif isinstance(data, list):
                    servers = data
                else:
                    logger.warning(f"Неожиданный формат данных от API (servers): {data}")
                    servers = []
                    flash('Unexpected data format from API (servers)', 'warning')
            else:
                servers = []
                flash('Failed to fetch server list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching servers: {str(e)}")
            servers = []
            flash('Service unavailable', 'danger')

    # Calculate server stats
    stats = {
        'total': len(servers),
        'active': sum(1 for s in servers if isinstance(s, dict) and s.get('status') == 'active'),
        'inactive': sum(1 for s in servers if isinstance(s, dict) and s.get('status') == 'inactive'),
        'degraded': sum(1 for s in servers if isinstance(s, dict) and s.get('status') == 'degraded')
    }
    
    return render_template(
        'servers/index.html',
        servers=servers,
        filter_form=filter_form,
        view_mode=view_mode,
        stats=stats,
        now=datetime.now()
    )

@servers_bp.route('/<int:server_id>', methods=['GET'])
@login_required
def details(server_id):
    """Show detailed information about a server."""
    if USE_MOCK_DATA:
        # Use mock data for development
        from utils.mock_data import find_server, generate_mock_metrics
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers.index'))
            
        # Generate mock metrics
        metrics = generate_mock_metrics(server_id)
        
        # Generate charts
        charts = {}
        if metrics and isinstance(metrics, dict) and 'history' in metrics and metrics['history']:
            chart_generator = ChartGenerator()
            charts['latency'] = chart_generator.generate_metrics_image(metrics, 'latency')
            charts['packet_loss'] = chart_generator.generate_metrics_image(metrics, 'packet_loss')
            charts['resources'] = chart_generator.generate_metrics_image(metrics, 'resources')
            
            # Generate interactive chart if plotly is available
            interactive_chart = chart_generator.generate_plotly_chart(metrics, 'server_detail')
        else:
            interactive_chart = None
            
        # Find geolocation information
        from utils.mock_data import find_geolocation
        geo_id = server.get('geolocation_id') if isinstance(server, dict) else None
        geo = find_geolocation(geo_id) or {'name': 'Unknown', 'code': 'N/A'}
        
        # Convert server dictionary to Server object if needed
        from models import Server
        if isinstance(server, dict):
            server_obj = Server.from_dict(server)
        else:
            server_obj = server
            
    else:
        # Get server information from API
        try:
            # Using db_client for API access
            from utils.db_client import DatabaseClient
            
            db_client = DatabaseClient(
                base_url=current_app.config['API_BASE_URL'],
                api_key=current_app.config['API_KEY']
            )
            
            # Get server details
            logger.info(f"Получение информации о сервере {server_id}")
            server_response = db_client.get(f'/api/servers/{server_id}')
            
            if server_response.status_code != 200:
                logger.error(f"Ошибка получения данных сервера: {server_response.status_code}, {server_response.text}")
                flash(f"Error retrieving server information", "danger")
                return redirect(url_for('servers.index'))
                
            # Try to parse response
            try:
                server_data = server_response.json()
                logger.info(f"Получены данные сервера: {server_data}")
            except ValueError as e:
                logger.error(f"Ошибка JSON: {e}, содержимое ответа: {server_response.text}")
                flash("Invalid JSON response from API", "danger")
                return redirect(url_for('servers.index'))
                
            # Extract server data if it's wrapped in another object
            if isinstance(server_data, dict) and 'server' in server_data:
                server_data = server_data['server']
                
            # Convert dictionary to Server object
            from models import Server
            try:
                server_obj = Server.from_dict(server_data)
                logger.info(f"Сервер преобразован в объект: {server_obj}")
            except Exception as e:
                logger.error(f"Ошибка преобразования в объект Server: {e}")
                # Fallback to using the dictionary directly
                server_obj = server_data
                logger.warning(f"Используем словарь напрямую: {server_data}")
                
            # Get geolocation information
            geo_id = server_data.get('geolocation_id')
            geo = None
            if geo_id:
                geo_response = db_client.get(f'/api/geolocations/{geo_id}')
                if geo_response.status_code == 200:
                    geo = geo_response.json()
                    if not isinstance(geo, dict):
                        logger.warning(f"Неверный формат данных геолокации: {geo}")
                        geo = {'name': 'Unknown', 'code': 'N/A'}
                else:
                    geo = {'name': 'Unknown', 'code': 'N/A'}
            else:
                geo = {'name': 'Unknown', 'code': 'N/A'}
            
            # Get metrics if available
            try:
                hours = request.args.get('hours', 24, type=int)
                metrics_response = db_client.get(f'/api/servers/{server_id}/metrics', 
                                              params={'hours': hours})
                
                if metrics_response.status_code == 200:
                    metrics = metrics_response.json()
                else:
                    logger.warning(f"Ошибка получения метрик: {metrics_response.status_code}, {metrics_response.text}")
                    metrics = {'current': {}, 'history': []}
            except Exception as e:
                logger.warning(f"Failed to retrieve metrics for server {server_id}: {str(e)}")
                metrics = {'current': {}, 'history': []}
            
            # Generate charts
            charts = {}
            if metrics and isinstance(metrics, dict) and 'history' in metrics and metrics['history']:
                chart_generator = ChartGenerator()
                charts['latency'] = chart_generator.generate_metrics_image(metrics, 'latency')
                charts['packet_loss'] = chart_generator.generate_metrics_image(metrics, 'packet_loss')
                charts['resources'] = chart_generator.generate_metrics_image(metrics, 'resources')
                
                # Generate interactive chart if plotly is available
                interactive_chart = chart_generator.generate_plotly_chart(metrics, 'server_detail')
            else:
                interactive_chart = None
                
        except Exception as e:
            logger.exception(f"Error showing server details: {str(e)}")
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for('servers.index'))
    
    # Handle server_obj for template - ensure it has proper attributes
    if isinstance(server_obj, dict):
        # Для случая, когда сервер остался словарём
        logger.warning("Сервер является словарём. Модифицируем шаблонную логику.")
        # Переносим простейшее решение прямо в функцию представления
        server_dict = server_obj
        class ServerWrapper:
            """Простой класс-обёртка для преобразования словаря в объект с атрибутами"""
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
                    
        server = ServerWrapper(server_dict)
    else:
        # Если это уже объект Server или другой класс с атрибутами
        server = server_obj
    
    # Render template with all data
    return render_template(
        'servers/details.html',
        server=server,
        geo=geo,
        metrics=metrics,
        charts=charts,
        interactive_chart=interactive_chart,
        hours=request.args.get('hours', 24, type=int),
        now=datetime.now()
    )

@servers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Добавление нового сервера в систему."""
    form = ServerForm()

    # Заполнение выпадающего списка геолокаций
    try:
        # Получение списка геолокаций из базы данных
        response = requests.get(f"{DATABASE_SERVICE_URL}/api/geolocations", timeout=5)
        if response.status_code == 200:
            geolocations = response.json().get('geolocations', [])
            form.geolocation_id.choices = [
                (int(geo['id']), geo['name']) for geo in geolocations if geo.get('available', True)
            ]
        else:
            flash('Не удалось загрузить список геолокаций', 'danger')
            form.geolocation_id.choices = []
    except Exception as e:
        logger.exception(f"Ошибка при загрузке геолокаций: {e}")
        flash(f'Ошибка: {str(e)}', 'danger')
        form.geolocation_id.choices = []

    if form.validate_on_submit():
        try:
            endpoint = form.endpoint.data
            port = form.port.data
            api_url = form.api_url.data or f"http://{endpoint}:5000"
            api_path = form.api_path.data or '/status'
            skip_api_check = form.skip_api_check.data

            # Проверка доступности сервера, если не нужно пропускать проверку API
            if not skip_api_check:
                try:
                    # Формируем URL для проверки (используем статус API)
                    check_url = f"{api_url}{api_path}"
                    logger.info(f"Проверка доступности сервера: {check_url}")
                    
                    api_key = form.api_key.data
                    headers = {}
                    if api_key:
                        headers['X-API-Key'] = api_key
                    
                    # Делаем запрос на сервер для проверки доступности
                    check_response = requests.get(check_url, timeout=5, headers=headers)
                    
                    if check_response.status_code != 200:
                        flash(f'Сервер недоступен. Код ответа: {check_response.status_code}', 'warning')
                        return render_template('servers/add.html', form=form, title='Добавление сервера')
                    
                    logger.info(f"Сервер доступен: {check_response.status_code}")
                except requests.RequestException as e:
                    logger.error(f"Ошибка при проверке доступности сервера: {e}")
                    flash(f'Не удалось подключиться к серверу: {str(e)}', 'warning')
                    return render_template('servers/add.html', form=form, title='Добавление сервера')

            # Генерация уникального server_id
            import uuid
            import secrets
            server_id = f"srv-{uuid.uuid4().hex[:8]}"
            
            # Подготовка данных сервера для отправки в API
            server_data = {
                'server_id': server_id,
                'name': form.name.data,
                'endpoint': form.endpoint.data,
                'port': form.port.data,
                'address': form.address.data,
                'public_key': form.public_key.data,
                'geolocation_id': form.geolocation_id.data,
                'max_peers': form.max_peers.data,
                'status': form.status.data,
                'api_key': form.api_key.data or secrets.token_hex(16),
                'api_url': api_url,
                'api_path': api_path,
                'skip_api_check': skip_api_check
            }
            
            # Отправка данных в API для добавления сервера
            logger.info(f"Отправка данных для добавления сервера: {server_data}")
            response = requests.post(
                f"{DATABASE_SERVICE_URL}/api/servers/add", 
                json=server_data,
                timeout=10
            )
            
            if response.status_code != 200:
                error_message = f"Ошибка при добавлении сервера: {response.text}"
                logger.error(error_message)
                flash(error_message, 'danger')
                return render_template('servers/add.html', form=form, title='Добавление сервера')
            
            # Получение результата
            result = response.json()
            logger.info(f"Сервер успешно добавлен: {result}")
            
            # Обновление кэша серверов (если используется)
            try:
                from flask import current_app
                if hasattr(current_app, 'cache') and current_app.cache:
                    current_app.cache.delete('servers_list')
            except Exception as e:
                logger.warning(f"Не удалось обновить кэш серверов: {e}")
            
            # Перенаправление на страницу со списком серверов
            flash('Сервер успешно добавлен', 'success')
            return redirect(url_for('servers.index'))
            
        except Exception as e:
            error_message = f"Ошибка при добавлении сервера: {str(e)}"
            logger.exception(error_message)
            flash(error_message, 'danger')
    
    # Если GET запрос или валидация не прошла
    return render_template('servers/add.html', form=form, title='Добавление сервера')

# Обновление функции редактирования сервера

@servers_bp.route('/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(server_id):
    """Редактирование информации о сервере."""
    # Получаем сервер для редактирования
    if USE_MOCK_DATA:
        from utils.mock_data import find_server, MOCK_SERVERS, MOCK_GEOLOCATIONS
        server_data = find_server(server_id)
        if not server_data:
            flash('Сервер не найден', 'danger')
            return redirect(url_for('servers.index'))
            
        # Проверяем, является ли server_data словарем или объектом
        if isinstance(server_data, dict):
            from models import Server
            try:
                server = Server.from_dict(server_data)
                logger.info(f"Мок-сервер преобразован в объект: {server}")
            except Exception as e:
                logger.error(f"Ошибка преобразования мок-сервера в объект: {e}")
                # Создаем простую обертку объекта
                class ServerWrapper:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                server = ServerWrapper(server_data)
        else:
            server = server_data
            
        form = ServerForm()
        if not form.is_submitted():
            # Заполняем форму данными сервера только если она не была отправлена
            form = ServerForm(obj=server)
            
        try:
            # Проверяем типы данных перед обработкой
            form.geolocation_id.choices = [
                (g['id'], g['name']) for g in MOCK_GEOLOCATIONS 
                if isinstance(g, dict) and 'id' in g and 'name' in g
            ]
        except Exception as e:
            logger.exception(f"Ошибка загрузки геолокаций для формы: {str(e)}")
            form.geolocation_id.choices = []
            flash('Ошибка загрузки опций геолокаций', 'danger')
        
        if form.validate_on_submit():
            try:
                # Обновляем данные сервера
                found = False
                for server_item in MOCK_SERVERS:
                    if isinstance(server_item, dict) and server_item.get('id') == server_id:
                        server_item.update({
                            'name': form.name.data,
                            'endpoint': form.endpoint.data,
                            'port': form.port.data,
                            'address': form.address.data,
                            'public_key': form.public_key.data,
                            'geolocation_id': form.geolocation_id.data,
                            'geolocation_name': next((g['name'] for g in MOCK_GEOLOCATIONS 
                                                    if isinstance(g, dict) and g.get('id') == form.geolocation_id.data), 
                                                    "Unknown"),
                            'max_peers': form.max_peers.data,
                            'status': form.status.data,
                            'api_key': form.api_key.data,
                            'api_url': form.api_url.data,
                            'api_path': form.api_path.data or '/status',
                            'skip_api_check': form.skip_api_check.data
                        })
                        found = True
                        break
                
                if not found:
                    logger.error(f"Сервер не найден при обновлении моковых данных. ID: {server_id}")
                    flash('Сервер не найден для обновления', 'danger')
                    return redirect(url_for('servers.index'))
                
                flash('Сервер успешно обновлен', 'success')
                return redirect(url_for('servers.details', server_id=server_id))
            except Exception as e:
                logger.exception(f"Ошибка обновления мок-сервера: {str(e)}")
                flash('Ошибка обновления сервера', 'danger')
    else:
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            # Получение данных сервера
            logger.info(f"Получение данных сервера {server_id} для редактирования")
            response = db_client.get(f'/api/servers/{server_id}')
            
            if response.status_code == 200:
                try:
                    server_data = response.json()
                    logger.info(f"Получены данные сервера: {server_data}")
                    
                    # Извлекаем данные сервера, если они обернуты
                    if isinstance(server_data, dict) and 'server' in server_data:
                        server_data = server_data['server']
                    
                    # Преобразуем словарь в объект Server
                    from models import Server
                    try:
                        server = Server.from_dict(server_data)
                        logger.info(f"Сервер преобразован в объект: {server}")
                    except Exception as e:
                        logger.error(f"Ошибка преобразования данных сервера в объект: {e}")
                        # Создаем простую обертку для словаря
                        class ServerWrapper:
                            def __init__(self, data):
                                for key, value in data.items():
                                    setattr(self, key, value)
                        server = ServerWrapper(server_data)
                        logger.info(f"Создана обертка для словаря: {server.__dict__}")
                except ValueError as e:
                    logger.error(f"Ошибка JSON: {e}, содержимое ответа: {response.text}")
                    flash("Неверный ответ JSON от API", "danger")
                    return redirect(url_for('servers.index'))
            else:
                logger.error(f"Ошибка получения данных сервера: {response.status_code}, {response.text}")
                flash('Сервер не найден', 'danger')
                return redirect(url_for('servers.index'))
        except Exception as e:
            logger.exception(f"Ошибка получения сервера: {str(e)}")
            flash('Сервис недоступен', 'danger')
            return redirect(url_for('servers.index'))
        
        form = ServerForm()
        if not form.is_submitted():
            # Заполняем форму данными сервера только если она не была отправлена
            form = ServerForm(obj=server)
        
        # Загрузка списка геолокаций
        try:
            geo_response = db_client.get('/api/geolocations')
            if geo_response.status_code == 200:
                data = geo_response.json()
                # Проверяем формат данных
                if isinstance(data, dict) and 'geolocations' in data:
                    geolocations = data['geolocations']
                elif isinstance(data, list):
                    geolocations = data
                else:
                    logger.warning(f"Неожиданный формат данных от API (geolocations): {data}")
                    geolocations = []
                    
                # Проверяем типы данных перед обработкой
                form.geolocation_id.choices = [
                    (g['id'], g['name']) for g in geolocations 
                    if isinstance(g, dict) and 'id' in g and 'name' in g
                ]
            else:
                flash('Не удалось загрузить опции геолокаций', 'warning')
                form.geolocation_id.choices = [(server.geolocation_id, 'Текущее местоположение')]
        except Exception as e:
            logger.exception(f"Ошибка загрузки геолокаций: {str(e)}")
            form.geolocation_id.choices = [(server.geolocation_id, 'Текущее местоположение')]
        
        if form.validate_on_submit():
            try:
                # Подготовка обновленных данных сервера
                server_data = {
                    'name': form.name.data,
                    'endpoint': form.endpoint.data,
                    'port': form.port.data,
                    'address': form.address.data,
                    'public_key': form.public_key.data,
                    'geolocation_id': form.geolocation_id.data,
                    'max_peers': form.max_peers.data,
                    'status': form.status.data,
                    'api_key': form.api_key.data,
                    'api_url': form.api_url.data,
                    'api_path': form.api_path.data or '/status',
                    'skip_api_check': form.skip_api_check.data
                }
                
                # Обновляем сервер через API
                response = db_client.put(f'/api/servers/{server_id}', json=server_data)
                
                if response.status_code == 200:
                    flash('Сервер успешно обновлен', 'success')
                    return redirect(url_for('servers.details', server_id=server_id))
                else:
                    logger.error(f"Ошибка обновления сервера: {response.status_code}, {response.text}")
                    flash('Не удалось обновить сервер', 'danger')
                    
            except Exception as e:
                logger.exception(f"Ошибка обновления сервера: {str(e)}")
                flash('Сервис недоступен', 'danger')
    
    return render_template('servers/edit.html', form=form, server=server, now=datetime.now())

@servers_bp.route('/<int:server_id>/delete')
@login_required
def delete(server_id):
    """Delete a server."""
    if USE_MOCK_DATA:
        # Import necessary modules
        from utils.mock_data import find_server
        
        # Find server in mock data
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers.index'))
        
        # Import and declare MOCK_SERVERS as global    
        global MOCK_SERVERS
        from utils.mock_data import MOCK_SERVERS
        
        # Remove server from mock data
        MOCK_SERVERS = [s for s in MOCK_SERVERS if not isinstance(s, dict) or s.get('id') != server_id]
        
        flash('Server deleted successfully', 'success')
    else:
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            response = db_client.delete(f'/api/servers/{server_id}')
            
            if response.status_code in [200, 204]:
                flash('Server deleted successfully', 'success')
            else:
                flash('Failed to delete server', 'danger')
                
        except Exception as e:
            logger.exception(f"Error deleting server: {str(e)}")
            flash('Service unavailable', 'danger')
    
    return redirect(url_for('servers.index'))

@servers_bp.route('/<int:server_id>/toggle_status')
@login_required
def toggle_status(server_id):
    """Изменить статус сервера (активный/неактивный)."""
    try:
        # Параметр статуса из запроса
        status = request.args.get('status')
        if not status or status not in ['active', 'inactive']:
            status = None  # Если статус не указан, будем просто переключать текущий
            
        logger.info(f"Запрос на переключение статуса сервера {server_id} в {status or 'противоположный'}")
        
        if USE_MOCK_DATA:
            from utils.mock_data import find_server, MOCK_SERVERS
            server = find_server(server_id)
            if not server:
                flash('Сервер не найден', 'danger')
                return redirect(url_for('servers.index'))
                
            # Переключение статуса в моковых данных
            found = False
            for s in MOCK_SERVERS:
                if isinstance(s, dict) and s.get('id') == server_id:
                    if status:
                        s['status'] = status
                    else:
                        # Переключение между active/inactive
                        s['status'] = 'inactive' if s.get('status') == 'active' else 'active'
                    new_status = s['status']
                    found = True
                    break
                    
            if not found:
                flash('Ошибка при изменении статуса сервера', 'danger')
                return redirect(url_for('servers.details', server_id=server_id))
                
            status_text = 'активирован' if new_status == 'active' else 'деактивирован'
            flash(f'Сервер успешно {status_text}', 'success')
        else:
            from utils.db_client import DatabaseClient
            
            db_client = DatabaseClient(
                base_url=current_app.config['API_BASE_URL'],
                api_key=current_app.config['API_KEY']
            )
            
            # Если статус не указан, получаем текущий и инвертируем его
            if not status:
                try:
                    server_response = db_client.get(f'/api/servers/{server_id}')
                    if server_response.status_code == 200:
                        server_data = server_response.json()
                        
                        # Проверка формата ответа
                        if isinstance(server_data, dict):
                            # Поддержка разных форматов ответа API
                            if 'server' in server_data:
                                server_data = server_data['server']
                            
                            # Определение текущего статуса
                            current_status = server_data.get('status')
                            if current_status is None:
                                # Проверим альтернативное поле is_active
                                is_active = server_data.get('is_active')
                                if is_active is not None:
                                    current_status = 'active' if is_active else 'inactive'
                                else:
                                    current_status = 'active'  # По умолчанию считаем активным
                            
                            # Инвертируем статус
                            status = 'inactive' if current_status == 'active' else 'active'
                        else:
                            logger.warning(f"Неожиданный формат данных от API: {server_data}")
                            status = 'active'  # Безопасное значение по умолчанию
                    else:
                        logger.error(f"Ошибка получения данных сервера: {server_response.status_code}")
                        flash('Не удалось получить информацию о сервере', 'danger')
                        return redirect(url_for('servers.details', server_id=server_id))
                except Exception as e:
                    logger.exception(f"Ошибка при получении данных сервера: {str(e)}")
                    flash('Сервис недоступен', 'danger')
                    return redirect(url_for('servers.details', server_id=server_id))
            
            # Обновляем статус через API
            logger.info(f"Изменение статуса сервера {server_id} на {status}")
            try:
                # Подготовка данных для обновления
                update_data = {'status': status}
                
                # Альтернативный формат для API, если оно принимает is_active вместо status
                if status in ['active', 'inactive']:
                    update_data['is_active'] = (status == 'active')
                
                # Отправка запроса
                response = db_client.put(f'/api/servers/{server_id}', json=update_data)
                
                if response.status_code == 200:
                    status_text = 'активирован' if status == 'active' else 'деактивирован'
                    flash(f'Сервер успешно {status_text}', 'success')
                else:
                    logger.error(f"Ошибка обновления статуса сервера: {response.status_code}, {response.text}")
                    flash('Не удалось обновить статус сервера', 'danger')
            except Exception as e:
                logger.exception(f"Ошибка при изменении статуса сервера: {str(e)}")
                flash('Сервис недоступен', 'danger')
                
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при изменении статуса сервера: {str(e)}")
        flash('Произошла ошибка', 'danger')
    
    return redirect(url_for('servers.details', server_id=server_id))

@servers_bp.route('/<int:server_id>/action/<action>', methods=['POST'])
@login_required
def action(server_id, action):
    """Выполнить действие с сервером (restart, toggle_status и т.д.)."""
    try:
        if action == 'toggle_status':
            # Получаем текущий статус сервера
            if USE_MOCK_DATA:
                from utils.mock_data import find_server, MOCK_SERVERS
                server = find_server(server_id)
            else:
                server = get_server(server_id)
                
            if not server:
                flash('Сервер не найден', 'danger')
                return redirect(url_for('servers.index'))
                
            # Переключаем статус
            current_status = server.get('status') if isinstance(server, dict) else server.status
            new_status = 'inactive' if current_status == 'active' else 'active'
            
            # Обновляем статус
            if USE_MOCK_DATA:
                # Обновление в моковых данных
                for s in MOCK_SERVERS:
                    if isinstance(s, dict) and s.get('id') == server_id:
                        s['status'] = new_status
                        break
            else:
                # Обновление через API
                try:
                    from utils.db_client import DatabaseClient
                    
                    db_client = DatabaseClient(
                        base_url=current_app.config['API_BASE_URL'],
                        api_key=current_app.config['API_KEY']
                    )
                    
                    # Подготовка данных для обновления
                    update_data = {'status': new_status}
                    
                    # Альтернативный формат для API, если оно принимает is_active вместо status
                    if new_status in ['active', 'inactive']:
                        update_data['is_active'] = (new_status == 'active')
                    
                    # Отправка запроса
                    response = db_client.put(f'/api/servers/{server_id}', json=update_data)
                    
                    if response.status_code != 200:
                        flash('Не удалось обновить статус сервера', 'danger')
                        return redirect(url_for('servers.details', server_id=server_id))
                except Exception as e:
                    logger.exception(f"Ошибка при обновлении статуса сервера: {e}")
                    flash('Сервис недоступен', 'danger')
                    return redirect(url_for('servers.details', server_id=server_id))
            
            status_text = 'деактивирован' if new_status == 'inactive' else 'активирован'
            flash(f'Сервер успешно {status_text}', 'success')
        elif action == 'restart':
            if USE_MOCK_DATA:
                flash('WireGuard service restarted successfully (mock)', 'success')
            else:
                from utils.db_client import DatabaseClient
                
                db_client = DatabaseClient(
                    base_url=current_app.config['API_BASE_URL'],
                    api_key=current_app.config['API_KEY']
                )
                
                response = db_client.post(f'/api/servers/{server_id}/restart')
                if response.status_code == 200:
                    flash('WireGuard service restarted successfully', 'success')
                else:
                    flash('Failed to restart WireGuard service', 'danger')
        else:
            flash('Unknown action', 'danger')
            
        return redirect(url_for('servers.details', server_id=server_id))
    except Exception as e:
        logger.exception(f"Error performing server action: {str(e)}")
        flash('Service unavailable', 'danger')
        return redirect(url_for('servers.details', server_id=server_id))

# Вспомогательная функция для получения сервера
def get_server(server_id):
    """Получить информацию о сервере по ID."""
    try:
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        response = db_client.get(f'/api/servers/{server_id}')
        if response.status_code == 200:
            server_data = response.json()
            # Извлекаем данные сервера, если они в оболочке
            if isinstance(server_data, dict) and 'server' in server_data:
                server_data = server_data['server']
            return server_data
    except Exception as e:
        logger.exception(f"Error getting server info: {str(e)}")
    
    return None