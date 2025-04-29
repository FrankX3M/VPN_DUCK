# Add this code to api_client.py
# This should be the entire content of the file

import requests
import time
import logging
import json

logger = logging.getLogger(__name__)

class ApiClient:
    """Client for interacting with API services"""
    def __init__(self, base_url, timeout=10, max_retries=3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _make_request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        logger.info(f"API request: {method} {url}")
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                
                # Log the response
                logger.info(f"Response status: {response.status_code}")
                try:
                    response_data = response.json()
                    logger.debug(f"Response body: {json.dumps(response_data)[:500]}")
                except:
                    logger.debug(f"Response body (not JSON): {response.text[:500]}")
                
                return response
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to complete request after {self.max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed: {str(e)}")
                time.sleep(1 * (attempt + 1))  # Increase wait time with each retry
    
    def get(self, endpoint, params=None):
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint, json=None, data=None):
        return self._make_request('POST', endpoint, json=json, data=data)
    
    def put(self, endpoint, json=None, data=None):
        return self._make_request('PUT', endpoint, json=json, data=data)
    
    def delete(self, endpoint):
        return self._make_request('DELETE', endpoint)