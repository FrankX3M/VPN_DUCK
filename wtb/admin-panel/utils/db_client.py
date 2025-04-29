import requests
import logging
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

class DatabaseClient:
    """
    Client for interacting with the backend API.
    Handles all HTTP requests to the database service.
    """
    
    def __init__(self, base_url, api_key=None, timeout=10):
        """
        Initialize the database client.
        
        Args:
            base_url (str): Base URL for the API
            api_key (str, optional): API key for authentication
            timeout (int, optional): Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
    
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
        Generic method to handle all HTTP requests.
        
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
            
        try:
            logger.debug(f"Making {method.upper()} request to {url}")
            response = requests.request(method, url, **kwargs)
            logger.debug(f"Response status: {response.status_code}")
            
            return response
        
        except Timeout:
            logger.error(f"Request to {url} timed out after {self.timeout} seconds")
            raise
        
        except RequestException as e:
            logger.error(f"Request to {url} failed: {str(e)}")
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