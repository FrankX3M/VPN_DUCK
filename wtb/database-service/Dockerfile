FROM python:3.9-slim

WORKDIR /app

# Install PostgreSQL client libraries
RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    apt-get clean

# First install specific versions of Werkzeug and Flask
RUN pip install --no-cache-dir werkzeug==2.0.3
RUN pip install --no-cache-dir flask==2.0.1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data

CMD ["python", "db_manager.py"]