FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database volume
RUN mkdir -p /app/data

# Initialize database on startup
ENV DATABASE_PATH=/app/data/database.db

# Expose port 5000
EXPOSE 5000

# Create an entrypoint script
RUN echo '#!/bin/sh\n\
python init_db.py\n\
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Run with the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
