# Gym Tracker Production Migration Guide

## Overview
The gym tracker feature requires database tables that don't exist in production yet. This guide explains how to run the necessary migrations.

## Migration Order
The migrations must be run in this specific order:
1. **Gym Tracker Base Tables** - Creates exercises, workout_sessions, and workout_sets tables
2. **Workout Templates** - Adds template functionality on top of the base tables

## Files Created
- `migrate_gym_tracker_complete.py` - Combined migration script that runs both migrations in order

## Deployment Steps

### 1. Copy the migration script to production
```bash
scp migrate_gym_tracker_complete.py root@164.90.169.51:~/
```

### 2. SSH into the production server
```bash
ssh root@164.90.169.51
```

### 3. Set the database path and run the migration
```bash
export DATABASE_PATH=/root/nutrition_tracker_data/database.db
python3 migrate_gym_tracker_complete.py
```

Expected output:
```
Running gym tracker migrations on database: /root/nutrition_tracker_data/database.db
============================================================

Step 1: Creating gym tracker tables...
✓ Created exercises table
✓ Created workout_sessions table
✓ Created workout_sets table
✓ Populated initial exercises
✅ Gym tracker tables created successfully!

Step 2: Adding workout templates functionality...
✓ Created workout_templates table
✓ Created workout_template_exercises table
✓ Added template_id column to workout_sessions
✓ Created indexes
✓ Created sample 'Push Day' template
✅ Workout templates migration completed successfully!

============================================================
✅ All gym tracker migrations completed successfully!
```

### 4. Verify the migration
```bash
sqlite3 /root/nutrition_tracker_data/database.db ".tables" | grep -E "(workout|exercise|template)"
```

Should show:
- exercises
- workout_sessions
- workout_sets
- workout_templates
- workout_template_exercises

### 5. Restart the application
```bash
systemctl restart nutrition-tracker
```

## Alternative: Run migrations separately
If you prefer to run the original migration files separately:

```bash
# First, update migrate_add_gym_tracker.py to use DATABASE_PATH
sed -i "s/sqlite3.connect('database.db')/sqlite3.connect(os.getenv('DATABASE_PATH', 'database.db'))/" migrate_add_gym_tracker.py
sed -i '1i import os' migrate_add_gym_tracker.py

# Run migrations in order
export DATABASE_PATH=/root/nutrition_tracker_data/database.db
python3 migrate_add_gym_tracker.py
python3 migrate_add_workout_templates.py
```

## Troubleshooting

### If migration fails
1. Check database permissions:
   ```bash
   ls -la /root/nutrition_tracker_data/database.db
   ```

2. Backup database before retrying:
   ```bash
   cp /root/nutrition_tracker_data/database.db /root/nutrition_tracker_data/database.db.backup
   ```

3. Check for partial migration:
   ```bash
   sqlite3 /root/nutrition_tracker_data/database.db ".schema" | grep -E "(workout|exercise|template)"
   ```

### Rolling back
If needed, remove the gym tracker tables:
```sql
DROP TABLE IF EXISTS workout_template_exercises;
DROP TABLE IF EXISTS workout_templates;
DROP TABLE IF EXISTS workout_sets;
DROP TABLE IF EXISTS workout_sessions;
DROP TABLE IF EXISTS exercises;
```

## Post-Migration
After successful migration:
1. Test the gym tracker features on production
2. Create a few test templates
3. Verify data persistence across restarts
