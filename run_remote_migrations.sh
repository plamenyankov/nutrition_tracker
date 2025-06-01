#!/bin/bash

# Script to run migrations on the remote DigitalOcean server

# Configuration
DROPLET_IP="164.90.169.51"
DROPLET_USER="root"
CONTAINER_NAME="nutrition-tracker"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running migrations on DigitalOcean server...${NC}"

# Command to run migrations inside the Docker container
MIGRATION_COMMAND="docker exec ${CONTAINER_NAME} python run_all_migrations.py"

# Execute via SSH
ssh -o StrictHostKeyChecking=no ${DROPLET_USER}@${DROPLET_IP} "$MIGRATION_COMMAND"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Migrations completed successfully on production!${NC}"
else
    echo -e "${RED}❌ Migration failed on production!${NC}"
    exit 1
fi
