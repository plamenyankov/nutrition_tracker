#!/bin/bash

# DigitalOcean Deployment Script using rsync
# This script copies files directly without requiring git

# Configuration
DROPLET_IP="164.90.169.51"
DROPLET_USER="root"
REMOTE_APP_DIR="/root/nutrition_tracker"
LOCAL_APP_DIR="."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment to DigitalOcean using rsync...${NC}"

# Step 1: Create remote directory if it doesn't exist
echo -e "${YELLOW}Ensuring remote directory exists...${NC}"
ssh ${DROPLET_USER}@${DROPLET_IP} "mkdir -p ${REMOTE_APP_DIR}"

# Step 2: Sync files using rsync
echo -e "${YELLOW}Syncing files to DigitalOcean...${NC}"
rsync -avz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.DS_Store' \
    --exclude='*.ipynb' \
    --exclude='venv/' \
    --exclude='env/' \
    --exclude='.env.local' \
    --exclude='*.log' \
    --exclude='*.sqlite' \
    --exclude='database.db' \
    --exclude='cookies.txt' \
    --exclude='deploy_*.sh' \
    --exclude='DEPLOYMENT_*.md' \
    ${LOCAL_APP_DIR}/ ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_APP_DIR}/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ File sync failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Files synced successfully!${NC}"

# Step 3: Deploy on the droplet
echo -e "${YELLOW}Deploying application...${NC}"

ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
cd /root/nutrition_tracker

# Stop and remove existing container
echo "Stopping existing container..."
docker stop nutrition-tracker 2>/dev/null || true
docker rm nutrition-tracker 2>/dev/null || true

# Remove old image to ensure fresh build
echo "Removing old Docker image..."
docker rmi nutrition-tracker-app 2>/dev/null || true

# Build new image
echo "Building new Docker image..."
docker build -t nutrition-tracker-app .

# Get OPENAI_API_KEY from existing container or environment
if [ -z "$OPENAI_API_KEY" ]; then
    # Try to get from .env file if exists
    if [ -f .env ]; then
        export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Run new container
echo "Starting new container..."
docker run -d \
    --name nutrition-tracker \
    -p 80:5000 \
    -e SECRET_KEY="$(openssl rand -hex 32)" \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e DEBUG=False \
    --restart unless-stopped \
    nutrition-tracker-app

# Check if container is running
sleep 3
if docker ps | grep -q nutrition-tracker; then
    echo "✅ Deployment successful! Container is running."
    docker logs --tail 20 nutrition-tracker
else
    echo "❌ Deployment failed! Container is not running."
    docker logs nutrition-tracker
    exit 1
fi

echo "Deployment completed successfully!"
ENDSSH

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo -e "${GREEN}Your app should be available at: http://${DROPLET_IP}${NC}"
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    exit 1
fi
