# Database Persistence Guide

This guide explains how the application handles database persistence to prevent data loss during deployments.

## The Problem

Previously, the `database.db` file was included in the Docker image. This meant that every deployment would overwrite the production database with the development database, causing data loss.

## The Solution

We've implemented a volume-based persistence solution:

1. **Database Excluded from Docker Image**: The `.dockerignore` file now excludes `database.db` from the Docker build
2. **Docker Volume**: Production data is stored in a Docker volume mounted at `/root/nutrition_tracker_data`
3. **Environment Variable**: The application uses `DATABASE_PATH` environment variable to locate the database
4. **Automatic Initialization**: The `init_db.py` script creates the database and tables only if they don't exist

## How It Works

### During Development
- Database is stored at `database.db` in your project root
- All models use `DATABASE_PATH` environment variable (defaults to `database.db`)

### During Deployment
1. Docker image is built without the database file
2. Container starts with volume mounted at `/app/data`
3. `init_db.py` runs and creates database at `/app/data/database.db` if it doesn't exist
4. Application uses `DATABASE_PATH=/app/data/database.db`
5. Data persists in `/root/nutrition_tracker_data` on the server

### First Deployment After This Change

For the first deployment after implementing this solution:

```bash
# SSH into your server
ssh root@164.90.169.51

# Create the data directory
mkdir -p /root/nutrition_tracker_data

# If you have existing data you want to preserve, copy it:
# docker cp nutrition-tracker:/app/database.db /root/nutrition_tracker_data/database.db

# Deploy normally
./deploy_to_digitalocean.sh
```

## Benefits

1. **Data Persistence**: Database survives container restarts and redeployments
2. **Separation of Concerns**: Code and data are separated
3. **Easy Backups**: Database can be backed up from `/root/nutrition_tracker_data`
4. **Development Freedom**: You can test with any data locally without affecting production

## Backup and Restore

### Backup
```bash
ssh root@164.90.169.51 "tar -czf nutrition_backup_$(date +%Y%m%d).tar.gz -C /root nutrition_tracker_data"
scp root@164.90.169.51:~/nutrition_backup_*.tar.gz ./backups/
```

### Restore
```bash
scp ./backups/nutrition_backup_20240101.tar.gz root@164.90.169.51:~/
ssh root@164.90.169.51 "tar -xzf nutrition_backup_20240101.tar.gz -C /root"
```

## Troubleshooting

### Database not found
If the application can't find the database:
1. Check that the volume is mounted: `docker inspect nutrition-tracker`
2. Verify DATABASE_PATH is set: `docker exec nutrition-tracker env | grep DATABASE_PATH`
3. Check file exists: `docker exec nutrition-tracker ls -la /app/data/`

### Permission Issues
If you encounter permission issues:
```bash
ssh root@164.90.169.51 "chmod -R 755 /root/nutrition_tracker_data"
```

### Migration from Old Setup
If you're migrating from the old setup where database was in the image:
```bash
# Copy database from running container
docker cp nutrition-tracker:/app/database.db /root/nutrition_tracker_data/database.db

# Redeploy with new setup
./deploy_to_digitalocean.sh
```
