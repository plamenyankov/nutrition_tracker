# Flask Nutrition Tracker - Docker + DigitalOcean Deployment

## Overview
This document outlines the **essential tasks** to deploy the Flask Nutrition Tracker application using **Docker containers on DigitalOcean**. This is a streamlined checklist for a production-ready deployment.

---

## 📋 Essential Pre-Deployment Tasks

### 1. Code Preparation
- [x] **Basic Configuration**
  - [x] Move sensitive data to environment variables (SECRET_KEY, OPENAI_API_KEY)
  - [x] Ensure debug mode is disabled in production (`DEBUG=False`)
  - [x] Test app runs without errors locally

- [x] **Dependencies**
  - [x] Add `gunicorn` to requirements.txt
  - [x] Ensure requirements.txt is up to date

---

## 🐳 Docker Setup

### 2. Create Dockerfile
- [x] **Dockerfile Creation**
  - [x] Use Python 3.9-slim base image
  - [x] Set working directory to /app
  - [x] Copy requirements.txt and install dependencies
  - [x] Copy application code
  - [x] Expose port 5000
  - [x] Set entry point to run with gunicorn

- [x] **Test Docker Locally**
  - [x] Build Docker image: `docker build -t nutrition-tracker .`
  - [x] Run container locally: `docker run -p 5000:5000 nutrition-tracker`
  - [x] Verify app works in container

### 3. Docker Hub Setup
- [x] **Container Registry**
  - [x] Create Docker Hub account
  - [x] Create repository: `plamenyankov1/nutrition-tracker`
  - [x] Tag image: `docker tag nutrition-tracker plamenyankov1/nutrition-tracker`
  - [x] Push image: `docker push plamenyankov1/nutrition-tracker`

---

## ☁️ DigitalOcean Deployment

### 4. DigitalOcean Server Setup
- [x] **Create Droplet**
  - [x] Create DigitalOcean account
  - [x] Create Ubuntu 22.04 LTS droplet (minimum $6/month)
  - [x] Set up SSH keys for secure access
  - [x] Note down droplet IP address

- [x] **Server Configuration**
  - [x] SSH into server: `ssh root@your-server-ip`
  - [x] Update system: `apt update && apt upgrade -y`
  - [x] Install Docker: `curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh`
  - [x] Install Docker Compose: `apt install docker-compose -y`

### 5. Firewall & Security
- [x] **Basic Security Setup**
  - [x] Set up UFW firewall: `ufw enable`
  - [x] Allow SSH: `ufw allow 22`
  - [x] Allow HTTP: `ufw allow 80`
  - [x] Allow HTTPS: `ufw allow 443`

### 6. Deploy Application
- [x] **Pull and Run Container**
  - [x] Pull your image: `docker pull plamenyankov1/nutrition-tracker`
  - [x] Create environment file with your secrets
  - [x] Run container with environment variables:
    ```bash
    docker run -d \
      --name nutrition-app \
      -p 5000:5000 \
      -e SECRET_KEY=your-secret-key \
      -e OPENAI_API_KEY=your-openai-api-key \
      -e FLASK_ENV=production \
      -e DEBUG=False \
      --restart unless-stopped \
      plamenyankov1/nutrition-tracker
    ```

### 7. Nginx Reverse Proxy
- [ ] **Install and Configure Nginx**
  - [ ] Install Nginx: `apt install nginx -y`
  - [ ] Create Nginx config file for your app
  - [ ] Configure proxy to forward requests to Docker container
  - [ ] Test Nginx configuration: `nginx -t`
  - [ ] Restart Nginx: `systemctl restart nginx`

### 8. SSL Certificate
- [ ] **Set up HTTPS**
  - [ ] Install Certbot: `apt install certbot python3-certbot-nginx -y`
  - [ ] Get SSL certificate: `certbot --nginx -d your-domain.com`
  - [ ] Test auto-renewal: `certbot renew --dry-run`

---

## 🔧 Essential Configuration Files

### 9. Required Files to Create

- [x] **Dockerfile**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

- [ ] **Nginx Configuration** (`/etc/nginx/sites-available/nutrition-tracker`)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Environment Variables Script** (`deploy.sh`)
```bash
#!/bin/bash
docker run -d \
  --name nutrition-app \
  -p 5000:5000 \
  -e SECRET_KEY="your-generated-secret-key" \
  -e OPENAI_API_KEY="your-openai-api-key" \
  -e FLASK_ENV=production \
  -e DEBUG=False \
  --restart unless-stopped \
  your-username/nutrition-tracker
```

---

## 🚀 Go Live Checklist

### 10. Final Testing
- [x] **Verify Deployment**
  - [x] Check container is running: `docker ps`
  - [x] Test app responds: `curl http://localhost:5000`
  - [x] Test through Nginx: `curl http://your-domain.com`
  - [ ] Test HTTPS: `curl https://your-domain.com`

- [x] **Functional Testing**
  - [x] App loads in browser
  - [x] Can add food items
  - [x] OpenAI integration works
  - [x] Data persists between requests

### 11. Basic Monitoring
- [ ] **Check Logs**
  - [ ] View container logs: `docker logs nutrition-app`
  - [ ] Check Nginx logs: `tail -f /var/log/nginx/access.log`
  - [ ] Monitor system resources: `htop`

---

## 🔄 Updates & Maintenance

### 12. Deployment Updates
- [ ] **Update Process**
  - [ ] Build new image locally
  - [ ] Push to Docker Hub
  - [ ] SSH to server
  - [ ] Stop old container: `docker stop nutrition-app`
  - [ ] Remove old container: `docker rm nutrition-app`
  - [ ] Pull new image: `docker pull your-username/nutrition-tracker`
  - [ ] Run new container with same command

---

## 📚 Quick Reference Commands

### Essential Commands
```bash
# Build and push image
docker build -t your-username/nutrition-tracker .
docker push your-username/nutrition-tracker

# Deploy on server
docker pull your-username/nutrition-tracker
docker stop nutrition-app && docker rm nutrition-app
docker run -d --name nutrition-app -p 5000:5000 \
  -e SECRET_KEY=your-key -e OPENAI_API_KEY=your-key \
  --restart unless-stopped your-username/nutrition-tracker

# Check status
docker ps
docker logs nutrition-app
systemctl status nginx
```

---

## 🎯 Success Criteria

- [ ] App accessible via HTTPS at your domain
- [ ] Container runs automatically on server restart
- [ ] All core functionality works (add food, OpenAI integration)
- [ ] SSL certificate is valid and auto-renewing

---

*Estimated deployment time: 2-3 hours*
*Monthly cost: ~$6-12 for DigitalOcean droplet*
