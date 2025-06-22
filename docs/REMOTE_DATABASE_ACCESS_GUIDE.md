# Remote Database Access Guide for DigitalOcean

## Database Location

Your nutrition tracker uses **SQLite** database stored on the DigitalOcean server at:
- **Container path**: `/app/data/database.db`
- **Host path**: `/root/nutrition_tracker_data/database.db`

## Methods to Access the Database

### Method 1: Direct SSH Access (Recommended)

1. **SSH into your server**:
```bash
ssh root@164.90.169.51
```

2. **Access database directly on server**:
```bash
# Install sqlite3 if not already installed
apt-get update && apt-get install -y sqlite3

# Open the database
sqlite3 /root/nutrition_tracker_data/database.db

# Now you can run SQL commands
.tables  # List all tables
.schema  # Show table schemas
SELECT * FROM ingredients LIMIT 10;  # Query example
.quit  # Exit sqlite3
```

### Method 2: Copy Database Locally

1. **Download database to your local machine**:
```bash
# Create local backup directory
mkdir -p ~/nutrition_tracker_backups

# Copy database from server
scp root@164.90.169.51:/root/nutrition_tracker_data/database.db ~/nutrition_tracker_backups/database_$(date +%Y%m%d_%H%M%S).db
```

2. **Open locally with SQLite**:
```bash
sqlite3 ~/nutrition_tracker_backups/database_*.db
```

### Method 3: Access Through Docker Container

1. **SSH into server and access via Docker**:
```bash
ssh root@164.90.169.51

# Execute sqlite3 inside the container
docker exec -it nutrition-tracker sqlite3 /app/data/database.db
```

### Method 4: Create a Database Management Script

Save this as `remote_db_manager.sh` on your local machine:

```bash
#!/bin/bash

# Remote Database Manager for Nutrition Tracker
# Usage: ./remote_db_manager.sh [backup|restore|query|shell]

SERVER="root@164.90.169.51"
REMOTE_DB="/root/nutrition_tracker_data/database.db"
LOCAL_BACKUP_DIR="$HOME/nutrition_tracker_backups"

case "$1" in
  backup)
    echo "Backing up remote database..."
    mkdir -p "$LOCAL_BACKUP_DIR"
    BACKUP_FILE="$LOCAL_BACKUP_DIR/database_$(date +%Y%m%d_%H%M%S).db"
    scp "$SERVER:$REMOTE_DB" "$BACKUP_FILE"
    echo "Backup saved to: $BACKUP_FILE"
    ;;

  restore)
    if [ -z "$2" ]; then
      echo "Usage: $0 restore <backup_file>"
      exit 1
    fi
    echo "Restoring database from $2..."
    read -p "This will overwrite the production database. Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      scp "$2" "$SERVER:$REMOTE_DB"
      ssh "$SERVER" "docker restart nutrition-tracker"
      echo "Database restored and container restarted"
    fi
    ;;

  query)
    if [ -z "$2" ]; then
      echo "Usage: $0 query \"SQL QUERY\""
      exit 1
    fi
    echo "Running query on remote database..."
    ssh "$SERVER" "sqlite3 $REMOTE_DB \"$2\""
    ;;

  shell)
    echo "Opening SQLite shell on remote database..."
    ssh -t "$SERVER" "sqlite3 $REMOTE_DB"
    ;;

  *)
    echo "Usage: $0 [backup|restore|query|shell]"
    echo "  backup              - Backup remote database"
    echo "  restore <file>      - Restore database from backup"
    echo "  query \"SQL\"         - Run SQL query"
    echo "  shell               - Open SQLite shell"
    ;;
esac
```

Make it executable:
```bash
chmod +x remote_db_manager.sh
```

## Common Database Operations

### View All Tables
```sql
.tables
```

### Check Table Schemas
```sql
.schema ingredients
.schema ingredient_quantity
.schema consumption
.schema recipes
.schema recipe_ingredients
```

### Query Examples

**View recent food entries**:
```sql
SELECT i.name, iq.quantity, iq.unit_id, iq.calories, iq.protein, iq.carbohydrates, iq.fat
FROM ingredient_quantity iq
JOIN ingredients i ON iq.ingredient_id = i.id
ORDER BY iq.id DESC
LIMIT 10;
```

