# Add this code to app.py
# Location: In the route handlers section, add this entire function

@app.route('/servers')
@login_required
def servers():
    # Get filter parameters from request
    search_term = request.args.get('search', '')
    geo_id = request.args.get('geo_id', 'all')
    status = request.args.get('status', 'all')
    view_mode = request.args.get('view', 'table')  # table or card
    
    # Create filter form instance
    filter_form = FilterForm()
    
    # Get all servers from API
    try:
        response = db_client.get('/api/servers/all')
        if response.status_code == 200:
            servers = response.json().get('servers', [])
        else:
            servers = []
            flash(f'Error getting server list: {response.status_code}', 'danger')
    except Exception as e:
        logger.exception(f"Error getting servers: {str(e)}")
        servers = []
        flash(f'Error: {str(e)}', 'danger')
    
    # Server-side filtering
    filtered_servers = []
    for server in servers:
        # Search by name, endpoint and ID
        search_match = (search_term == '' or 
                         (server.get('name', '') and search_term.lower() in server.get('name', '').lower()) or
                         (server.get('endpoint', '') and search_term.lower() in server.get('endpoint', '').lower()) or
                         (str(server.get('id', '')) == search_term))
        
        # Filter by geolocation
        geo_match = (geo_id == 'all' or str(server.get('geolocation_id', '')) == geo_id)
        
        # Filter by status
        status_match = (status == 'all' or server.get('status', '') == status)
        
        if search_match and geo_match and status_match:
            filtered_servers.append(server)
    
    # Get geolocation data for filter dropdown
    try:
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get('geolocations', [])
            
            # Update filter form choices
            filter_form.geolocation.choices = [('all', 'All Geolocations')] + [
                (str(g['id']), g['name']) for g in geolocations
            ]
        else:
            geolocations = []
    except Exception as e:
        logger.exception(f"Error getting geolocations: {str(e)}")
        geolocations = []
    
    # Set form values
    filter_form.search.data = search_term
    filter_form.geolocation.data = geo_id
    filter_form.status.data = status
    
    # Server statistics for dashboard
    total_servers = len(servers)
    active_servers = sum(1 for s in servers if s.get('status') == 'active')
    inactive_servers = sum(1 for s in servers if s.get('status') == 'inactive')
    degraded_servers = sum(1 for s in servers if s.get('status') == 'degraded')
    
    return render_template(
        'servers/index.html', 
        servers=filtered_servers, 
        geolocations=geolocations,
        filter_form=filter_form,
        view_mode=view_mode,
        stats={
            'total': total_servers,
            'active': active_servers,
            'inactive': inactive_servers,
            'degraded': degraded_servers
        }
    )
# Add this code to app.py
# Location: In the route handlers section, add this entire function

