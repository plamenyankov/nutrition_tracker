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
echo "FLASK_ENV: $FLASK_ENV"\n\
echo "USE_MYSQL: $USE_MYSQL"\n\
echo "DB_HOST: $DB_HOST"\n\
\n\
# Check if we should use MySQL\n\
if [ "$USE_MYSQL" = "true" ]; then\n\
    echo "Using MySQL database"\n\
    \n\
    # Determine which database to use based on environment\n\
    if [ "$FLASK_ENV" = "production" ]; then\n\
        export CURRENT_DB_NAME="$DB_NAME_PROD"\n\
        echo "Production environment - using database: $DB_NAME_PROD"\n\
    else\n\
        export CURRENT_DB_NAME="$DB_NAME_DEV"\n\
        echo "Development environment - using database: $DB_NAME_DEV"\n\
    fi\n\
    \n\
    echo "Testing MySQL connection to $DB_HOST:$DB_PORT..."\n\
    python test_mysql_connection.py || {\n\
        echo "MySQL connection failed! Check your environment variables."\n\
        echo "DB_HOST: $DB_HOST"\n\
        echo "DB_PORT: $DB_PORT"\n\
        echo "DB_USER: $DB_USER"\n\
        echo "Current DB: $CURRENT_DB_NAME"\n\
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
    \n\
    # Verify app database configuration\n\
    echo "Verifying app database configuration..."\n\
    python test_app_mysql.py || {\n\
        echo "App database configuration verification failed!"\n\
        exit 1\n\
    }\n\
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
