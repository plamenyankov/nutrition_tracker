#!/bin/bash

echo "🧹 Cleaning up Docker resources on production server..."

# SSH into the production server and clean up Docker
ssh root@164.90.169.51 << 'EOF'
echo "Current disk usage:"
df -h

echo ""
echo "Docker system info before cleanup:"
docker system df

echo ""
echo "Stopping all running containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

echo ""
echo "Removing all containers..."
docker rm $(docker ps -aq) 2>/dev/null || true

echo ""
echo "Removing all unused images..."
docker image prune -af

echo ""
echo "Removing all unused volumes..."
docker volume prune -f

echo ""
echo "Removing all unused networks..."
docker network prune -f

echo ""
echo "Running comprehensive system cleanup..."
docker system prune -af --volumes

echo ""
echo "Docker system info after cleanup:"
docker system df

echo ""
echo "Current disk usage after cleanup:"
df -h

echo ""
echo "✅ Docker cleanup completed!"
EOF

echo "🚀 Ready to redeploy! Run ./deploy_to_digitalocean.sh again"
