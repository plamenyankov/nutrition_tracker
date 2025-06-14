#!/bin/bash

# Test different MySQL ports on the remote server
MYSQL_HOST="213.91.178.104"
COMMON_PORTS=(3306 3307 33060 33061 3308 3309)

echo "Testing MySQL connectivity on different ports..."
echo "Host: $MYSQL_HOST"
echo "=============================================="

for port in "${COMMON_PORTS[@]}"; do
    echo -n "Testing port $port... "
    if timeout 5 nc -zv $MYSQL_HOST $port 2>/dev/null; then
        echo "✓ OPEN"
    else
        echo "✗ Closed/Filtered"
    fi
done

echo ""
echo "Testing from DigitalOcean server..."
echo "=============================================="

for port in "${COMMON_PORTS[@]}"; do
    echo -n "Testing port $port from DigitalOcean... "
    if ssh root@164.90.169.51 "timeout 5 nc -zv $MYSQL_HOST $port" 2>/dev/null; then
        echo "✓ OPEN"
    else
        echo "✗ Closed/Filtered"
    fi
done
