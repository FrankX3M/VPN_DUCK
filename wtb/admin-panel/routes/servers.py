import os
import logging
import secrets
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required

from forms import ServerForm, FilterForm
from utils.chart_generator import ChartGenerator
from config import USE_MOCK_DATA

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
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
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

@servers_bp.route('/<int:server_id>')
@login_required
def details(server_id):
    """Show detailed information about a server."""
    hours = request.args.get('hours', 24, type=int)
    
    if USE_MOCK_DATA:
        # Use mock data for development
        from utils.mock_data import find_server, generate_mock_metrics
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers.index'))
            
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
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            response = db_client.get(f'/api/servers/{server_id}')
            if response.status_code == 200:
                server = response.json()
            else:
                flash('Server not found', 'danger')
                return redirect(url_for('servers.index'))
        except Exception as e:
            logger.exception(f"Error fetching server details: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('servers.index'))
        
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
        chart_generator = ChartGenerator()
        if metrics and 'history' in metrics and metrics['history']:
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

@servers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new server."""
    form = ServerForm()
    
    if USE_MOCK_DATA:
        # Use mock data for development
        from utils.mock_data import MOCK_GEOLOCATIONS, MOCK_SERVERS
        form.geolocation_id.choices = [(g['id'], g['name']) for g in MOCK_GEOLOCATIONS if g.get('available', True)]
        
        if form.validate_on_submit():
            try:
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
                return redirect(url_for('servers.details', server_id=server.get('id')))
            except Exception as e:
                logger.exception(f"Error creating mock server: {str(e)}")
                flash('Error creating server', 'danger')
    else:
        # Load geolocation choices from API
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
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
                    return redirect(url_for('servers.details', server_id=server.get('id')))
                else:
                    flash('Failed to create server', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error creating server: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template('servers/add.html', form=form, now=datetime.now())

@servers_bp.route('/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(server_id):
    """Edit server information."""
    # Fetch server to edit
    if USE_MOCK_DATA:
        from utils.mock_data import find_server, MOCK_SERVERS, MOCK_GEOLOCATIONS
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers.index'))
            
        form = ServerForm(obj=server)
        form.geolocation_id.choices = [(g['id'], g['name']) for g in MOCK_GEOLOCATIONS]
        
        if form.validate_on_submit():
            try:
                # Update server data
                for server_item in MOCK_SERVERS:
                    if server_item['id'] == server_id:
                        server_item.update({
                            'name': form.name.data,
                            'endpoint': form.endpoint.data,
                            'port': form.port.data,
                            'address': form.address.data,
                            'public_key': form.public_key.data,
                            'geolocation_id': form.geolocation_id.data,
                            'geolocation_name': next((g['name'] for g in MOCK_GEOLOCATIONS if g['id'] == form.geolocation_id.data), "Unknown"),
                            'max_peers': form.max_peers.data,
                            'status': form.status.data,
                            'api_key': form.api_key.data,
                            'api_url': form.api_url.data
                        })
                        break
                
                flash('Server updated successfully', 'success')
                return redirect(url_for('servers.details', server_id=server_id))
            except Exception as e:
                logger.exception(f"Error updating mock server: {str(e)}")
                flash('Error updating server', 'danger')
    else:
        from utils.db_client import DatabaseClient
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            response = db_client.get(f'/api/servers/{server_id}')
            if response.status_code == 200:
                server = response.json()
            else:
                flash('Server not found', 'danger')
                return redirect(url_for('servers.index'))
        except Exception as e:
            logger.exception(f"Error fetching server: {str(e)}")
            flash('Service unavailable', 'danger')
            return redirect(url_for('servers.index'))
        
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
                    return redirect(url_for('servers.details', server_id=server_id))
                else:
                    flash('Failed to update server', 'danger')
                    
            except Exception as e:
                logger.exception(f"Error updating server: {str(e)}")
                flash('Service unavailable', 'danger')
    
    return render_template('servers/edit.html', form=form, server=server, now=datetime.now())

@servers_bp.route('/<int:server_id>/delete')
@login_required
def delete(server_id):
    """Delete a server."""
    if USE_MOCK_DATA:
        # Find server in mock data
        from utils.mock_data import find_server, MOCK_SERVERS
        server = find_server(server_id)
        if not server:
            flash('Server not found', 'danger')
            return redirect(url_for('servers.index'))
            
        # Remove server from mock data
        MOCK_SERVERS = [s for s in MOCK_SERVERS if s['id'] != server_id]
        
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

@servers_bp.route('/<int:server_id>/action/<action>', methods=['POST'])
@login_required
def action(server_id, action):
    """Perform action on server (restart, toggle status, etc)."""
    try:
        if USE_MOCK_DATA:
            from utils.mock_data import find_server, MOCK_SERVERS
            server = find_server(server_id)
            if not server:
                flash('Server not found', 'danger')
                return redirect(url_for('servers.index'))
                
            if action == 'restart':
                flash('WireGuard service restarted successfully (mock)', 'success')
                
            elif action == 'toggle_status':
                # Toggle status in mock data
                for s in MOCK_SERVERS:
                    if s['id'] == server_id:
                        s['status'] = 'inactive' if s['status'] == 'active' else 'active'
                        status_text = 'activated' if s['status'] == 'active' else 'deactivated'
                        flash(f'Server {status_text} successfully', 'success')
                        break
            else:
                flash('Unknown action', 'danger')
        else:
            from utils.db_client import DatabaseClient
            
            db_client = DatabaseClient(
                base_url=current_app.config['API_BASE_URL'],
                api_key=current_app.config['API_KEY']
            )
            
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
    
    return redirect(url_for('servers.details', server_id=server_id))