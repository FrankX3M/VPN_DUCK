#!/bin/bash
set -e

# Ensure static directories exist
mkdir -p /app/static/css /app/static/js /app/static/img

# Check if the CSS files exist, if not create a minimal CSS file to prevent errors
if [ ! -f /app/static/css/bootstrap.min.css ]; then
    echo "/* Placeholder CSS file - minimum content to prevent empty file errors */" > /app/static/css/bootstrap.min.css
    echo "body { font-family: Arial, sans-serif; }" >> /app/static/css/bootstrap.min.css
    echo "Creating placeholder CSS files..."
fi

if [ ! -f /app/static/css/bootstrap-icons.css ]; then
    echo "/* Placeholder icons CSS file - minimum content to prevent empty file errors */" > /app/static/css/bootstrap-icons.css
    echo ".bi { display: inline-block; }" >> /app/static/css/bootstrap-icons.css
fi

if [ ! -f /app/static/css/custom.css ]; then
    echo "/* Custom CSS file - minimum content to prevent empty file errors */" > /app/static/css/custom.css
    echo ".custom { color: #333; }" >> /app/static/css/custom.css
fi

# Check if JS files exist, if not create placeholder files
if [ ! -f /app/static/js/bootstrap.bundle.min.js ]; then
    echo "// Placeholder JS file - minimum content to prevent empty file errors" > /app/static/js/bootstrap.bundle.min.js
    echo "console.log('Bootstrap bundle placeholder');" >> /app/static/js/bootstrap.bundle.min.js
    echo "Creating placeholder JS files..."
fi

if [ ! -f /app/static/js/minimal.js ]; then
    echo "// Minimal JS file - minimum content to prevent empty file errors" > /app/static/js/minimal.js
    echo "console.log('Minimal JS loaded');" >> /app/static/js/minimal.js
fi

# Create placeholder favicon if it doesn't exist
if [ ! -f /app/static/img/favicon.ico ]; then
    echo "Creating placeholder favicon..."
    # Create a minimal 1x1 ICO file (not empty)
    printf "\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x30\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF\xFF\x00" > /app/static/img/favicon.ico
fi

# Create placeholder logo if it doesn't exist
if [ ! -f /app/static/img/logo.png ]; then
    echo "Creating placeholder logo..."
    # Create a minimal 1x1 PNG file (not empty)
    printf "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A\x00\x00\x00\x0D\x49\x48\x44\x52\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90\x77\x53\xDE\x00\x00\x00\x0C\x49\x44\x41\x54\x08\xD7\x63\xF8\xFF\xFF\x3F\x00\x05\xFE\x02\xFE\xDC\xCC\x59\xE7\x00\x00\x00\x00\x49\x45\x4E\x44\xAE\x42\x60\x82" > /app/static/img/logo.png
fi

# Set proper permissions on static files
chmod -R 755 /app/static

echo "Starting VPN Duck Admin Panel..."
exec "$@"