@app.route('/servers/add', methods=['GET', 'POST'])
@login_required
def add_server():
    """Route for adding a new server."""
    form = ServerForm()
    
    # Load geolocation choices for dropdown
    try:
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get("geolocations", [])
            form.geolocation_id.choices = [(g['id'], g['name']) for g in geolocations]
        else:
            flash('Failed to load geolocation list', 'warning')
            geolocations = []
    except Exception as e:
        logger.exception(f"Error loading geolocations: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        geolocations = []
    
    if form.validate_on_submit():
        # Generate API key if not specified
        if not form.api_key.data:
            form.api_key.data = secrets.token_hex(16)
        
        # Prepare data for API
        server_data = {
            "name": form.name.data or f"Server {form.endpoint.data}",
            "endpoint": form.endpoint.data,
            "port": form.port.data,
            "address": form.address.data,
            "public_key": form.public_key.data,
            "geolocation_id": form.geolocation_id.data,
            "api_key": form.api_key.data,
            "max_peers": form.max_peers.data or 100,
            "status": form.status.data,
            "location": f"{form.endpoint.data}:{form.port.data}",
            "api_url": form.api_url.data or f"http://{form.endpoint.data}:{form.port.data}/api"
        }
        
        try:
            # Send data to API
            response = db_client.post('/api/servers/add', json=server_data)
            
            if response.status_code in [200, 201]:
                flash('Server added successfully!', 'success')
                return redirect(url_for('servers'))
            else:
                error_msg = 'Error adding server'
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                flash(error_msg, 'danger')
        except Exception as e:
            logger.exception(f"Error adding server: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
    
    # Generate API key for the form if it doesn't have one
    if not form.api_key.data:
        form.api_key.data = secrets.token_hex(16)
    
    return render_template('servers/add.html', form=form, geolocations=geolocations)

@app.route('/servers/<int:server_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):
    """Route for editing an existing server."""
    form = ServerForm()
    
    # Load server data
    try:
        server_response = db_client.get(f'/api/servers/{server_id}')
        if server_response.status_code != 200:
            flash(f'Server with ID {server_id} not found', 'danger')
            return redirect(url_for('servers'))
        
        server = server_response.json()
    except Exception as e:
        logger.exception(f"Error loading server data: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('servers'))
    
    # Load geolocation choices
    try:
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get("geolocations", [])
            form.geolocation_id.choices = [(g['id'], g['name']) for g in geolocations]
        else:
            geolocations = []
    except Exception as e:
        logger.exception(f"Error loading geolocations: {str(e)}")
        geolocations = []
    
    # If form is submitted
    if form.validate_on_submit():
        # Prepare data for API
        server_data = {
            "id": server_id,
            "name": form.name.data,
            "endpoint": form.endpoint.data,
            "port": form.port.data,
            "address": form.address.data,
            "public_key": form.public_key.data,
            "geolocation_id": form.geolocation_id.data,
            "api_key": form.api_key.data,
            "max_peers": form.max_peers.data,
            "status": form.status.data,
            "api_url": form.api_url.data
        }
        
        try:
            # Send data to API
            response = db_client.put(f'/api/servers/{server_id}', json=server_data)
            
            if response.status_code == 200:
                flash('Server updated successfully!', 'success')
                return redirect(url_for('server_details', server_id=server_id))
            else:
                flash('Error updating server', 'danger')
        except Exception as e:
            logger.exception(f"Error updating server: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
    
    # Fill form with existing data for GET request
    elif request.method == 'GET':
        form.name.data = server.get('name', '')
        form.endpoint.data = server.get('endpoint', '')
        form.port.data = server.get('port', 51820)
        form.address.data = server.get('address', '')
        form.public_key.data = server.get('public_key', '')
        form.geolocation_id.data = server.get('geolocation_id')
        form.api_key.data = server.get('api_key', '')
        form.max_peers.data = server.get('max_peers', 100)
        form.status.data = server.get('status', 'active')
        form.api_url.data = server.get('api_url', '')
    
    return render_template('servers/edit.html', form=form, server=server, geolocations=geolocations)

# Add this code to app.py
# Location: In the route handlers section, add this entire function

@app.route('/servers/<int:server_id>', methods=['GET'])
@login_required
def server_details(server_id):
    """Route for viewing detailed server information with metrics."""
    try:
        # Get server information
        server_response = db_client.get(f'/api/servers/{server_id}')
        
        if server_response.status_code != 200:
            flash(f'Server with ID {server_id} not found', 'danger')
            return redirect(url_for('servers'))
        
        server = server_response.json()
        
        # Get server metrics
        hours = request.args.get('hours', 24, type=int)
        metrics_response = db_client.get(f'/api/servers/{server_id}/metrics?hours={hours}')
        
        if metrics_response.status_code == 200:
            metrics = metrics_response.json()
            
            # Generate server-side charts
            charts = {
                'latency': ChartGenerator.generate_metrics_image(metrics, 'latency', hours),
                'load': ChartGenerator.generate_metrics_image(metrics, 'load', hours),
                'resources': ChartGenerator.generate_metrics_image(metrics, 'resources', hours),
                'packet_loss': ChartGenerator.generate_metrics_image(metrics, 'packet_loss', hours)
            }
            
            # Generate interactive chart
            interactive_chart = ChartGenerator.generate_plotly_chart(metrics, 'server_detail')
        else:
            metrics = None
            charts = {}
            interactive_chart = None
            flash('Failed to load server metrics', 'warning')
            
        # Get geolocation info
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get('geolocations', [])
        else:
            geolocations = []
            
        return render_template(
            'servers/details.html',
            server=server,
            metrics=metrics,
            charts=charts,
            interactive_chart=interactive_chart,
            geolocations=geolocations,
            hours=hours
        )
            
    except Exception as e:
        logger.exception(f"Error loading server details: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('servers'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Route for the system dashboard with metrics visualization."""
    # Get all servers for metrics display
    try:
        servers_response = db_client.get('/api/servers/all')
        if servers_response.status_code == 200:
            servers = servers_response.json().get('servers', [])
        else:
            servers = []
            flash('Failed to load server list', 'warning')
    except Exception as e:
        logger.exception(f"Error loading server list: {str(e)}")
        servers = []
        flash(f'Error: {str(e)}', 'danger')
    
    # Get geolocation data
    try:
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get('geolocations', [])
        else:
            geolocations = []
    except Exception as e:
        logger.exception(f"Error loading geolocations: {str(e)}")
        geolocations = []
    
    # Generate charts for the dashboard
    try:
        # Collect metrics for all active servers
        all_metrics = []
        
        for server in servers:
            if server.get('status') == 'active':
                metrics_response = db_client.get(f"/api/servers/{server['id']}/metrics?hours=24")
                if metrics_response.status_code == 200:
                    server_metrics = metrics_response.json()
                    all_metrics.append({
                        'server_id': server['id'],
                        'server_name': server.get('name', f"Server {server['id']}"),
                        'geolocation_id': server.get('geolocation_id'),
                        'geolocation_name': server.get('geolocation_name', 'Unknown'),
                        'metrics': server_metrics
                    })
        
        # Generate charts for each geolocation
        geolocation_charts = {}
        for geo in geolocations:
            geo_servers = [s for s in all_metrics if s['geolocation_id'] == geo['id']]
            if geo_servers:
                # Combine metrics for servers in the same geolocation
                combined_metrics = {'history': []}
                for server in geo_servers:
                    for history_item in server['metrics'].get('history', []):
                        # Add server reference to the metrics
                        history_item['server_id'] = server['server_id']
                        history_item['server_name'] = server['server_name']
                        combined_metrics['history'].append(history_item)
                
                # Generate the charts
                latency_chart = ChartGenerator.generate_metrics_image(combined_metrics, 'latency')
                packet_loss_chart = ChartGenerator.generate_metrics_image(combined_metrics, 'packet_loss')
                
                if latency_chart and packet_loss_chart:
                    geolocation_charts[geo['id']] = {
                        'latency_chart': latency_chart,
                        'packet_loss_chart': packet_loss_chart,
                        'geo_name': geo['name'],
                        'servers_count': len(geo_servers)
                    }
    except Exception as e:
        logger.exception(f"Error generating charts: {str(e)}")
        flash(f'Error generating charts: {str(e)}', 'danger')
        all_metrics = []
        geolocation_charts = {}
    
    return render_template(
        'dashboard.html', 
        servers=servers, 
        geolocations=geolocations,
        all_metrics=all_metrics,
        geolocation_charts=geolocation_charts,
        current_hours=24
    )


# Add these routes to app.py for geolocation management

@app.route('/geolocations')
@login_required
def geolocations():
    """Route for geolocation management page."""
    try:
        # Get all geolocations
        geo_response = db_client.get('/api/geolocations')
        if geo_response.status_code == 200:
            geolocations = geo_response.json().get('geolocations', [])
            
            # Get server counts for each geolocation
            servers_response = db_client.get('/api/servers/all')
            if servers_response.status_code == 200:
                servers = servers_response.json().get('servers', [])
                
                # Count servers for each geolocation
                geo_counts = {}
                for server in servers:
                    geo_id = server.get('geolocation_id')
                    if geo_id:
                        geo_counts[geo_id] = geo_counts.get(geo_id, 0) + 1
                
                # Add server count to geolocations
                for geo in geolocations:
                    geo['server_count'] = geo_counts.get(geo['id'], 0)
            
        else:
            geolocations = []
            flash('Failed to load geolocation list', 'warning')
    except Exception as e:
        logger.exception(f"Error loading geolocations: {str(e)}")
        geolocations = []
        flash(f'Error: {str(e)}', 'danger')
    
    return render_template('geolocations/index.html', geolocations=geolocations)

@app.route('/geolocations/add', methods=['GET', 'POST'])
@login_required
def add_geolocation():
    """Route for adding a new geolocation."""
    form = GeolocationForm()
    
    if form.validate_on_submit():
        geo_data = {
            "code": form.code.data.upper(),
            "name": form.name.data,
            "available": form.available.data,
            "description": form.description.data or ""
        }
        
        try:
            response = db_client.post('/api/geolocations/add', json=geo_data)
            
            if response.status_code in [200, 201]:
                flash('Geolocation added successfully!', 'success')
                return redirect(url_for('geolocations'))
            else:
                error_msg = 'Error adding geolocation'
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                flash(error_msg, 'danger')
        except Exception as e:
            logger.exception(f"Error adding geolocation: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('geolocations/add.html', form=form)

@app.route('/geolocations/<int:geo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_geolocation(geo_id):
    """Route for editing an existing geolocation."""
    form = GeolocationForm()
    
    # Get geolocation data
    try:
        geo_response = db_client.get(f'/api/geolocations/{geo_id}')
        if geo_response.status_code != 200:
            flash(f'Geolocation with ID {geo_id} not found', 'danger')
            return redirect(url_for('geolocations'))
        
        geolocation = geo_response.json()
    except Exception as e:
        logger.exception(f"Error loading geolocation: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('geolocations'))
    
    # Get servers using this geolocation
    servers = []
    server_count = 0
    try:
        servers_response = db_client.get('/api/servers/all')
        if servers_response.status_code == 200:
            all_servers = servers_response.json().get('servers', [])
            servers = [s for s in all_servers if s.get('geolocation_id') == geo_id]
            server_count = len(servers)
    except Exception as e:
        logger.exception(f"Error loading servers: {str(e)}")
    
    if form.validate_on_submit():
        geo_data = {
            "id": geo_id,
            "code": form.code.data.upper(),
            "name": form.name.data,
            "available": form.available.data,
            "description": form.description.data or ""
        }      
        try:
            response = db_client.put(f'/api/geolocations/{geo_id}', json=geo_data)
            
            if response.status_code == 200:
                flash('Geolocation updated successfully!', 'success')
                return redirect(url_for('geolocations'))
            else:
                flash('Error updating geolocation', 'danger')
        except Exception as e:
            logger.exception(f"Error updating geolocation: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
    
    # Fill form with existing data for GET request
    elif request.method == 'GET':
        form.code.data = geolocation.get('code', '')
        form.name.data = geolocation.get('name', '')
        form.available.data = geolocation.get('available', True)
        form.description.data = geolocation.get('description', '')
    
    return render_template('geolocations/edit.html', 
                          form=form, 
                          geolocation=geolocation, 
                          servers=servers,
                          server_count=server_count)

@app.route('/geolocations/<int:geo_id>/toggle', methods=['GET'])
@login_required
def toggle_geolocation(geo_id):
    """Route for toggling geolocation availability."""
    try:
        # Get current geolocation data
        geo_response = db_client.get(f'/api/geolocations/{geo_id}')
        if geo_response.status_code != 200:
            flash(f'Geolocation with ID {geo_id} not found', 'danger')
            return redirect(url_for('geolocations'))
        
        geolocation = geo_response.json()
        
        # Update with toggled availability
        geo_data = geolocation.copy()
        geo_data['available'] = not geolocation.get('available', True)
        
        response = db_client.put(f'/api/geolocations/{geo_id}', json=geo_data)
        
        if response.status_code == 200:
            status = "enabled" if geo_data['available'] else "disabled"
            flash(f'Geolocation {geolocation.get("name")} {status} successfully!', 'success')
        else:
            flash('Error updating geolocation', 'danger')
    except Exception as e:
        logger.exception(f"Error toggling geolocation: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('geolocations'))

@app.route('/geolocations/<int:geo_id>/delete', methods=['GET'])
@login_required
def delete_geolocation(geo_id):
    """Route for deleting a geolocation."""
    try:
        # Check if geolocation has servers assigned
        servers_response = db_client.get('/api/servers/all')
        if servers_response.status_code == 200:
            servers = servers_response.json().get('servers', [])
            geo_servers = [s for s in servers if s.get('geolocation_id') == geo_id]
            
            if geo_servers:
                flash('Cannot delete geolocation with assigned servers', 'warning')
                return redirect(url_for('geolocations'))
        
        # Get geolocation name before deletion
        geo_response = db_client.get(f'/api/geolocations/{geo_id}')
        geo_name = "Geolocation"
        if geo_response.status_code == 200:
            geolocation = geo_response.json()
            geo_name = geolocation.get('name', "Geolocation")
        
        # Delete geolocation
        response = db_client.delete(f'/api/geolocations/{geo_id}')
        
        if response.status_code in [200, 204]:
            flash(f'{geo_name} deleted successfully!', 'success')
        else:
            flash('Error deleting geolocation', 'danger')
    except Exception as e:
        logger.exception(f"Error deleting geolocation: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('geolocations'))