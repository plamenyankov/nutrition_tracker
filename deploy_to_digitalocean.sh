#!/bin/bash

# DigitalOcean Deployment Script for Nutrition Tracker

# Configuration
DROPLET_IP="164.90.169.51"
DROPLET_USER="root"
APP_DIR="/root/nutrition_tracker"
CONTAINER_NAME="nutrition-tracker"

# Docker Hub configuration - UPDATE THESE WITH YOUR DOCKER HUB USERNAME
DOCKER_USERNAME="plamenyankov1"  # Replace with your Docker Hub username
DOCKER_IMAGE_NAME="nutrition-tracker"
DOCKER_TAG="latest"
DOCKER_FULL_NAME="${DOCKER_USERNAME}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"

# DigitalOcean Managed MySQL Configuration
# IMPORTANT: All secrets must be provided via environment variables, not hardcoded
# Load from environment variables (set in CI/CD or manually before running script)
MYSQL_HOST="${DO_DB_HOST:-db-mysql-fra1-07479-do-user-23762110-0.e.db.ondigitalocean.com}"
MYSQL_PORT="${DO_DB_PORT:-25060}"
MYSQL_USER="${DO_DB_USER:-nutrition_user}"
# Password must be provided via DO_DB_PASS environment variable
MYSQL_PASS="${DO_DB_PASS}"
MYSQL_DB_PROD="${DB_NAME_PROD:-nutri_tracker_prod}"
MYSQL_DB_DEV="${DB_NAME_DEV:-nutri_tracker_dev}"

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

# Step 5: Ask user about database choice
echo -e "${YELLOW}Choose database option:${NC}"
echo "1) SQLite (default, data stored in volume)"
echo "2) MySQL Production (remote database at ${MYSQL_HOST})"
echo "3) MySQL Production with migration (migrate from SQLite to MySQL)"
read -p "Enter choice (1-3) [2]: " db_choice
db_choice=${db_choice:-2}

# Step 6: Deploy to DigitalOcean
echo -e "${GREEN}Deploying to DigitalOcean droplet...${NC}"

# Create deployment commands based on database choice
if [ "$db_choice" = "2" ] || [ "$db_choice" = "3" ]; then
    # MySQL deployment
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
    # Try to get from existing .env file
    if [ -f /root/nutrition_tracker/.env ]; then
        export OPENAI_API_KEY=\$(grep OPENAI_API_KEY /root/nutrition_tracker/.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Set migration flag
RUN_MIGRATION="false"
if [ "$db_choice" = "3" ]; then
    RUN_MIGRATION="true"
    echo "Migration will be performed on startup..."
fi

# Run new container with MySQL Production configuration
echo "Starting new container with MySQL Production..."
docker run -d \\
    --name ${CONTAINER_NAME} \\
    -p 80:5000 \\
    -v /root/nutrition_tracker_data:/app/data \\
    -e SECRET_KEY="\$(openssl rand -hex 32)" \\
    -e OPENAI_API_KEY="\$OPENAI_API_KEY" \\
    -e USE_MYSQL=true \\
    -e FLASK_ENV=production \\
    -e DEBUG=false \\
    -e DB_HOST=${MYSQL_HOST} \\
    -e DB_PORT=${MYSQL_PORT} \\
    -e DB_USER=${MYSQL_USER} \\
    -e DB_PASS=${MYSQL_PASS} \\
    -e DB_NAME_DEV=${MYSQL_DB_DEV} \\
    -e DB_NAME_PROD=${MYSQL_DB_PROD} \\
    -e RUN_MIGRATION=\$RUN_MIGRATION \\
    --restart unless-stopped \\
    ${DOCKER_FULL_NAME}

# Check if container is running
sleep 10
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "✅ Deployment successful! Container is running with MySQL Production."
    echo "Container logs:"
    docker logs --tail 50 ${CONTAINER_NAME}
else
    echo "❌ Deployment failed! Container is not running."
    echo "Container logs:"
    docker logs ${CONTAINER_NAME}
    exit 1
fi

echo "MySQL Production deployment completed successfully!"
EOF
)
else
    # SQLite deployment (original)
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
    if [ -f /root/nutrition_tracker/.env ]; then
        export OPENAI_API_KEY=\$(grep OPENAI_API_KEY /root/nutrition_tracker/.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Run new container with SQLite configuration
echo "Starting new container with SQLite..."
docker run -d \\
    --name ${CONTAINER_NAME} \\
    -p 80:5000 \\
    -v /root/nutrition_tracker_data:/app/data \\
    -e SECRET_KEY="\$(openssl rand -hex 32)" \\
    -e OPENAI_API_KEY="\$OPENAI_API_KEY" \\
    -e DATABASE_PATH="/app/data/database.db" \\
    -e USE_MYSQL=false \\
    -e DEBUG=false \\
    --restart unless-stopped \\
    ${DOCKER_FULL_NAME}

# Check if container is running
sleep 3
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "✅ Deployment successful! Container is running with SQLite."
    docker logs --tail 20 ${CONTAINER_NAME}
else
    echo "❌ Deployment failed! Container is not running."
    docker logs ${CONTAINER_NAME}
    exit 1
fi

echo "SQLite deployment completed successfully!"
EOF
)
fi

# Execute deployment via SSH
ssh -o StrictHostKeyChecking=no ${DROPLET_USER}@${DROPLET_IP} "$DEPLOY_COMMANDS"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo -e "${GREEN}Your app should be available at: http://${DROPLET_IP}${NC}"

    if [ "$db_choice" = "2" ] || [ "$db_choice" = "3" ]; then
        echo -e "${GREEN}Database: MySQL Production at ${MYSQL_HOST}:${MYSQL_PORT}${NC}"
        echo -e "${GREEN}Database Name: ${MYSQL_DB_PROD}${NC}"
        echo -e "${YELLOW}You can verify the database connection by checking container logs:${NC}"
        echo -e "${YELLOW}ssh ${DROPLET_USER}@${DROPLET_IP} 'docker logs ${CONTAINER_NAME}'${NC}"
    else
        echo -e "${GREEN}Database: SQLite (persistent volume)${NC}"
    fi
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    exit 1
fi