**View consumption history**:
```sql
SELECT c.date, i.name, c.quantity, iq.calories
FROM consumption c
JOIN ingredient_quantity iq ON c.ingredient_quantity_id = iq.id
JOIN ingredients i ON iq.ingredient_id = i.id
ORDER BY c.date DESC
LIMIT 20;
```

**Update a food's nutrition values**:
```sql
UPDATE ingredient_quantity
SET calories = 250, protein = 20, carbohydrates = 10, fat = 15
WHERE id = 123;
```

**Delete a food entry**:
```sql
-- Be careful! This will delete the food and all related consumption records
DELETE FROM ingredient_quantity WHERE id = 123;
```

### Export/Import Data

**Export to CSV**:
```sql
.mode csv
.headers on
.output ingredients_export.csv
SELECT * FROM ingredients;
.output stdout
```

**Import from CSV**:
```sql
.mode csv
.import new_ingredients.csv ingredients
```

## Safety Tips

1. **Always backup before making changes**:
```bash
./remote_db_manager.sh backup
```

2. **Test queries locally first**:
   - Download a backup
   - Test your SQL on the backup
   - Apply to production only when confident

3. **Use transactions for multiple changes**:
```sql
BEGIN TRANSACTION;
-- Your changes here
UPDATE ingredient_quantity SET calories = 100 WHERE id = 1;
UPDATE ingredient_quantity SET calories = 200 WHERE id = 2;
-- If everything looks good:
COMMIT;
-- Or if something went wrong:
ROLLBACK;
```

## GUI Database Management

If you prefer a graphical interface:

1. **Download the database locally** (using Method 2 above)

2. **Use a SQLite GUI tool**:
   - [DB Browser for SQLite](https://sqlitebrowser.org/) (Free, cross-platform)
   - [TablePlus](https://tableplus.com/) (Free tier available)
   - [DBeaver](https://dbeaver.io/) (Free, supports many databases)

3. **Make your changes in the GUI**

4. **Upload the modified database**:
```bash
# First backup the current production database
./remote_db_manager.sh backup

# Upload your modified database
scp your_modified_database.db root@164.90.169.51:/root/nutrition_tracker_data/database.db

# Restart the container to ensure clean connections
ssh root@164.90.169.51 "docker restart nutrition-tracker"
```

## Automated Backups

Add this to your server's crontab for daily backups:

```bash
# SSH into server
ssh root@164.90.169.51

# Edit crontab
crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * tar -czf /root/backups/nutrition_db_$(date +\%Y\%m\%d).tar.gz -C /root nutrition_tracker_data
```

## Troubleshooting

### Database is locked
If you get "database is locked" errors:
```bash
ssh root@164.90.169.51 "docker restart nutrition-tracker"
```

### Corrupted database
If the database becomes corrupted:
```bash
# On the server
sqlite3 /root/nutrition_tracker_data/database.db ".recover" | sqlite3 /root/nutrition_tracker_data/database_recovered.db
mv /root/nutrition_tracker_data/database.db /root/nutrition_tracker_data/database_corrupted.db
mv /root/nutrition_tracker_data/database_recovered.db /root/nutrition_tracker_data/database.db
docker restart nutrition-tracker
```

### Check database integrity
```sql
PRAGMA integrity_check;
```

## Quick Reference Card

```bash
# Quick backup
ssh root@164.90.169.51 "cp /root/nutrition_tracker_data/database.db /root/nutrition_tracker_data/database_backup_$(date +%Y%m%d).db"

# Quick SQL query
ssh root@164.90.169.51 "sqlite3 /root/nutrition_tracker_data/database.db 'SELECT COUNT(*) FROM ingredients;'"

# Interactive SQL shell
ssh -t root@164.90.169.51 "sqlite3 /root/nutrition_tracker_data/database.db"

# View recent entries
ssh root@164.90.169.51 "sqlite3 /root/nutrition_tracker_data/database.db 'SELECT * FROM consumption ORDER BY date DESC LIMIT 5;'"
```
