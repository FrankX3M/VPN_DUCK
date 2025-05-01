#!/bin/bash
set -e

# Ensure static directories exist
mkdir -p /app/static/css /app/static/js /app/static/img

# Check if the CSS files exist, if not create a minimal CSS file to prevent errors
if [ ! -f /app/static/css/bootstrap.min.css ]; then
    echo "/* Placeholder CSS file */" > /app/static/css/bootstrap.min.css
    echo "Creating placeholder CSS files..."
fi

if [ ! -f /app/static/css/bootstrap-icons.css ]; then
    echo "/* Placeholder icons CSS file */" > /app/static/css/bootstrap-icons.css
fi

if [ ! -f /app/static/css/custom.css ]; then
    echo "/* Custom CSS file */" > /app/static/css/custom.css
fi

# Check if JS files exist, if not create placeholder files
if [ ! -f /app/static/js/bootstrap.bundle.min.js ]; then
    echo "// Placeholder JS file" > /app/static/js/bootstrap.bundle.min.js
    echo "Creating placeholder JS files..."
fi

if [ ! -f /app/static/js/minimal.js ]; then
    echo "// Minimal JS file" > /app/static/js/minimal.js
fi

# Create placeholder favicon if it doesn't exist
if [ ! -f /app/static/img/favicon.ico ]; then
    echo "Creating placeholder favicon..."
    touch /app/static/img/favicon.ico
fi

# Create placeholder logo if it doesn't exist
if [ ! -f /app/static/img/logo.png ]; then
    echo "Creating placeholder logo..."
    touch /app/static/img/logo.png
fi

# Set proper permissions on static files
chmod -R 755 /app/static

echo "Starting VPN Duck Admin Panel..."
exec "$@"