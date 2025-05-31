# How to Check Docker Logs on DigitalOcean

## 1. SSH into your Droplet

```bash
ssh root@164.90.169.51
```

## 2. Check Running Containers

```bash
# List all running containers
docker ps

# List all containers (including stopped ones)
docker ps -a
```

## 3. View Container Logs

```bash
# View logs of the nutrition-tracker container
docker logs nutrition-tracker

# View last 100 lines
docker logs --tail 100 nutrition-tracker

# Follow logs in real-time (like tail -f)
docker logs -f nutrition-tracker

# View logs with timestamps
docker logs -t nutrition-tracker

# View logs from last 30 minutes
docker logs --since 30m nutrition-tracker
```

## 4. Common Commands for Debugging

```bash
# Check if container is running
docker ps | grep nutrition-tracker

# Inspect container for detailed info
docker inspect nutrition-tracker

# Execute commands inside running container
docker exec -it nutrition-tracker /bin/bash

# Check container resource usage
docker stats nutrition-tracker
```

## 5. Debugging the AI Assistant to Recipe Issue

To specifically debug the "save ingredients from AI assistant to recipe" issue:

```bash
# Check recent logs with grep for errors
docker logs nutrition-tracker 2>&1 | grep -i error | tail -20

# Look for OpenAI related errors
docker logs nutrition-tracker 2>&1 | grep -i openai | tail -20

# Look for recipe creation errors
docker logs nutrition-tracker 2>&1 | grep -i recipe | tail -20

# Check Python traceback errors
docker logs nutrition-tracker 2>&1 | grep -A 10 -i traceback
```

## 6. Check Application Logs Inside Container

```bash
# Enter the container
docker exec -it nutrition-tracker /bin/bash

# Inside container, check if there are any log files
ls -la /app/logs/  # if you have a logs directory
cat /app/*.log     # if there are log files

# Check Python error output
python -c "import app; print(app.app.config)"
```

## 7. Common Issues and Solutions

### Issue: OpenAI API Timeout
- **Symptom**: Logs show timeout errors after 30-120 seconds
- **Solution**: Already configured with 120s timeout, but may need to increase

### Issue: Memory Issues
```bash
# Check container memory usage
docker stats --no-stream nutrition-tracker

# If memory is high, restart container
docker restart nutrition-tracker
```

### Issue: Database Lock
- **Symptom**: "database is locked" errors
- **Solution**: May need to restart container or check SQLite concurrent access

## 8. Restart Container if Needed

```bash
# Restart the container
docker restart nutrition-tracker

# Stop and start manually
docker stop nutrition-tracker
docker start nutrition-tracker

# Full recreation (if config changed)
docker stop nutrition-tracker
docker rm nutrition-tracker
docker run -d --name nutrition-tracker -p 5000:5000 nutrition-tracker:latest
```

## 9. Live Debugging Session

For a live debugging session while trying to reproduce the issue:

```bash
# Terminal 1: Follow logs
ssh root@164.90.169.51
docker logs -f nutrition-tracker

# Terminal 2: Try to reproduce the issue in the app
# Go to AI Assistant, analyze foods, try to create recipe
# Watch the logs in Terminal 1 for errors
```

## Quick Debug Commands

```bash
# One-liner to check recent errors
ssh root@164.90.169.51 "docker logs --tail 200 nutrition-tracker 2>&1 | grep -i -E 'error|exception|traceback'"

# Save logs to file for analysis
ssh root@164.90.169.51 "docker logs nutrition-tracker > nutrition_logs.txt 2>&1"
scp root@164.90.169.51:nutrition_logs.txt ./
```

## What to Look For

When checking logs for the AI Assistant → Recipe creation issue, look for:

1. **OpenAI API errors**: Rate limits, timeouts, invalid responses
2. **Database errors**: SQLite locks, constraint violations
3. **Data parsing errors**: CSV parsing issues, missing columns
4. **Memory errors**: If processing large responses
5. **Permission errors**: File system access issues

The error will likely show a Python traceback that indicates exactly where the recipe creation is failing.
