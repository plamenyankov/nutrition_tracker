# Deployment Guide for Nutrition Tracker

This guide explains how to deploy your Nutrition Tracker application to DigitalOcean.

## Prerequisites

1. SSH access to your DigitalOcean droplet (IP: 164.90.169.51)
2. Docker installed on the droplet
3. OPENAI_API_KEY set up on the droplet

## Deployment Scripts

We provide two deployment scripts:

### 1. Git-based Deployment (`deploy_to_digitalocean.sh`)

This script is ideal if you have a git repository set up.

**Features:**
- Automatically commits uncommitted changes
- Pushes to remote git repository
- Pulls changes on the server
- Rebuilds and restarts Docker container

**Usage:**
```bash
./deploy_to_digitalocean.sh
```

### 2. Direct File Copy Deployment (`deploy_rsync.sh`)

This script copies files directly using rsync without requiring git.

**Features:**
- Direct file synchronization using rsync
- Excludes unnecessary files (cache, logs, etc.)
- Preserves local database files
- Rebuilds and restarts Docker container

**Usage:**
```bash
./deploy_rsync.sh
```

## First-time Setup

If this is your first deployment, you may need to:

1. Set up SSH key authentication:
```bash
ssh-copy-id root@164.90.169.51
```

2. Ensure the OPENAI_API_KEY is set on the droplet:
```bash
ssh root@164.90.169.51
echo "OPENAI_API_KEY=your_api_key_here" > /root/nutrition_tracker/.env
```

## What Happens During Deployment

1. **Local Changes**: The script handles any uncommitted changes
2. **File Transfer**: Files are synced to the droplet
3. **Container Management**:
   - Stops and removes the old container
   - Builds a fresh Docker image
   - Starts a new container with proper environment variables
4. **Health Check**: Verifies the container is running

## Troubleshooting

### Container won't start
Check the logs:
```bash
ssh root@164.90.169.51 "docker logs nutrition-tracker"
```

### Permission denied
Ensure your SSH key is added:
```bash
ssh-add ~/.ssh/id_rsa
```

### Files not updating
Clear Docker cache and rebuild:
```bash
ssh root@164.90.169.51 "cd /root/nutrition_tracker && docker system prune -f && docker build --no-cache -t nutrition-tracker-app ."
```

## Manual Deployment

If you prefer to deploy manually:

1. Copy files to droplet:
```bash
rsync -avz --exclude='*.pyc' --exclude='__pycache__' . root@164.90.169.51:/root/nutrition_tracker/
```

2. SSH into droplet and rebuild:
```bash
ssh root@164.90.169.51
cd /root/nutrition_tracker
docker stop nutrition-tracker
docker rm nutrition-tracker
docker build -t nutrition-tracker-app .
docker run -d --name nutrition-tracker -p 80:8000 -e SECRET_KEY="$(openssl rand -hex 32)" -e OPENAI_API_KEY="$OPENAI_API_KEY" nutrition-tracker-app
```

## Monitoring

After deployment, you can:

1. Check if the app is running:
```bash
curl http://164.90.169.51
```

2. View container status:
```bash
ssh root@164.90.169.51 "docker ps"
```

3. View recent logs:
```bash
ssh root@164.90.169.51 "docker logs --tail 50 nutrition-tracker"
```
