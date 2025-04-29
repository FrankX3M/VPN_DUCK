# Add this code to Dockerfile
# This builds a Docker container for the VPN Duck Admin Panel

FROM python:3.9-slim

WORKDIR /app

# Install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV ADMIN_USERNAME=admin
ENV ADMIN_PASSWORD=password
ENV ADMIN_SECRET_KEY=change_this_in_production
ENV DATABASE_SERVICE_URL=http://database-service:5002
ENV WIREGUARD_SERVICE_URL=http://wireguard-proxy:5001

# Expose the port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]