# Complete app.py file with all necessary routes
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
import secrets
import logging
import os
from forms import FilterForm, ServerForm, GeolocationForm, LoginForm
from utils.chart_generator import ChartGenerator
from utils.db_client import DatabaseClient

# Import mock data for development mode
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'
if USE_MOCK_DATA:
    from utils.mock_data import (MOCK_SERVERS, MOCK_GEOLOCATIONS, 
                               generate_mock_metrics, find_server, 
                               find_geolocation, filter_servers,
                               authenticate_user, MOCK_USERS)
from werkzeug.security import check_password_hash
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['WTF_CSRF_ENABLED'] = True

# Required for CSRF protection in WTF-Forms
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

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

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Use mock data in development mode
            if USE_MOCK_DATA:
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
                    return redirect(next_page or url_for('index'))
                else:
                    flash('Invalid username or password', 'danger')
            else:
                # For development/testing environment, allow a hardcoded admin account
                # In production, this should be removed and authenticate against a proper backend
                if os.environ.get('FLASK_ENV') == 'development' and \
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
                    return redirect(next_page or url_for('index'))
                
                # Normal authentication with API
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
                    return redirect(next_page or url_for('index'))
                else:
                    flash('Invalid username or password', 'danger')
        except Exception as e:
            logger.exception(f"Login error: {str(e)}")
            flash('Service unavailable. Please try again later.', 'danger')
    
    return render_template('login.html', form=form, error=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', now=datetime.now())

@app.route('/dashboard')
@login_required
def dashboard():
    hours = request.args.get('hours', 24, type=int)
    
    if USE_MOCK_DATA:
        # Use mock data for development
        servers = MOCK_SERVERS
        geolocations = MOCK_GEOLOCATIONS
        
        # Get metrics for each server
        all_metrics = []
        geolocation_charts = {}
        
        for server in servers:
            server_id = server.get('id')
            metrics_data = generate_mock_metrics(server_id, hours)
            
            all_metrics.append({
                'server': server,
                'metrics': metrics_data
            })
            
            # Generate charts for geolocation if not already done
            geo_id = server.get('geolocation_id')
            if geo_id and geo_id not in geolocation_charts:
                geo_name = next((g['name'] for g in geolocations if g['id'] == geo_id), f"Location {geo_id}")
                
                # Count servers in this geolocation
                servers_count = sum(1 for s in servers if s.get('geolocation_id') == geo_id)
                
                # Generate charts
                latency_chart = ChartGenerator.generate_metrics_image(
                    metrics_data, 'latency', hours)
                packet_loss_chart = ChartGenerator.generate_metrics_image(
                    metrics_data, 'packet_loss', hours)
                    
                geolocation_charts[geo_id] = {
                    'geo_name': geo_name,
                    'servers_count': servers_count,
                    'latency_chart': latency_chart,
                    'packet_loss_chart': packet_loss_chart
                }
    else:
        # Get all servers from API
        try:
            response = db_client.get('/api/servers')
            if response.status_code == 200:
                servers = response.json()
            else:
                servers = []
                flash('Failed to fetch server list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching servers: {str(e)}")
            servers = []
            flash('Service unavailable', 'danger')
        
        # Get geolocations from API
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                geolocations = response.json()
            else:
                geolocations = []
                flash('Failed to fetch geolocation list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching geolocations: {str(e)}")
            geolocations = []
        
        # Get metrics for each server
        all_metrics = []
        geolocation_charts = {}
        
        for server in servers:
            try:
                metrics_response = db_client.get(f'/api/servers/{server["id"]}/metrics', 
                                                params={'hours': hours})
                
                if metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    all_metrics.append({
                        'server': server,
                        'metrics': metrics_data
                    })
                    
                    # Generate charts for geolocation if not already done
                    geo_id = server.get('geolocation_id')
                    if geo_id and geo_id not in geolocation_charts:
                        geo_name = next((g['name'] for g in geolocations if g['id'] == geo_id), f"Location {geo_id}")
                        
                        # Count servers in this geolocation
                        servers_count = sum(1 for s in servers if s.get('geolocation_id') == geo_id)
                        
                        # Generate charts
                        latency_chart = ChartGenerator.generate_metrics_image(
                            metrics_data, 'latency', hours)
                        packet_loss_chart = ChartGenerator.generate_metrics_image(
                            metrics_data, 'packet_loss', hours)
                            
                        geolocation_charts[geo_id] = {
                            'geo_name': geo_name,
                            'servers_count': servers_count,
                            'latency_chart': latency_chart,
                            'packet_loss_chart': packet_loss_chart
                        }
                        
            except Exception as e:
                logger.exception(f"Error fetching metrics for server {server.get('id')}: {str(e)}")
    
    return render_template(
        'dashboard.html',
        servers=servers,
        geolocations=geolocations,
        all_metrics=all_metrics,
        geolocation_charts=geolocation_charts,
        current_hours=hours,
        now=datetime.now()
    )# _id')
            if geo_id and geo_id not in geolocation_charts:
                geo_name = next((g['name'] for g in geolocations if g['id'] == geo_id), f"Location {geo_id}")
                
                # Count servers in this geolocation
                servers_count = sum(1 for s in servers if s.get('geolocation

# Server management routes
@app.route('/servers')
@login_required
def servers():
    # Initialize filter form
    filter_form = FilterForm()
    
    # Get query parameters for filtering
    search = request.args.get('search', '')
    geolocation = request.args.get('geolocation', 'all')
    status = request.args.get('status', 'all')
    view_mode = request.args.get('view', 'table')
    
    if USE_MOCK_DATA:
        # Use mock data for development
        geolocations = MOCK_GEOLOCATIONS
        
        # Update filter form choices
        filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
            (str(geo['id']), geo['name']) for geo in geolocations
        ]
        
        # Prepare filter params
        filters = {}
        if search:
            filters['search'] = search
        if geolocation != 'all':
            filters['geolocation_id'] = int(geolocation)
        if status != 'all':
            filters['status'] = status
            
        # Filter servers
        servers = filter_servers(filters)
    else:
        # Load geolocations for the filter dropdown from API
        try:
            geo_response = db_client.get('/api/geolocations')
            if geo_response.status_code == 200:
                geolocations = geo_response.json()
                filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
                    (str(geo['id']), geo['name']) for geo in geolocations
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
                servers = response.json()
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
        'active': sum(1 for s in servers if s.get('status') == 'active'),
        'inactive': sum(1 for s in servers if s.get('status') == 'inactive'),
        'degraded': sum(1 for s in servers if s.get('status') == 'degraded')
    }
    
    return render_template(
        'servers/index.html',
        servers=servers,
        filter_form=filter_form,
        view_mode=view_mode,
        stats=stats,
        now=datetime.now()
    )

@app.route('/servers/add', methods=['GET', 'POST'])
@login_required
def add_server():
    form = ServerForm()
    
    if USE_MOCK_DATA:
        # Use mock data for development
        form.geolocation_id.choices = [(g['id'], g['name']) for g in MOCK_GEOLOCATIONS if g.get('available', True)]
        
        if form.validate_on_submit():
            # Generate a new server ID (max ID + 1)
            new_id = max(s['id'] for s in MOCK_SERVERS) + 1
            
            # Create new server
            server = {
                'id': new_id,
                'name': form.name.data or f"Server {new_id}",
                'endpoint': form.endpoint.data,
                'port': form.port.data,
                'address': form.address.data,
                'public_key': form.public_key.data,
                'geolocation_id': form.geolocation_id.data,
                'geolocation_name': next((g['name'] for g in MOCK_GEOLOCATIONS if g['id'] == form.geolocation_id.data), "Unknown"),
                'max_peers': form.max_peers.data,
                'status': form.status.data,
                'api_key': form.api_key.data or secrets.token_hex(16),
                'api_url': form.api_url.data or f"http://{form.endpoint.data}:{form.port.data}/api"
            }
            
            # Add to the global mock data
            MOCK_SERVERS.append(server)
            
            flash(f"Server '{server.get('name')}' created successfully", 'success')
            return redirect(url_for('server_details', server_id=server.get('id')))
    else:
        # Load geolocation choices from API
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                geolocations = response.json()
                form.geolocation_id.choices = [(g['id'], g['name']) for g in geolocations if g.get('available', True)]
            else:
                flash('Failed to load geolocation options', 'warning')
                form.geolocation_id.choices = []
        except Exception as e:
            logger.exception(f"Error loading geolocations: {str(e)}")
            flash('Service unavailable', 'danger')
            form.geolocation_id.choices = []
        
        if form.validate_on_submit():
            try:
                # Prepare server data
                server_data = {
                    'name': form.name.data,
                    'endpoint': form.endpoint.data,
                    'port': form.port.data,
                    'address': form.address.data,
                    'public_key': form.public_key.data,
                    'geolocation_id': form.geolocation_id.data,
                    'max_peers': form.max_peers.data,
                    'status': form.status.data,
                    'api_key': form.api_key.data or secrets.token_hex(16),
                    'api_url': form.api_url.data or f"http://{form.endpoint.data}:{form.port.data}/api"
                }
                
                # Create server via API
                response = db_client.post('/api/servers', json=server_data)
                
                if response.status_code == 201:
                    server = response.json()
                    flash(f"Server '{server.get('name')}' created successfully", 'success')
                    return redirect(url_for('server_details', server_id=server.get('id')))
                else:
                    flash('Failed to create server', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error creating server: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template('servers/add.html', form=form, now=datetime.now())

@app.route('/servers/<int:server_id>')
@login_required
def server_details(server_id):
    hours = request.args.get('hours', 24, type=int)
    
    if USE_MOCK_DATA:
        # Use mock data for development
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers'))
            
        # Generate mock metrics
        metrics = generate_mock_metrics(server_id, hours)
        
        # Generate charts
        charts = {}
        if metrics and 'history' in metrics and metrics['history']:
            chart_generator = ChartGenerator()
            charts['latency'] = chart_generator.generate_metrics_image(metrics, 'latency', hours)
            charts['packet_loss'] = chart_generator.generate_metrics_image(metrics, 'packet_loss', hours)
            charts['resources'] = chart_generator.generate_metrics_image(metrics, 'resources', hours)
            
            # Generate interactive chart if plotly is available
            interactive_chart = chart_generator.generate_plotly_chart(metrics, 'server_detail')
        else:
            interactive_chart = None
    else:
        # Fetch server details from API
        try:
            response = db_client.get(f'/api/servers/{server_id}')
            if response.status_code == 200:
                server = response.json()
            else:
                flash('Server not found', 'danger')
                return redirect(url_for('servers'))
        except Exception as e:
            logger.exception(f"Error fetching server details: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('servers'))
        
        # Fetch metrics from API
        try:
            metrics_response = db_client.get(f'/api/servers/{server_id}/metrics', 
                                            params={'hours': hours})
            
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
            else:
                metrics = None
        except Exception as e:
            logger.exception(f"Error fetching server metrics: {str(e)}")
            metrics = None
        
        # Generate charts
        charts = {}
        if metrics and 'history' in metrics and metrics['history']:
            chart_generator = ChartGenerator()
            charts['latency'] = chart_generator.generate_metrics_image(metrics, 'latency', hours)
            charts['packet_loss'] = chart_generator.generate_metrics_image(metrics, 'packet_loss', hours)
            charts['resources'] = chart_generator.generate_metrics_image(metrics, 'resources', hours)
            
            # Generate interactive chart if plotly is available
            interactive_chart = chart_generator.generate_plotly_chart(metrics, 'server_detail')
        else:
            interactive_chart = None
    
    return render_template(
        'servers/details.html',
        server=server,
        metrics=metrics,
        charts=charts,
        interactive_chart=interactive_chart,
        hours=hours,
        now=datetime.now()
    )

@app.route('/servers/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):
    # Fetch server to edit
    try:
        response = db_client.get(f'/api/servers/{server_id}')
        if response.status_code == 200:
            server = response.json()
        else:
            flash('Server not found', 'danger')
            return redirect(url_for('servers'))
    except Exception as e:
        logger.exception(f"Error fetching server: {str(e)}")
        flash('Service unavailable', 'danger')
        return redirect(url_for('servers'))
    
    form = ServerForm(obj=server)
    
    # Load geolocation choices
    try:
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json()
            form.geolocation_id.choices = [(g['id'], g['name']) for g in geolocations]
        else:
            flash('Failed to load geolocation options', 'warning')
            form.geolocation_id.choices = [(server['geolocation_id'], 'Current Location')]
    except Exception as e:
        logger.exception(f"Error loading geolocations: {str(e)}")
        form.geolocation_id.choices = [(server['geolocation_id'], 'Current Location')]
    
    if form.validate_on_submit():
        try:
            # Prepare updated server data
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
                'api_url': form.api_url.data
            }
            
            # Update server via API
            response = db_client.put(f'/api/servers/{server_id}', json=server_data)
            
            if response.status_code == 200:
                flash('Server updated successfully', 'success')
                return redirect(url_for('server_details', server_id=server_id))
            else:
                flash('Failed to update server', 'danger')
                
        except Exception as e:
            logger.exception(f"Error updating server: {str(e)}")
            flash('Service unavailable', 'danger')
    
    return render_template('servers/edit.html', form=form, server=server, now=datetime.now())

@app.route('/servers/<int:server_id>/delete')
@login_required
def delete_server(server_id):
    try:
        response = db_client.delete(f'/api/servers/{server_id}')
        
        if response.status_code == 204:
            flash('Server deleted successfully', 'success')
        else:
            flash('Failed to delete server', 'danger')
            
    except Exception as e:
        logger.exception(f"Error deleting server: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('servers'))

@app.route('/servers/<int:server_id>/action/<action>', methods=['POST'])
@login_required
def server_action(server_id, action):
    try:
        if action == 'restart':
            response = db_client.post(f'/api/servers/{server_id}/restart')
            if response.status_code == 200:
                flash('WireGuard service restarted successfully', 'success')
            else:
                flash('Failed to restart WireGuard service', 'danger')
                
        elif action == 'toggle_status':
            # First get current status
            server_response = db_client.get(f'/api/servers/{server_id}')
            if server_response.status_code == 200:
                server = server_response.json()
                new_status = 'inactive' if server.get('status') == 'active' else 'active'
                
                # Update status
                update_response = db_client.put(
                    f'/api/servers/{server_id}',
                    json={'status': new_status}
                )
                
                if update_response.status_code == 200:
                    status_text = 'activated' if new_status == 'active' else 'deactivated'
                    flash(f'Server {status_text} successfully', 'success')
                else:
                    flash('Failed to update server status', 'danger')
            else:
                flash('Failed to get server information', 'danger')
        else:
            flash('Unknown action', 'danger')
            
    except Exception as e:
        logger.exception(f"Error performing server action: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('server_details', server_id=server_id))

# Geolocation management routes
@app.route('/geolocations')
@login_required
def geolocations():
    if USE_MOCK_DATA:
        # Use mock data for development
        geolocations = MOCK_GEOLOCATIONS.copy()
        servers = MOCK_SERVERS
            
        # Count servers per geolocation
        for geo in geolocations:
            geo['server_count'] = sum(1 for s in servers if s.get('geolocation_id') == geo['id'])
    else:
        try:
            response = db_client.get('/api/geolocations')
            if response.status_code == 200:
                geolocations = response.json()
                
                # Get server counts for each geolocation
                server_response = db_client.get('/api/servers')
                if server_response.status_code == 200:
                    servers = server_response.json()
                    
                    # Count servers per geolocation
                    for geo in geolocations:
                        geo['server_count'] = sum(1 for s in servers if s.get('geolocation_id') == geo['id'])
                
            else:
                geolocations = []
                flash('Failed to fetch geolocation list', 'warning')
        except Exception as e:
            logger.exception(f"Error fetching geolocations: {str(e)}")
            geolocations = []
            flash('Service unavailable', 'danger')
    
    return render_template('geolocations/index.html', geolocations=geolocations, now=datetime.now())

@app.route('/geolocations/add', methods=['GET', 'POST'])
@login_required
def add_geolocation():
    form = GeolocationForm()
    
    if form.validate_on_submit():
        try:
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
                return redirect(url_for('geolocations'))
            else:
                flash('Failed to create geolocation', 'danger')
                
        except Exception as e:
            logger.exception(f"Error creating geolocation: {str(e)}")
            flash('Service unavailable', 'danger')
    
    return render_template('geolocations/add.html', form=form, now=datetime.now())

@app.route('/geolocations/<int:geo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_geolocation(geo_id):
    # Fetch geolocation to edit
    try:
        response = db_client.get(f'/api/geolocations/{geo_id}')
        if response.status_code == 200:
            geolocation = response.json()
        else:
            flash('Geolocation not found', 'danger')
            return redirect(url_for('geolocations'))
    except Exception as e:
        logger.exception(f"Error fetching geolocation: {str(e)}")
        flash('Service unavailable', 'danger')
        return redirect(url_for('geolocations'))
    
    form = GeolocationForm(obj=geolocation)
    
    # Count servers using this geolocation
    try:
        server_response = db_client.get('/api/servers')
        if server_response.status_code == 200:
            servers = server_response.json()
            server_count = sum(1 for s in servers if s.get('geolocation_id') == geo_id)
            geo_servers = [s for s in servers if s.get('geolocation_id') == geo_id]
        else:
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
            
            # Update geolocation via API
            response = db_client.put(f'/api/geolocations/{geo_id}', json=geo_data)
            
            if response.status_code == 200:
                flash('Geolocation updated successfully', 'success')
                return redirect(url_for('geolocations'))
            else:
                flash('Failed to update geolocation', 'danger')
                
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

@app.route('/geolocations/<int:geo_id>/toggle')
@login_required
def toggle_geolocation(geo_id):
    try:
        # First get current status
        geo_response = db_client.get(f'/api/geolocations/{geo_id}')
        if geo_response.status_code == 200:
            geo = geo_response.json()
            
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
    
    return redirect(url_for('geolocations'))

@app.route('/geolocations/<int:geo_id>/delete')
@login_required
def delete_geolocation(geo_id):
    try:
        # First check if any servers are using this geolocation
        server_response = db_client.get('/api/servers')
        if server_response.status_code == 200:
            servers = server_response.json()
            if any(s.get('geolocation_id') == geo_id for s in servers):
                flash('Cannot delete geolocation with active servers', 'danger')
                return redirect(url_for('geolocations'))
        
        # Delete geolocation
        response = db_client.delete(f'/api/geolocations/{geo_id}')
        
        if response.status_code == 204:
            flash('Geolocation deleted successfully', 'success')
        else:
            flash('Failed to delete geolocation', 'danger')
            
    except Exception as e:
        logger.exception(f"Error deleting geolocation: {str(e)}")
        flash('Service unavailable', 'danger')
    
    return redirect(url_for('geolocations'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')