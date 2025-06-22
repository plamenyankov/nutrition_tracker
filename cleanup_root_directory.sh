#!/bin/bash

# Nutrition Tracker - Root Directory Cleanup Script
# Removes completed migration files, old backups, and test scripts
# Run from project root directory

echo "🧹 Cleaning up root directory..."
echo "========================================"

# Create backup list of what we're removing
echo "Creating backup list of removed files..."
{
    echo "# Files removed on $(date)"
    echo "# Nutrition Tracker Root Directory Cleanup"
    echo ""
} > removed_files_$(date +%Y%m%d_%H%M%S).log

# Function to safely remove files
remove_files() {
    local category="$1"
    shift
    echo ""
    echo "📁 Removing $category..."

    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "  ✓ Removing: $file"
            echo "$file" >> removed_files_$(date +%Y%m%d_%H%M%S).log
            rm "$file"
        else
            echo "  ⚠ Not found: $file"
        fi
    done
}

# 1. Remove old SQLite database backups
remove_files "Old SQLite Database Backups" \
    "database_backup_1749877305.db" \
    "database_backup_1749886192.db" \
    "database_backup_1749886247.db" \
    "database_backup_1749889452.db" \
    "database_backup.db" \
    "database_old.db" \
    "database_old.db-shm" \
    "database_old.db-wal"

# 2. Remove migration logs and reports
remove_files "Migration Logs and Reports" \
    "migration_20250614_060944.log" \
    "migration_20250614_061226.log" \
    "migration_20250614_061255.log" \
    "migration_20250614_061610.log" \
    "migration_20250614_061642.log" \
    "migration_20250614_061717.log" \
    "migration_20250614_061748.log" \
    "migration_20250614_061828.log" \
    "migration_20250614_082504.log" \
    "migration_20250614_113606.log" \
    "migration_20250614_113626.log" \
    "migration_20250615_080350.log" \
    "migration_report_20250614_061840.json" \
    "migration_report_20250614_082522.json" \
    "migration_report_20250614_113613.json" \
    "migration_report_20250614_113634.json" \
    "migration_report_20250615_080425.json"

# 3. Remove one-time migration scripts
remove_files "One-time Migration Scripts" \
    "migrate_production_sqlite_to_mysql.py" \
    "migrate_to_mysql.py" \
    "simple_migrate_prod.py" \
    "migrate_timing_to_production.py"

# 4. Remove sync scripts
remove_files "Data Sync Scripts" \
    "sync_dev_to_prod.py" \
    "sync_dev_to_prod_with_backup.py" \
    "sync_prod_to_dev_mysql.py" \
    "sync_prod_schema_to_dev.py" \
    "sync_workout_data.py"

# 5. Remove test and debug scripts
remove_files "Test and Debug Scripts" \
    "test_production_db.py" \
    "test_mysql_connection.py" \
    "test_app_mysql.py" \
    "test_current_db.py" \
    "test_timer_functionality.py" \
    "check_dev_data.py" \
    "check_prod_data.py" \
    "check_users.py"

# 6. Remove old documentation
remove_files "Outdated Documentation" \
    "SQLITE_TO_MYSQL_MIGRATION_PLAN.md" \
    "BRAND_BOOK.md"

# 7. Remove old MySQL backups (keep latest)
remove_files "Old MySQL Backups" \
    "nutri_tracker_prod_backup_20250615_085943.sql" \
    "nutri_tracker_prod_backup_20250615_090242.sql"

# 8. Remove utility scripts that are no longer needed
remove_files "Utility Scripts" \
    "fix_consumption_dates.py" \
    "run_remote_migrations.sh"

echo ""
echo "========================================"
echo "✅ Cleanup completed!"
echo ""
echo "📊 Summary:"
echo "  • Removed old SQLite database backups"
echo "  • Removed completed migration logs"
echo "  • Removed one-time migration scripts"
echo "  • Removed test and debug scripts"
echo "  • Removed outdated documentation"
echo "  • Kept active migration scripts"
echo "  • Kept current documentation"
echo "  • Kept latest production backup"
echo ""
echo "📝 List of removed files saved to: removed_files_$(date +%Y%m%d_%H%M%S).log"
echo ""
echo "🎯 Root directory is now clean and organized!"
