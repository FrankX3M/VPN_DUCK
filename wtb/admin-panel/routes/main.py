from datetime import datetime
import logging
from flask import Blueprint, render_template, jsonify, redirect, url_for, request, flash
from flask_login import login_required, current_user

from config import USE_MOCK_DATA
from utils.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Main index route."""
    return render_template('index.html', now=datetime.now())

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route showing server metrics and status."""
    hours = request.args.get('hours', 24, type=int)
    
    if USE_MOCK_DATA:
        # Use mock data for development
        from utils.mock_data import MOCK_SERVERS, MOCK_GEOLOCATIONS, generate_mock_metrics
        
        servers = MOCK_SERVERS
        geolocations = MOCK_GEOLOCATIONS
        
        # Get metrics for each server
        all_metrics = []
        geolocation_charts = {}
        
        for server in servers:
            try:
                # Проверяем, что server является словарем
                if not isinstance(server, dict):
                    logger.warning(f"Сервер не является словарем: {server}")
                    continue
                    
                server_id = server.get('id')
                if server_id is None:
                    logger.warning(f"Сервер не имеет ID: {server}")
                    continue
                    
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
                    servers_count = sum(1 for s in servers if isinstance(s, dict) and s.get('geolocation_id') == geo_id)
                    
                    # Generate charts
                    chart_generator = ChartGenerator()
                    latency_chart = chart_generator.generate_metrics_image(
                        metrics_data, 'latency', hours)
                    packet_loss_chart = chart_generator.generate_metrics_image(
                        metrics_data, 'packet_loss', hours)
                        
                    geolocation_charts[geo_id] = {
                        'geo_name': geo_name,
                        'servers_count': servers_count,
                        'latency_chart': latency_chart,
                        'packet_loss_chart': packet_loss_chart
                    }
            except Exception as e:
                server_id = server.get('id') if isinstance(server, dict) else str(server)
                logger.exception(f"Error generating metrics for server {server_id}: {str(e)}")
    else:
        # Get all servers from API
        from utils.db_client import DatabaseClient
        from flask import current_app
        
        db_client = DatabaseClient(
            base_url=current_app.config['API_BASE_URL'],
            api_key=current_app.config['API_KEY']
        )
        
        try:
            response = db_client.get('/api/servers')
            if response.status_code == 200:
                data = response.json()
                # Проверяем формат данных
                if isinstance(data, dict) and 'servers' in data:
                    servers = data['servers']
                elif isinstance(data, list):
                    servers = data
                else:
                    logger.warning(f"Неожиданный формат данных от API: {data}")
                    servers = []
                    flash('Unexpected data format from API', 'warning')
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
                # Проверяем, что server является словарем
                if not isinstance(server, dict):
                    logger.warning(f"Сервер не является словарем: {server}")
                    continue
                    
                server_id = server.get('id')
                if server_id is None:
                    logger.warning(f"Сервер не имеет ID: {server}")
                    continue
                
                metrics_response = db_client.get(f'/api/servers/{server_id}/metrics', 
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
                        geo_name = next((g['name'] for g in geolocations if isinstance(g, dict) and g.get('id') == geo_id), f"Location {geo_id}")
                        
                        # Count servers in this geolocation
                        servers_count = sum(1 for s in servers if isinstance(s, dict) and s.get('geolocation_id') == geo_id)
                        
                        # Generate charts
                        chart_generator = ChartGenerator()
                        latency_chart = chart_generator.generate_metrics_image(
                            metrics_data, 'latency', hours)
                        packet_loss_chart = chart_generator.generate_metrics_image(
                            metrics_data, 'packet_loss', hours)
                            
                        geolocation_charts[geo_id] = {
                            'geo_name': geo_name,
                            'servers_count': servers_count,
                            'latency_chart': latency_chart,
                            'packet_loss_chart': packet_loss_chart
                        }
            except Exception as e:
                server_id = server.get('id') if isinstance(server, dict) else str(server)
                logger.exception(f"Error fetching metrics for server {server_id}: {str(e)}")
    
    return render_template(
        'dashboard.html',
        servers=servers,
        geolocations=geolocations,
        all_metrics=all_metrics,
        geolocation_charts=geolocation_charts,
        current_hours=hours,
        now=datetime.now()
    )

@main_bp.route('/admin/download-bootstrap', methods=['GET'])
@login_required
def admin_download_bootstrap():
    """Download local copies of Bootstrap, jQuery and other libraries."""
    try:
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin rights required.', 'danger')
            return redirect(url_for('main.index'))
        
        from utils.template_utils import download_bootstrap_resources
        from flask import current_app
        
        result = download_bootstrap_resources(current_app.root_path)
        
        # Check results
        if result['failed']:
            flash(f"Failed to download some files: {', '.join(result['failed'])}", 'warning')
        
        if result['downloaded']:
            flash(f"Successfully downloaded: {', '.join(result['downloaded'])}", 'success')
        
        logger.info("Local library copies successfully downloaded")
        return redirect(url_for('main.index'))
        
    except Exception as e:
        logger.exception(f"Error downloading libraries: {e}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/health')
def health_check():
    """Health check endpoint for container orchestration."""
    return jsonify({"status": "ok", "version": "1.0.0"}), 200