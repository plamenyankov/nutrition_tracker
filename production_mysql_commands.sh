#!/bin/bash

# Production MySQL Management Commands
# Use these commands to manually manage MySQL migration on your DigitalOcean server

DROPLET_IP="164.90.169.51"
DROPLET_USER="root"
CONTAINER_NAME="nutrition-tracker"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Production MySQL Management Commands${NC}"
echo "=================================================="

echo -e "${YELLOW}1. Connect to your DigitalOcean server:${NC}"
echo "ssh ${DROPLET_USER}@${DROPLET_IP}"

echo -e "\n${YELLOW}2. Check if container is running:${NC}"
echo "docker ps | grep ${CONTAINER_NAME}"

echo -e "\n${YELLOW}3. View container logs:${NC}"
echo "docker logs ${CONTAINER_NAME}"
echo "docker logs --tail 50 ${CONTAINER_NAME}"

echo -e "\n${YELLOW}4. Access container shell to run migration commands:${NC}"
echo "docker exec -it ${CONTAINER_NAME} /bin/bash"

echo -e "\n${YELLOW}5. Inside the container, you can run:${NC}"
echo "# Test MySQL connection"
echo "python test_mysql_connection.py"
echo ""
echo "# Check what database the app is using"
echo "python test_app_mysql.py"
echo ""
echo "# Run full migration from SQLite to MySQL"
echo "python migrate_to_mysql.py --full-migration"
echo ""
echo "# Run schema-only migration"
echo "python migrate_to_mysql.py --schema-only"
echo ""
echo "# Run data-only migration"
echo "python migrate_to_mysql.py --data-only"

echo -e "\n${YELLOW}6. Environment variables in container:${NC}"
echo "docker exec ${CONTAINER_NAME} env | grep -E '(MYSQL|DB_|USE_MYSQL)'"

echo -e "\n${YELLOW}7. Copy files from container to host (if needed):${NC}"
echo "docker cp ${CONTAINER_NAME}:/app/test_mysql_connection.py ."
echo "docker cp ${CONTAINER_NAME}:/app/migrate_to_mysql.py ."

echo -e "\n${YELLOW}8. Restart container with MySQL:${NC}"
echo "docker stop ${CONTAINER_NAME}"
echo "docker run -d \\"
echo "    --name ${CONTAINER_NAME} \\"
echo "    -p 80:5000 \\"
echo "    -v /root/nutrition_tracker_data:/app/data \\"
echo "    -e SECRET_KEY=\"\$(openssl rand -hex 32)\" \\"
echo "    -e USE_MYSQL=true \\"
echo "    -e FLASK_ENV=production \\"
echo "    -e DEBUG=false \\"
echo "    -e DB_HOST=192.168.11.1 \\"
echo "    -e DB_PORT=3306 \\"
echo "    -e DB_USER=remote_user \\"
echo "    -e DB_PASS=BuGr@d@N4@loB6! \\"
echo "    -e DB_NAME_DEV=nutri_tracker_dev \\"
echo "    -e DB_NAME_PROD=nutri_tracker_prod \\"
echo "    -e RUN_MIGRATION=true \\"
echo "    --restart unless-stopped \\"
echo "    plamenyankov1/nutrition-tracker:latest"

echo -e "\n${YELLOW}9. Quick migration command (run on DigitalOcean server):${NC}"
echo "docker exec ${CONTAINER_NAME} python migrate_to_mysql.py --full-migration"

echo -e "\n${GREEN}=================================================="
echo "All migration files are included in the Docker image!"
echo "You can access them inside the running container."
echo "==================================================${NC}"
