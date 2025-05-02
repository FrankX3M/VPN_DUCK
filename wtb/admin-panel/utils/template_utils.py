import os
import logging

logger = logging.getLogger(__name__)

def create_error_templates():
    """Creates error template pages if they don't exist."""
    # Check directory and create if necessary
    templates_dir = 'templates'
    errors_dir = os.path.join(templates_dir, 'errors')
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    if not os.path.exists(errors_dir):
        os.makedirs(errors_dir)
    
    # Create 404.html template
    error_404_path = os.path.join(errors_dir, '404.html')
    if not os.path.exists(error_404_path):
        with open(error_404_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            padding-top: 50px; 
            padding-bottom: 50px; 
            background-color: #f8f9fa;
            text-align: center;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error-code {
            font-size: 120px;
            color: #dc3545;
            margin-bottom: 0;
        }
        .error-message {
            font-size: 24px;
            margin-bottom: 20px;
            color: #343a40;
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }
        .btn:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">404</h1>
        <p class="error-message">Page Not Found</p>
        <p>The page you are looking for does not exist or has been moved.</p>
        <a href="/" class="btn">Return to Home</a>
    </div>
</body>
</html>
''')
    
    # Create 500.html template
    error_500_path = os.path.join(errors_dir, '500.html')
    if not os.path.exists(error_500_path):
        with open(error_500_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>500 - Server Error</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            padding-top: 50px; 
            padding-bottom: 50px; 
            background-color: #f8f9fa;
            text-align: center;
        }
        .error-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error-code {
            font-size: 120px;
            color: #dc3545;
            margin-bottom: 0;
        }
        .error-message {
            font-size: 24px;
            margin-bottom: 20px;
            color: #343a40;
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }
        .btn:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">500</h1>
        <p class="error-message">Server Error</p>
        <p>Sorry, something went wrong on our end. Please try again later.</p>
        <a href="/" class="btn">Return to Home</a>
    </div>
</body>
</html>
''')

def create_favicon():
    """Creates a simple favicon.ico if it doesn't exist."""
    favicon_dir = os.path.join('static', 'img')
    os.makedirs(favicon_dir, exist_ok=True)
    
    favicon_path = os.path.join(favicon_dir, 'favicon.ico')
    if not os.path.exists(favicon_path):
        try:
            # Create minimal ico file
            with open(favicon_path, 'wb') as f:
                # Minimal ICO file structure
                f.write(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        except Exception as e:
            logger.error(f"Error creating favicon: {str(e)}")

def download_bootstrap_resources(app_root_path):
    """Downloads Bootstrap, jQuery and Chart.js for offline use."""
    import json
    import requests
    from datetime import datetime
    
    # Create directories
    static_dir = os.path.join(app_root_path, 'static')
    css_dir = os.path.join(static_dir, 'css')
    js_dir = os.path.join(static_dir, 'js')
    
    for directory in [css_dir, js_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # List of URLs to download
    resources = [
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
            'path': os.path.join(css_dir, 'bootstrap.min.css')
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
            'path': os.path.join(js_dir, 'bootstrap.bundle.min.js')
        },
        {
            'url': 'https://code.jquery.com/jquery-3.6.0.min.js',
            'path': os.path.join(js_dir, 'jquery.min.js')
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js',
            'path': os.path.join(js_dir, 'chart.min.js')
        }
    ]
    
    downloaded_files = []
    failed_files = []
    
    # Download each resource
    for resource in resources:
        try:
            logger.info(f"Downloading {resource['url']}")
            response = requests.get(resource['url'], timeout=30)
            
            if response.status_code == 200:
                with open(resource['path'], 'wb') as f:
                    f.write(response.content)
                downloaded_files.append(os.path.basename(resource['path']))
            else:
                logger.error(f"Error downloading {resource['url']}: {response.status_code}")
                failed_files.append(os.path.basename(resource['path']))
        except Exception as e:
            logger.exception(f"Error downloading {resource['url']}: {str(e)}")
            failed_files.append(os.path.basename(resource['path']))
    
    # Create configuration file for using local resources
    config_path = os.path.join(app_root_path, 'config', 'local_resources.json')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump({
            'use_local_resources': True,
            'bootstrap_css': '/static/css/bootstrap.min.css',
            'bootstrap_js': '/static/js/bootstrap.bundle.min.js',
            'jquery_js': '/static/js/jquery.min.js',
            'chart_js': '/static/js/chart.min.js',
            'downloaded_at': datetime.now().isoformat()
        }, f, indent=4)
    
    logger.info("Local library copies successfully downloaded")
    
    return {
        'downloaded': downloaded_files,
        'failed': failed_files
    }