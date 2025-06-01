#!/bin/bash

# Remote Database Manager for Nutrition Tracker
# Usage: ./remote_db_manager.sh [backup|restore|query|shell]

SERVER="root@164.90.169.51"
REMOTE_DB="/root/nutrition_tracker_data/database.db"
LOCAL_BACKUP_DIR="$HOME/nutrition_tracker_backups"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

case "$1" in
  backup)
    echo -e "${BLUE}Backing up remote database...${NC}"
    mkdir -p "$LOCAL_BACKUP_DIR"
    BACKUP_FILE="$LOCAL_BACKUP_DIR/database_$(date +%Y%m%d_%H%M%S).db"
    if scp "$SERVER:$REMOTE_DB" "$BACKUP_FILE"; then
      echo -e "${GREEN}✓ Backup saved to: $BACKUP_FILE${NC}"
      ls -lh "$BACKUP_FILE"
    else
      echo -e "${RED}✗ Backup failed${NC}"
      exit 1
    fi
    ;;

  restore)
    if [ -z "$2" ]; then
      echo -e "${RED}Usage: $0 restore <backup_file>${NC}"
      exit 1
    fi
    if [ ! -f "$2" ]; then
      echo -e "${RED}Error: File $2 not found${NC}"
      exit 1
    fi
    echo -e "${BLUE}Restoring database from $2...${NC}"
    read -p "This will overwrite the production database. Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      # Create backup before restore
      echo -e "${BLUE}Creating safety backup first...${NC}"
      SAFETY_BACKUP="$LOCAL_BACKUP_DIR/database_before_restore_$(date +%Y%m%d_%H%M%S).db"
      scp "$SERVER:$REMOTE_DB" "$SAFETY_BACKUP"

      # Restore database
      if scp "$2" "$SERVER:$REMOTE_DB"; then
        ssh "$SERVER" "docker restart nutrition-tracker"
        echo -e "${GREEN}✓ Database restored and container restarted${NC}"
        echo -e "${GREEN}Safety backup saved at: $SAFETY_BACKUP${NC}"
      else
        echo -e "${RED}✗ Restore failed${NC}"
        exit 1
      fi
    else
      echo -e "${BLUE}Restore cancelled${NC}"
    fi
    ;;

  query)
    if [ -z "$2" ]; then
      echo -e "${RED}Usage: $0 query \"SQL QUERY\"${NC}"
      echo "Example: $0 query \"SELECT COUNT(*) FROM ingredients;\""
      exit 1
    fi
    echo -e "${BLUE}Running query on remote database...${NC}"
    ssh "$SERVER" "sqlite3 -header -column $REMOTE_DB \"$2\""
    ;;

  shell)
    echo -e "${BLUE}Opening SQLite shell on remote database...${NC}"
    echo -e "${GREEN}Tip: Use .help for commands, .quit to exit${NC}"
    ssh -t "$SERVER" "sqlite3 -header -column $REMOTE_DB"
    ;;

  info)
    echo -e "${BLUE}Fetching database information...${NC}"
    ssh "$SERVER" "ls -lh $REMOTE_DB"
    echo
    echo -e "${BLUE}Table information:${NC}"
    ssh "$SERVER" "sqlite3 $REMOTE_DB '.tables'"
    echo
    echo -e "${BLUE}Row counts:${NC}"
    ssh "$SERVER" "sqlite3 -header -column $REMOTE_DB \"
      SELECT 'ingredients' as table_name, COUNT(*) as row_count FROM ingredients
      UNION ALL
      SELECT 'ingredient_quantity', COUNT(*) FROM ingredient_quantity
      UNION ALL
      SELECT 'consumption', COUNT(*) FROM consumption
      UNION ALL
      SELECT 'recipes', COUNT(*) FROM recipes
      UNION ALL
      SELECT 'recipe_ingredients', COUNT(*) FROM recipe_ingredients
      UNION ALL
      SELECT 'favorites', COUNT(*) FROM favorites
      UNION ALL
      SELECT 'exercises', COUNT(*) FROM exercises
      UNION ALL
      SELECT 'workouts', COUNT(*) FROM workouts
      UNION ALL
      SELECT 'workout_exercises', COUNT(*) FROM workout_exercises
      UNION ALL
      SELECT 'calories', COUNT(*) FROM calories
      UNION ALL
      SELECT 'weight', COUNT(*) FROM weight;
    \""
    ;;

  recent)
    echo -e "${BLUE}Recent consumption entries:${NC}"
    ssh "$SERVER" "sqlite3 -header -column $REMOTE_DB \"
      SELECT
        c.date,
        i.name as food,
        ROUND(c.quantity * iq.quantity, 2) as qty,
        u.name as unit,
        ROUND(c.quantity * iq.calories, 1) as calories
      FROM consumption c
      JOIN ingredient_quantity iq ON c.ingredient_quantity_id = iq.id
      JOIN ingredients i ON iq.ingredient_id = i.id
      JOIN units u ON iq.unit_id = u.id
      ORDER BY c.date DESC, c.id DESC
      LIMIT 10;
    \""
    ;;

  export)
    EXPORT_DIR="$LOCAL_BACKUP_DIR/export_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$EXPORT_DIR"
    echo -e "${BLUE}Exporting all tables to CSV files...${NC}"

    # Get list of tables
    TABLES=$(ssh "$SERVER" "sqlite3 $REMOTE_DB '.tables'" | tr ' ' '\n' | grep -v '^$')

    for table in $TABLES; do
      echo -e "${BLUE}Exporting $table...${NC}"
      ssh "$SERVER" "sqlite3 -header -csv $REMOTE_DB \"SELECT * FROM $table;\"" > "$EXPORT_DIR/$table.csv"
    done

    echo -e "${GREEN}✓ All tables exported to: $EXPORT_DIR${NC}"
    ls -la "$EXPORT_DIR"
    ;;

  *)
    echo -e "${BLUE}Remote Database Manager for Nutrition Tracker${NC}"
    echo
    echo "Usage: $0 [command] [options]"
    echo
    echo "Commands:"
    echo "  backup              - Backup remote database to local machine"
    echo "  restore <file>      - Restore database from local backup file"
    echo "  query \"SQL\"         - Run SQL query on remote database"
    echo "  shell               - Open interactive SQLite shell"
    echo "  info                - Show database information and statistics"
    echo "  recent              - Show recent consumption entries"
    echo "  export              - Export all tables to CSV files"
    echo
    echo "Examples:"
    echo "  $0 backup"
    echo "  $0 query \"SELECT COUNT(*) FROM ingredients;\""
    echo "  $0 shell"
    echo "  $0 restore ~/nutrition_tracker_backups/database_20240101_120000.db"
    ;;
esac
