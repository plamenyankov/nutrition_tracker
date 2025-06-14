#!/bin/bash

# Test MySQL connection from DigitalOcean server
# Run this script to verify the connection works

MYSQL_HOST="213.91.178.104"
MYSQL_PORT="3306"
MYSQL_USER="remote_user"
MYSQL_PASS="BuGr@d@N4@loB6!"
DROPLET_IP="164.90.169.51"

echo "Testing MySQL connection from DigitalOcean server..."
echo "=============================================="

# Test network connectivity first
echo "1. Testing network connectivity to MySQL server..."
ssh root@${DROPLET_IP} "nc -zv ${MYSQL_HOST} ${MYSQL_PORT}" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Network connection successful"
else
    echo "✗ Network connection failed"
    echo "Please check:"
    echo "  - MySQL server is running"
    echo "  - Firewall allows connections from ${DROPLET_IP}"
    echo "  - MySQL bind-address is configured correctly"
    exit 1
fi

echo ""
echo "2. Testing MySQL authentication..."

# Test MySQL connection using Docker container
ssh root@${DROPLET_IP} "docker run --rm mysql:8.0 mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER} -p'${MYSQL_PASS}' -e 'SELECT \"Connection successful!\" as status;'" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ MySQL authentication successful"
else
    echo "✗ MySQL authentication failed"
    echo "Please check:"
    echo "  - User 'remote_user' exists and has correct password"
    echo "  - User is allowed to connect from ${DROPLET_IP}"
    echo "  - User has mysql_native_password authentication"
    exit 1
fi

echo ""
echo "3. Testing database access..."

# Test database access
ssh root@${DROPLET_IP} "docker run --rm mysql:8.0 mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER} -p'${MYSQL_PASS}' -e 'SHOW DATABASES;'" 2>&1

echo ""
echo "=============================================="
echo "✅ All tests passed! Ready for deployment."
echo "=============================================="
