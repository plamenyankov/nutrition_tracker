#!/bin/bash

# DigitalOcean Deployment Script for Nutrition Tracker

# Configuration
DROPLET_IP="164.90.169.51"
DROPLET_USER="root"
APP_DIR="/root/nutrition_tracker"
CONTAINER_NAME="nutrition-tracker"

# Docker Hub configuration - UPDATE THESE WITH YOUR DOCKER HUB USERNAME
DOCKER_USERNAME="plamenyankov"  # Replace with your Docker Hub username
DOCKER_IMAGE_NAME="nutrition-tracker"
DOCKER_TAG="latest"
DOCKER_FULL_NAME="${DOCKER_USERNAME}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"

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

# Step 3: Build Docker image locally
echo -e "${GREEN}Building Docker image locally...${NC}"
docker build -t ${DOCKER_FULL_NAME} .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi

# Step 4: Push to Docker Hub
echo -e "${YELLOW}Pushing image to Docker Hub...${NC}"
echo -e "${YELLOW}Please ensure you're logged in to Docker Hub (docker login)${NC}"

docker push ${DOCKER_FULL_NAME}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker push failed! Please run 'docker login' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image pushed to Docker Hub successfully!${NC}"

# Step 5: Deploy to DigitalOcean
echo -e "${GREEN}Deploying to DigitalOcean droplet...${NC}"

# Create deployment commands
DEPLOY_COMMANDS=$(cat <<EOF
# Stop and remove existing container
echo "Stopping existing container..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Pull the latest image from Docker Hub
echo "Pulling latest image from Docker Hub..."
docker pull ${DOCKER_FULL_NAME}

# Get OPENAI_API_KEY from environment or .env file
if [ -z "\$OPENAI_API_KEY" ]; then
    # Try to get from existing container
    OPENAI_API_KEY=\$(docker inspect ${CONTAINER_NAME} 2>/dev/null | grep OPENAI_API_KEY | head -1 | cut -d'"' -f4)

    # If still empty, try from .env file
    if [ -z "\$OPENAI_API_KEY" ] && [ -f /root/nutrition_tracker/.env ]; then
        export OPENAI_API_KEY=\$(grep OPENAI_API_KEY /root/nutrition_tracker/.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Run new container with environment variables
echo "Starting new container..."
docker run -d \\
    --name ${CONTAINER_NAME} \\
    -p 80:5000 \\
    -e SECRET_KEY="\$(openssl rand -hex 32)" \\
    -e OPENAI_API_KEY="\$OPENAI_API_KEY" \\
    -e DEBUG=False \\
    --restart unless-stopped \\
    ${DOCKER_FULL_NAME}

# Check if container is running
sleep 3
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "✅ Deployment successful! Container is running."
    docker logs --tail 20 ${CONTAINER_NAME}
else
    echo "❌ Deployment failed! Container is not running."
    docker logs ${CONTAINER_NAME}
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
