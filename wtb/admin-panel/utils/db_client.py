import requests
import logging
import time
import json
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)

class DatabaseClient:
    """
    Client for interacting with the backend API.
    Handles all HTTP requests to the database service.
    """
    
    def __init__(self, base_url, api_key=None, timeout=10, max_retries=3):
        """
        Initialize the database client.
        
        Args:
            base_url (str): Base URL for the API
            api_key (str, optional): API key for authentication
            timeout (int, optional): Request timeout in seconds
            max_retries (int, optional): Maximum number of retry attempts for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _get_headers(self):
        """Get headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    def _handle_request(self, method, endpoint, **kwargs):
        """
        Generic method to handle all HTTP requests with retry logic.
        
        Args:
            method (str): HTTP method (get, post, put, delete)
            endpoint (str): API endpoint
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response: HTTP response object
        """
        url = f"{self.base_url}{endpoint}"
        
        # Add headers and timeout to kwargs
        if 'headers' not in kwargs:
            kwargs['headers'] = self._get_headers()
        
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
            
        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making {method.upper()} request to {url} (Attempt {attempt+1}/{self.max_retries})")
                response = requests.request(method, url, **kwargs)
                
                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")
                try:
                    response_data = response.json()
                    logger.debug(f"Response body: {json.dumps(response_data)[:500]}...")
                except (ValueError, TypeError):
                    logger.debug(f"Response body (not JSON): {response.text[:500]}...")
                
                # Handle common HTTP error codes
                if response.status_code >= 500:
                    logger.warning(f"Server error: {response.status_code} for {url}")
                    if attempt < self.max_retries - 1:
                        wait_time = 1 * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                return response
            
            except (ConnectionError, Timeout) as e:
                if attempt < self.max_retries - 1:
                    wait_time = 1 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request failed: {str(e)}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request to {url} failed after {self.max_retries} attempts: {str(e)}")
                    raise
            except RequestException as e:
                logger.error(f"Request error for {url}: {str(e)}")
                raise
    
    def get(self, endpoint, params=None):
        """Send GET request to the API."""
        return self._handle_request('get', endpoint, params=params)
    
    def post(self, endpoint, json=None, data=None):
        """Send POST request to the API."""
        return self._handle_request('post', endpoint, json=json, data=data)
    
    def put(self, endpoint, json=None, data=None):
        """Send PUT request to the API."""
        return self._handle_request('put', endpoint, json=json, data=data)
    
    def delete(self, endpoint):
        """Send DELETE request to the API."""
        return self._handle_request('delete', endpoint)
    
    # Additional convenience methods for specific API endpoints
    
    def get_servers(self, filters=None):
        """
        Get list of servers with optional filtering.
        
        Args:
            filters (dict, optional): Filter parameters
            
        Returns:
            list: List of server objects or empty list on error
        """
        try:
            response = self.get('/api/servers', params=filters)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get servers. Status: {response.status_code}")
                return []
        except Exception as e:
            logger.exception(f"Error fetching servers: {str(e)}")
            return []
    
    def get_server(self, server_id):
        """
        Get a single server by ID.
        
        Args:
            server_id: Server ID
            
        Returns:
            dict: Server object or None on error
        """
        try:
            response = self.get(f'/api/servers/{server_id}')
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get server {server_id}. Status: {response.status_code}")
                return None
        except Exception as e:
            logger.exception(f"Error fetching server {server_id}: {str(e)}")
            return None
    
    def get_geolocations(self):
        """
        Get list of all geolocations.
        
        Returns:
            list: List of geolocation objects or empty list on error
        """
        try:
            response = self.get('/api/geolocations')
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get geolocations. Status: {response.status_code}")
                return []
        except Exception as e:
            logger.exception(f"Error fetching geolocations: {str(e)}")
            return []
    
    def get_server_metrics(self, server_id, hours=24):
        """
        Get metrics for a server.
        
        Args:
            server_id: Server ID
            hours (int): Time period in hours
            
        Returns:
            dict: Metrics data or None on error
        """
        try:
            response = self.get(f'/api/servers/{server_id}/metrics', params={'hours': hours})
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get metrics for server {server_id}. Status: {response.status_code}")
                return None
        except Exception as e:
            logger.exception(f"Error fetching metrics for server {server_id}: {str(e)}")
            return None
    
    def authenticate_user(self, username, password):
        """
        Authenticate user credentials.
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            dict: User data or None if authentication fails
        """
        try:
            response = self.post('/api/auth/login', json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Authentication failed for user {username}. Status: {response.status_code}")
                return None
        except Exception as e:
            logger.exception(f"Error during authentication: {str(e)}")
            return None