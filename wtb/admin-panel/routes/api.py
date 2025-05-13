import os
import logging
import secrets
import requests
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/servers', methods=['POST'])
@login_required
def add_server():
    """Add a new server to the system."""
    try:
        data = request.json
        logger.info(f"Received data for adding server: {data}")
        
        # Проверка обязательных полей
        required_fields = ['endpoint', 'port', 'public_key', 'address', 'geolocation_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
        
        # Генерация уникального server_id, если он не предоставлен
        if 'server_id' not in data:
            import uuid
            data['server_id'] = f"srv-{uuid.uuid4().hex[:8]}"
        
        # Конвертация типов данных
        try:
            data['port'] = int(data['port']) if isinstance(data['port'], str) else data['port']
            data['geolocation_id'] = int(data['geolocation_id']) if isinstance(data['geolocation_id'], str) else data['geolocation_id']
            
            # Конвертация булевых полей
            if 'skip_api_check' in data and isinstance(data['skip_api_check'], str):
                data['skip_api_check'] = data['skip_api_check'].lower() in ('true', 'yes', '1', 'y')
        except ValueError as e:
            return jsonify({"error": f"Data error: {str(e)}"}), 400
        
        # Автоматическая генерация имени (если пусто)
        if not data.get('name'):
            data['name'] = f"Server {data['endpoint']}:{data['port']}"
        
        # Автоматическая генерация API_KEY (если пусто)
        if not data.get('api_key'):
            data['api_key'] = secrets.token_hex(16)
        
        # Автоматическая генерация API_URL (если пусто)
        if not data.get('api_url'):
            data['api_url'] = f"http://{data['endpoint']}:5000"
        
        # Добавление API_PATH (если пусто)
        if 'api_path' not in data:
            data['api_path'] = '/status'
        
        # Добавление статуса (если пусто)
        if not data.get('status'):
            data['status'] = 'active'
        
        # Запрос к базе данных для добавления сервера
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/api/servers/add", 
            json=data,
            timeout=15
        )
        
        if response.status_code != 200:
            return jsonify({
                "error": "Failed to add server",
                "details": response.text
            }), response.status_code
        
        logger.info(f"Server successfully added: {response.json()}")
        
        return jsonify({
            "success": True,
            "message": "Server successfully added",
            "server": response.json()
        }), 201
    except Exception as e:
        logger.exception(f"Error adding server: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@api_bp.route('/servers/<int:server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    """Delete a server from the system."""
    try:
        # Log delete request
        logger.info(f"Received request to delete server {server_id}")
        
        # Get server information to find public key
        DATABASE_SERVICE_URL = current_app.config['DATABASE_SERVICE_URL']
        WIREGUARD_SERVICE_URL = current_app.config['WIREGUARD_SERVICE_URL']
        
        server_response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", 
            timeout=10
        )
        
        if server_response.status_code != 200:
            logger.error(f"Server with ID {server_id} not found in database")
            return jsonify({"status": "error", "message": "Server not found"}), 404
        
        server_data = server_response.json()
        public_key = server_data.get("public_key")
        
        # Remove peer from WireGuard server if public key exists
        if public_key:
            try:
                wg_response = requests.delete(
                    f"{WIREGUARD_SERVICE_URL}/api/remove",
                    json={"public_key": public_key},
                    timeout=10
                )
                
                if wg_response.status_code != 200:
                    logger.warning(f"Error removing peer from WireGuard: {wg_response.status_code}, {wg_response.text}")
                else:
                    logger.info(f"Peer with public key {public_key} successfully removed from WireGuard")
            except Exception as e:
                logger.warning(f"Error communicating with WireGuard service: {str(e)}")
        
        # Delete server from database
        delete_response = requests.delete(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", 
            timeout=15
        )
        
        if delete_response.status_code != 200:
            logger.error(f"Error deleting server: {delete_response.status_code}, {delete_response.text}")
            
            # Check for error info in response
            error_message = "Failed to delete server"
            try:
                error_data = delete_response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
                
            return jsonify({"status": "error", "message": error_message}), delete_response.status_code
        
        logger.info(f"Server {server_id} successfully deleted")
        return jsonify({"status": "success", "message": "Server successfully deleted"})
        
    except Exception as e:
        logger.exception(f"Error deleting server: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "details": str(e)
        }), 500


@api_bp.route('/servers/<int:server_id>', methods=['PUT'])
@login_required
def update_server(server_id):
    """Update server information."""
    try:
        data = request.json
        logger.info(f"Received request to update server {server_id} with data: {data}")
        
        # Check for data presence
        if not data:
            logger.error("Received empty data")
            return jsonify({"error": "Empty request data"}), 400
        
        # Get current server data
        DATABASE_SERVICE_URL = current_app.config['DATABASE_SERVICE_URL']
        current_server_response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}", 
            timeout=10
        )
        
        if current_server_response.status_code != 200:
            logger.error(f"Server with ID {server_id} not found in database")
            return jsonify({"error": "Server not found"}), 404
            
        current_server = current_server_response.json()
        
        # Prepare data for database request
        update_data = {}
        
        # Add fields that are allowed to be updated
        allowed_fields = [
            'endpoint', 'port', 'address', 'geolocation_id', 'status', 
            'name', 'city', 'country', 'api_key', 'public_key', 
            'api_url', 'api_path', 'skip_api_check'
        ]
        
        for field in allowed_fields:
            if field in data:
                # Convert numeric fields from strings to numbers
                if field in ['port', 'geolocation_id'] and isinstance(data[field], str):
                    try:
                        update_data[field] = int(data[field])
                    except ValueError:
                        return jsonify({"error": f"Field '{field}' must be a number"}), 400
                # Convert boolean fields
                elif field == 'skip_api_check' and isinstance(data[field], str):
                    update_data[field] = data[field].lower() in ('true', 'yes', '1', 'y')
                else:
                    update_data[field] = data[field]
        
        # Check that there is data to update
        if not update_data:
            return jsonify({"error": "No fields specified for update"}), 400
        
        # If endpoint or port are updated but not api_url, generate it
        if ('endpoint' in update_data or 'port' in update_data) and 'api_url' not in update_data:
            # Use new values if present, otherwise use current values
            endpoint = update_data.get('endpoint', current_server.get('server', {}).get('endpoint'))
            port = update_data.get('port', current_server.get('server', {}).get('port'))
            
            if endpoint and port:
                update_data['api_url'] = f"http://{endpoint}:5000"
                logger.info(f"Automatically updated API URL for server: {update_data['api_url']}")
        
        # Send request to database
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/api/servers/{server_id}",
            json=update_data,
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Error updating server: {response.status_code}, {response.text}")
            
            # Check for error info in response
            error_message = "Error updating server"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
            except:
                pass
                
            return jsonify({
                "error": error_message,
                "details": response.text
            }), response.status_code
        
        # Log successful update
        logger.info(f"Server {server_id} successfully updated")
        return jsonify({
            "success": True, 
            "message": "Server data successfully updated",
            "server_id": server_id
        })
        
    except Exception as e:
        logger.exception(f"Error updating server: {e}")
        return jsonify({
            "error": str(e)
        }), 500

@api_bp.route('/geolocations/<int:geo_id>', methods=['DELETE'])
@login_required
def delete_geolocation(geo_id):
    """Delete a geolocation from the system."""
    try:
        logger.info(f"Received request to delete geolocation {geo_id}")
        
        # Check if geolocation is used by servers
        DATABASE_SERVICE_URL = current_app.config['DATABASE_SERVICE_URL']
        servers_response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/servers", 
            timeout=10
        )
        
        if servers_response.status_code == 200:
            servers = servers_response.json().get("servers", [])
            used_by_servers = [s for s in servers if s.get('geolocation_id') == geo_id]
            
            if used_by_servers:
                logger.warning(f"Geolocation {geo_id} is used by {len(used_by_servers)} servers. Cannot delete.")
                server_names = ", ".join([s.get('name', f"Server {s.get('id')}") for s in used_by_servers[:5]])
                
                # If more than 5 servers, add ellipsis
                if len(used_by_servers) > 5:
                    server_names += " and others"
                    
                return jsonify({
                    "status": "error", 
                    "message": f"Geolocation is used by {len(used_by_servers)} servers: {server_names}. Change the geolocation of these servers first."
                }), 400
        else:
            logger.warning(f"Failed to get server list: {servers_response.status_code}. Continuing with geolocation deletion.")
        
        # Send request to delete geolocation
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Error deleting geolocation: {response.status_code}, {response.text}")
            
            # Check for error info in response
            error_message = "Error deleting geolocation"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
                elif "message" in error_data:
                    error_message = error_data.get("message")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
        
        logger.info(f"Geolocation {geo_id} successfully deleted")
        return jsonify({"status": "success", "message": "Geolocation successfully deleted"})
        
    except Exception as e:
        logger.exception(f"Error deleting geolocation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/geolocations/<int:geo_id>', methods=['PUT'])
@login_required
def update_geolocation(geo_id):
    """Update geolocation information."""
    try:
        data = request.json
        logger.info(f"Received request to update geolocation {geo_id} with data: {data}")
        
        # Check for data presence
        if not data:
            logger.error("Received empty data")
            return jsonify({"status": "error", "message": "Empty request data"}), 400
        
        # Check if geolocation exists
        DATABASE_SERVICE_URL = current_app.config['DATABASE_SERVICE_URL']
        check_response = requests.get(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}", 
            timeout=10
        )
        
        if check_response.status_code != 200:
            logger.error(f"Geolocation with ID {geo_id} not found")
            return jsonify({"status": "error", "message": "Geolocation not found"}), 404
        
        # Prepare data for request
        update_data = {}
        
        # Add fields that are allowed to be updated
        allowed_fields = ['code', 'name', 'available', 'description']
        for field in allowed_fields:
            if field in data:
                # Special handling for 'available' field - convert to boolean value
                if field == 'available':
                    if isinstance(data[field], str):
                        update_data[field] = data[field].lower() in ['true', '1', 'yes', 'y']
                    else:
                        update_data[field] = bool(data[field])
                elif field == 'code' and isinstance(data[field], str):
                    # Convert code to uppercase
                    update_data[field] = data[field].upper()
                else:
                    update_data[field] = data[field]
        
        # Check that there is data to update
        if not update_data:
            return jsonify({"status": "error", "message": "No fields specified for update"}), 400
        
        # Send request to update geolocation
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/api/geolocations/{geo_id}",
            json=update_data,
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Error updating geolocation: {response.status_code}, {response.text}")
            
            # Check for error info in response
            error_message = "Error updating geolocation"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_message = error_data.get("error")
                elif "message" in error_data:
                    error_message = error_data.get("message")
            except:
                pass
            
            return jsonify({"status": "error", "message": error_message}), response.status_code
        
        logger.info(f"Geolocation {geo_id} successfully updated")
        return jsonify({
            "status": "success", 
            "message": "Geolocation successfully updated",
            "geolocation_id": geo_id
        })
        
    except Exception as e:
        logger.exception(f"Error updating geolocation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500