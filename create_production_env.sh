#!/bin/bash

# Production Environment Setup Script
# Run this script on your production server to create the .env file

echo "============================================================"
echo "PRODUCTION ENVIRONMENT SETUP"
echo "============================================================"

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    # Backup existing .env
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✓ Backup created"
fi

# Create the production .env file
cat > .env << 'EOF'
# Production Environment Configuration
FLASK_ENV=production
DEBUG=false
USE_MYSQL=true

# Remote MySQL Database Configuration
DB_HOST=192.168.11.1
DB_PORT=3306
DB_USER=remote_user
DB_PASS=BuGr@d@N4@loB6!
DB_NAME_DEV=nutri_tracker_dev
DB_NAME_PROD=nutri_tracker_prod

# SQLite fallback (for migration source if needed)
DATABASE_PATH=database.db

# Production Application Settings
SECRET_KEY=CHANGE_THIS_IN_PRODUCTION_TO_RANDOM_STRING
SESSION_TIMEOUT=30

# Security Settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
EOF

echo "✓ Production .env file created"

# Set proper permissions
chmod 600 .env
echo "✓ File permissions set to 600 (owner read/write only)"

# Generate a random secret key
echo ""
echo "🔐 IMPORTANT: Generate a secure SECRET_KEY for production!"
echo "Run this command to generate a random secret key:"
echo ""
echo "python3 -c \"import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))\""
echo ""
echo "Then update your .env file with the generated key."

echo ""
echo "============================================================"
echo "✓ Production environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Update SECRET_KEY with a random value (see command above)"
echo "2. Review and adjust any other settings as needed"
echo "3. Test the database connection: python3 test_mysql_connection.py"
echo "4. Verify app configuration: python3 test_app_mysql.py"
echo "============================================================"
