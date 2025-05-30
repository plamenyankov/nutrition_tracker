# Deployment Guide for Nutrition Tracker

This guide explains how to deploy your Nutrition Tracker application to DigitalOcean.

## Prerequisites

1. SSH access to your DigitalOcean droplet (IP: 164.90.169.51)
2. Docker installed locally and on the droplet
3. Docker Hub account
4. OPENAI_API_KEY set up on the droplet

## Docker Hub Setup

Before using the deployment script, you need to:

1. **Create a Docker Hub account** (if you don't have one):
   - Go to https://hub.docker.com
   - Sign up for a free account

2. **Login to Docker Hub locally**:
   ```bash
   docker login
   ```
   Enter your Docker Hub username and password.

3. **Update the deployment script** with your Docker Hub username:
   - Edit `deploy_to_digitalocean.sh`
   - Change `DOCKER_USERNAME="plamenyankov"` to your Docker Hub username

## Deployment Scripts

We provide two deployment scripts:

### 1. Docker Hub Deployment (`deploy_to_digitalocean.sh`)

This script uses Docker Hub to transfer the image.

**Features:**
- Builds Docker image locally
- Pushes image to Docker Hub
- Pulls image on the server (no server-side building needed)
- Faster deployment (no compilation on server)
- Version control through Docker tags

**Usage:**
```bash
./deploy_to_digitalocean.sh
```

**What it does:**
1. Commits any uncommitted changes to git
2. Pushes to git remote (if configured)
3. Builds Docker image locally
4. Pushes image to Docker Hub
5. Connects to server and pulls the new image
6. Restarts the container

### 2. Direct File Copy Deployment (`deploy_rsync.sh`)

This script copies files directly using rsync without requiring git.

**Features:**
- Direct file synchronization using rsync
- Excludes unnecessary files (cache, logs, etc.)
- Preserves local database files
- Builds Docker image on the server

**Usage:**
```bash
./deploy_rsync.sh
```

## First-time Setup

If this is your first deployment:

1. **Set up SSH key authentication**:
   ```bash
   ssh-copy-id root@164.90.169.51
   ```

2. **Ensure the OPENAI_API_KEY is set on the droplet**:
   ```bash
   ssh root@164.90.169.51
   echo "OPENAI_API_KEY=your_api_key_here" > /root/nutrition_tracker/.env
   ```

3. **Login to Docker Hub on the server** (for pulling private images):
   ```bash
   ssh root@164.90.169.51 "docker login"
   ```

## Troubleshooting

### Docker push fails
Ensure you're logged in:
```bash
docker login
```

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

### Image not found on Docker Hub
Make sure you've updated the `DOCKER_USERNAME` in the script and the repository is public.

## Manual Deployment with Docker Hub

If you prefer to deploy manually:

1. Build and push locally:
```bash
docker build -t yourusername/nutrition-tracker:latest .
docker push yourusername/nutrition-tracker:latest
```

2. SSH into droplet and pull/run:
```bash
ssh root@164.90.169.51
docker pull yourusername/nutrition-tracker:latest
docker stop nutrition-tracker
docker rm nutrition-tracker
docker run -d --name nutrition-tracker -p 80:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  yourusername/nutrition-tracker:latest
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

## Advanced: Using Different Tags

For production deployments, consider using version tags:

```bash
# In deploy_to_digitalocean.sh, change:
DOCKER_TAG="v1.0.0"  # Instead of "latest"
```

This allows you to:
- Roll back to previous versions
- Deploy specific versions
- Maintain a deployment history
