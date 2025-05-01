# Updated Dockerfile with better static file handling
FROM python:3.9-slim

WORKDIR /app

# Install required system packages for image processing libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create static directory with proper permissions
RUN mkdir -p /app/static/css /app/static/js /app/static/img \
    && chmod -R 755 /app/static

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    USE_MOCK_DATA=true \
    SECRET_KEY=change_this_in_production

# Make sure static files have correct permissions
RUN chmod -R 755 /app/static

# Expose port
EXPOSE 5000

# Use a custom entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the application with Gunicorn with appropriate timeout settings
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "2", "app:app"]