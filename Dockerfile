FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for MySQL
RUN apt-get update && apt-get install -y \
    default-mysql-client \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database volume
RUN mkdir -p /app/data

# Set default environment variables
ENV DATABASE_PATH=/app/data/database.db
ENV USE_MYSQL=false
ENV FLASK_ENV=production
ENV DEBUG=false

# Expose port 5000
EXPOSE 5000

# Create an entrypoint script that supports both SQLite and MySQL
RUN echo '#!/bin/sh\n\
echo "Starting Nutrition Tracker..."\n\
echo "USE_MYSQL: $USE_MYSQL"\n\
echo "DB_HOST: $DB_HOST"\n\
\n\
# Check if we should use MySQL\n\
if [ "$USE_MYSQL" = "true" ]; then\n\
    echo "Using MySQL database"\n\
    echo "Testing MySQL connection..."\n\
    python test_mysql_connection.py || {\n\
        echo "MySQL connection failed! Check your environment variables."\n\
        exit 1\n\
    }\n\
    echo "MySQL connection successful!"\n\
    \n\
    # Check if migration is needed\n\
    if [ "$RUN_MIGRATION" = "true" ]; then\n\
        echo "Running MySQL migration..."\n\
        python migrate_to_mysql.py --full-migration || {\n\
            echo "Migration failed!"\n\
            exit 1\n\
        }\n\
        echo "Migration completed successfully!"\n\
    fi\n\
else\n\
    echo "Using SQLite database"\n\
    python init_db.py\n\
    python run_all_migrations.py\n\
fi\n\
\n\
echo "Starting application..."\n\
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Run with the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
