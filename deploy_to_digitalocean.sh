#!/bin/bash

# DigitalOcean Deployment Script for Nutrition Tracker

# Configuration
DROPLET_IP="164.90.169.51"
DROPLET_USER="root"
APP_DIR="/root/nutrition_tracker"
CONTAINER_NAME="nutrition-tracker"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment to DigitalOcean...${NC}"

# Step 1: Check for uncommitted changes
echo -e "${YELLOW}Checking for uncommitted changes...${NC}"
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}Found uncommitted changes. Committing...${NC}"
    git add -A
    echo "Enter commit message (or press Enter for default):"
    read commit_message
    if [ -z "$commit_message" ]; then
        commit_message="Update: Deploy latest changes to production"
    fi
    git commit -m "$commit_message"
else
    echo -e "${GREEN}No uncommitted changes found.${NC}"
fi

# Step 2: Push to remote repository (if exists)
echo -e "${YELLOW}Checking for remote repository...${NC}"
if git remote -v | grep -q origin; then
    echo -e "${YELLOW}Pushing to remote repository...${NC}"
    git push origin main || git push origin master
else
    echo -e "${YELLOW}No remote repository found. Skipping push.${NC}"
fi

# Step 3: Deploy to DigitalOcean
echo -e "${GREEN}Deploying to DigitalOcean droplet...${NC}"

# Create deployment commands
DEPLOY_COMMANDS=$(cat <<'EOF'
cd /root/nutrition_tracker

# Pull latest changes if git repo exists
if [ -d .git ]; then
    echo "Pulling latest changes from git..."
    git pull origin main || git pull origin master || echo "Git pull skipped"
fi

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

# Run new container with environment variables
echo "Starting new container..."
docker run -d \
    --name nutrition-tracker \
    -p 80:8000 \
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
EOF
)

# Execute deployment via SSH
ssh -o StrictHostKeyChecking=no ${DROPLET_USER}@${DROPLET_IP} "$DEPLOY_COMMANDS"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo -e "${GREEN}Your app should be available at: http://${DROPLET_IP}${NC}"
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    exit 1
fi
