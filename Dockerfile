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
ENV USE_MYSQL=true
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
    python test_current_db.py || {\n\
        echo "MySQL connection failed! Check your environment variables."\n\
        echo "DB_HOST: $DB_HOST"\n\
        echo "DB_PORT: $DB_PORT"\n\
        echo "DB_USER: $DB_USER"\n\
        echo "Current DB: $CURRENT_DB_NAME"\n\
        exit 1\n\
    }\n\
    echo "MySQL connection successful!"\n\
    \n\
    # Always run schema migrations (they are idempotent)\n\
    echo "Running schema migrations..."\n\
    python run_schema_migrations.py || {\n\
        echo "Schema migrations failed!"\n\
        exit 1\n\
    }\n\
    echo "Schema migrations completed!"\n\
    \n\
    # Check if data migration is needed\n\
    if [ "$RUN_MIGRATION" = "true" ]; then\n\
        echo "Running data migration..."\n\
        python migrate_to_mysql.py --env production || {\n\
            echo "Data migration failed!"\n\
            exit 1\n\
        }\n\
        echo "Data migration completed successfully!"\n\
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
fi\n\
\n\
echo "Starting application..."\n\
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Run with the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
