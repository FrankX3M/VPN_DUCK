import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required

from forms import GeolocationForm
from config import USE_MOCK_DATA

logger = logging.getLogger(__name__)

# Create blueprint
geolocations_bp = Blueprint('geolocations', __name__)

@geolocations_bp.route('/')
@login_required
def index():
    """Display list of geolocations."""
    if USE_MOCK_DATA:
        # Use mock data for development
        from utils.mock_data import MOCK_GEOLOCATIONS, MOCK_SERVERS
        geolocations = MOCK_GEOLOCATIONS.copy()
        servers = MOCK_SERVERS
            
        # Count servers per geolocation
        for geo in geolocations:
            if not isinstance(geo, dict):
                logger.warning(f"Геолокация не является словарем: {geo}")
                continue
                
            geo_id = geo.get('id')
            if geo_id is None:
                logger.warning(f"Геолокация не имеет ID: {geo}")
                continue
                
            if isinstance(servers, list):
                geo['server_count'] = sum(1 for s in servers if isinstance(s, dict) and s.get('geolocation_id') == geo_id)
            else:
                geo['server_count'] = 0
    else:
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                data = response.json()
                # Проверяем формат данных
                if isinstance(data, dict) and 'geolocations' in data:
                    geolocations = data['geolocations']
                elif isinstance(data, list):
                    geolocations = data
                else:
                    logger.warning(f"Неожиданный формат данных от API (geolocations): {data}")
                    geolocations = []
                    flash('Unexpected data format from API (geolocations)', 'warning')
                
                # Get server counts for each geolocation
                server_response = db_client.get('/api/servers')
                if server_response.status_code == 200:
                    data = server_response.json()
                    # Проверяем формат данных
                    if isinstance(data, dict) and 'servers' in data:
                        servers = data['servers']
                    elif isinstance(data, list):
                        servers = data
                    else:
                        logger.warning(f"Неожиданный формат данных от API (servers): {data}")
                        servers = []
                    
                    # Count servers per geolocation
                    for geo in geolocations:
                        if not isinstance(geo, dict):
                            logger.warning(f"Геолокация не является словарем: {geo}")
                            continue
                            
                        geo_id = geo.get('id')
                        if geo_id is None:
                            logger.warning(f"Геолокация не имеет ID: {geo}")
                            continue
                            
                        if isinstance(servers, list):
                            geo['server_count'] = sum(1 for s in servers if isinstance(s, dict) and s.get('geolocation_id') == geo_id)
                        else:
                            geo['server_count'] = 0
            else:
                geolocations = []
                flash('Failed to fetch geolocation list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching geolocations: {str(e)}")
            geolocations = []
            flash('Service unavailable', 'danger')
    
    return render_template('geolocations/index.html', geolocations=geolocations, now=datetime.now())

@geolocations_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new geolocation."""
    form = GeolocationForm()
    
    if form.validate_on_submit():
        try:
            if USE_MOCK_DATA:
                from utils.mock_data import MOCK_GEOLOCATIONS
                # Generate a new ID for the mock geolocation
                if not MOCK_GEOLOCATIONS:
                    new_id = 1
                else:
                    new_id = max(g.get('id', 0) for g in MOCK_GEOLOCATIONS if isinstance(g, dict)) + 1
                
                # Create new geolocation
                geo = {
                    'id': new_id,
                    'code': form.code.data.upper(),
                    'name': form.name.data,
                    'available': form.available.data,
                    'description': form.description.data
                }
                
                # Add to mock data
                MOCK_GEOLOCATIONS.append(geo)
                
                flash(f"Geolocation '{geo.get('name')}' created successfully", 'success')
                return redirect(url_for('geolocations.index'))
            else:
                from utils.db_client import DatabaseClient
                
                db_client = DatabaseClient(
                    base_url=current_app.config['API_BASE_URL'],
                    api_key=current_app.config['API_KEY']
                )
                
                # Prepare geolocation data
                geo_data = {
                    'code': form.code.data.upper(),
                    'name': form.name.data,
                    'available': form.available.data,
                    'description': form.description.data
                }
                
                # Create geolocation via API
                response = db_client.post('/api/geolocations', json=geo_data)
                
                if response.status_code == 201:
                    geo = response.json()
                    flash(f"Geolocation '{geo.get('name')}' created successfully", 'success')
                    return redirect(url_for('geolocations.index'))
                else:
                    flash('Failed to create geolocation', 'danger')
                    
        except Exception as e:
            logger.exception(f"Error creating geolocation: {str(e)}")
            flash('Service unavailable', 'danger')
    
    return render_template('geolocations/add.html', form=form, now=datetime.now())

@geolocations_bp.route('/<int:geo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(geo_id):
    """Edit geolocation information."""
    # Логирование для отладки
    logger.info(f"Получен запрос на редактирование геолокации ID: {geo_id}")
    
    # Fetch geolocation to edit
    if USE_MOCK_DATA:
        from utils.mock_data import find_geolocation, MOCK_SERVERS, MOCK_GEOLOCATIONS
        geolocation = find_geolocation(geo_id)
        if not geolocation:
            logger.error(f"Геолокация не найдена в моковых данных. ID: {geo_id}")
            flash('Geolocation not found', 'danger')
            return redirect(url_for('geolocations.index'))
            
        # Count servers using this geolocation
        geo_servers = [s for s in MOCK_SERVERS if isinstance(s, dict) and s.get('geolocation_id') == geo_id]
        server_count = len(geo_servers)
        
        form = GeolocationForm()
        if not form.is_submitted():
            # Заполняем форму данными только если она не была отправлена
            form = GeolocationForm(obj=geolocation)
        
        if form.validate_on_submit():
            try:
                # Update geolocation in mock data
                found = False
                for geo in MOCK_GEOLOCATIONS:
                    if isinstance(geo, dict) and geo.get('id') == geo_id:
                        geo.update({
                            'code': form.code.data.upper(),
                            'name': form.name.data,
                            'available': form.available.data,
                            'description': form.description.data
                        })
                        found = True
                        break
                
                if not found:
                    logger.error(f"Геолокация не найдена при обновлении моковых данных. ID: {geo_id}")
                    flash('Geolocation not found for update', 'danger')
                    return redirect(url_for('geolocations.index'))
                
                flash('Geolocation updated successfully', 'success')
                return redirect(url_for('geolocations.index'))
            except Exception as e:
                logger.exception(f"Error updating mock geolocation: {str(e)}")
                flash('Error updating geolocation', 'danger')
    else:
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            logger.info(f"Запрос к API для получения геолокации ID: {geo_id}")
            response = db_client.get(f'/api/geolocations/{geo_id}')
            
            if response.status_code == 200:
                logger.info(f"Геолокация успешно получена. ID: {geo_id}")
                geolocation = response.json()
                
                if not isinstance(geolocation, dict):
                    logger.error(f"Получены неверные данные для геолокации. ID: {geo_id}, Data: {geolocation}")
                    flash('Invalid geolocation data received from API', 'danger')
                    return redirect(url_for('geolocations.index'))
            else:
                logger.error(f"Ошибка при получении геолокации. ID: {geo_id}, Код: {response.status_code}")
                flash('Geolocation not found', 'danger')
                return redirect(url_for('geolocations.index'))
        except Exception as e:
            logger.exception(f"Error fetching geolocation: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('geolocations.index'))
        
        # Создаем форму и заполняем ее данными
        form = GeolocationForm()
        if not form.is_submitted():
            # Заполняем форму данными только если она не была отправлена
            form = GeolocationForm(obj=geolocation)
        
        # Count servers using this geolocation
        try:
            server_response = db_client.get('/api/servers')
            if server_response.status_code == 200:
                data = server_response.json()
                # Проверяем формат данных
                if isinstance(data, dict) and 'servers' in data:
                    servers = data['servers']
                elif isinstance(data, list):
                    servers = data
                else:
                    logger.warning(f"Неожиданный формат данных от API (servers): {data}")
                    servers = []
                
                server_count = sum(1 for s in servers if isinstance(s, dict) and s.get('geolocation_id') == geo_id)
                geo_servers = [s for s in servers if isinstance(s, dict) and s.get('geolocation_id') == geo_id]
            else:
                logger.warning(f"Не удалось получить серверы. Код: {server_response.status_code}")
                server_count = 0
                geo_servers = []
        except Exception as e:
            logger.exception(f"Error counting servers for geolocation: {str(e)}")
            server_count = 0
            geo_servers = []
        
        if form.validate_on_submit():
            try:
                # Prepare updated geolocation data
                geo_data = {
                    'code': form.code.data.upper(),
                    'name': form.name.data,
                    'available': form.available.data,
                    'description': form.description.data
                }
                
                logger.info(f"Отправка запроса на обновление геолокации. ID: {geo_id}, Данные: {geo_data}")
                
                # Update geolocation via API
                response = db_client.put(f'/api/geolocations/{geo_id}', json=geo_data)
                
                if response.status_code == 200:
                    logger.info(f"Геолокация успешно обновлена. ID: {geo_id}")
                    flash('Geolocation updated successfully', 'success')
                    return redirect(url_for('geolocations.index'))
                else:
                    logger.error(f"Ошибка при обновлении геолокации. ID: {geo_id}, Код: {response.status_code}, Ответ: {response.text}")
                    flash(f'Failed to update geolocation: {response.text}', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error updating geolocation: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template(
        'geolocations/edit.html', 
        form=form, 
        geolocation=geolocation, 
        server_count=server_count,
        servers=geo_servers,
        now=datetime.now()
    )

@geolocations_bp.route('/<int:geo_id>/delete')
@login_required
def delete(geo_id):
    """Delete a geolocation."""
    try:
        if USE_MOCK_DATA:
            from utils.mock_data import MOCK_SERVERS, MOCK_GEOLOCATIONS
            # Check if any servers are using this geolocation
            if any(isinstance(s, dict) and s.get('geolocation_id') == geo_id for s in MOCK_SERVERS):
                flash('Cannot delete geolocation with active servers', 'danger')
                return redirect(url_for('geolocations.index'))
                
            # Remove from mock data
            global MOCK_GEOLOCATIONS
            MOCK_GEOLOCATIONS = [g for g in MOCK_GEOLOCATIONS if not isinstance(g, dict) or g.get('id') != geo_id]
            
            flash('Geolocation deleted successfully', 'success')
        else:
            from utils.db_client import DatabaseClient
            
            db_client = DatabaseClient(
                base_url=current_app.config['API_BASE_URL'],
                api_key=current_app.config['API_KEY']
            )
            
            # First check if any servers are using this geolocation
            server_response = db_client.get('/api/servers')
            if server_response.status_code == 200:
                data = server_response.json()
                # Проверяем формат данных
                if isinstance(data, dict) and 'servers' in data:
                    servers = data['servers']
                elif isinstance(data, list):
                    servers = data
                else:
                    logger.warning(f"Неожиданный формат данных от API (servers): {data}")
                    servers = []
                
                if any(isinstance(s, dict) and s.get('geolocation_id') == geo_id for s in servers):
                    flash('Cannot delete geolocation with active servers', 'danger')
                    return redirect(url_for('geolocations.index'))
            
            # Delete geolocation
            response = db_client.delete(f'/api/geolocations/{geo_id}')
            
            if response.status_code in [200, 204]:
                flash('Geolocation deleted successfully', 'success')
            else:
                flash('Failed to delete geolocation', 'danger')
                
    except Exception as e:
        logger.exception(f"Error deleting geolocation: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('geolocations.index'))

@geolocations_bp.route('/<int:geo_id>/toggle')
@login_required
def toggle(geo_id):
    """Toggle geolocation availability."""
    try:
        if USE_MOCK_DATA:
            from utils.mock_data import find_geolocation, MOCK_GEOLOCATIONS
            # Find geolocation in mock data
            geolocation = find_geolocation(geo_id)
            if not geolocation:
                flash('Geolocation not found', 'danger')
                return redirect(url_for('geolocations.index'))

            # Toggle availability
            for geo in MOCK_GEOLOCATIONS:
                if isinstance(geo, dict) and geo.get('id') == geo_id:
                    geo['available'] = not geo.get('available', True)
                    status_text = 'enabled' if geo['available'] else 'disabled'
                    flash(f'Geolocation {status_text} successfully', 'success')
                    break
        else:
            from utils.db_client import DatabaseClient
            
            db_client = DatabaseClient(
                base_url=current_app.config['API_BASE_URL'],
                api_key=current_app.config['API_KEY']
            )
            
            # First get current status
            geo_response = db_client.get(f'/api/geolocations/{geo_id}')
            if geo_response.status_code == 200:
                geo = geo_response.json()
                
                if not isinstance(geo, dict):
                    logger.error(f"Получены неверные данные для геолокации. ID: {geo_id}, Data: {geo}")
                    flash('Invalid geolocation data received from API', 'danger')
                    return redirect(url_for('geolocations.index'))
                
                # Toggle availability
                new_availability = not geo.get('available', True)
                
                # Update status
                update_response = db_client.put(
                    f'/api/geolocations/{geo_id}',
                    json={'available': new_availability}
                )
                
                if update_response.status_code == 200:
                    status_text = 'enabled' if new_availability else 'disabled'
                    flash(f'Geolocation {status_text} successfully', 'success')
                else:
                    flash('Failed to update geolocation status', 'danger')
            else:
                flash('Failed to get geolocation information', 'danger')
                
    except Exception as e:
        logger.exception(f"Error toggling geolocation: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('geolocations.index'))