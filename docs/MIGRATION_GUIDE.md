# SQLite to MySQL Migration Guide

This guide explains how to migrate your nutrition tracker database from SQLite to a remote MySQL server.

## Prerequisites

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have access to the remote MySQL server at `192.168.11.1:3306`

## Configuration

The system uses the following configuration:

- **Remote MySQL Server**: 192.168.11.1:3306
- **MySQL User**: remote_user
- **MySQL Password**: BuGr@d@N4@loB6!
- **Development Database**: nutri_tracker_dev
- **Production Database**: nutri_tracker_prod

## Docker Network Configuration

If running in Docker, the container needs to access the remote MySQL server. The `docker-compose.yml` is configured with:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
  - "mysql-host:192.168.11.1"
```

## Step 1: Setup MySQL Databases

First, you need to create the required databases on the remote MySQL server.

### Automated Setup (Recommended)

Run the simple database setup script:

```bash
python simple_mysql_setup.py
```

This will:
- Connect directly to MySQL server at 192.168.11.1:3306
- Create `nutri_tracker_dev` and `nutri_tracker_prod` databases
- Set up the `remote_user` with proper `mysql_native_password` authentication
- Test the connection to ensure everything works

### Option B: Manual Setup

If you prefer to run SQL commands directly:

```sql
-- Connect to MySQL as admin user
mysql -h 192.168.11.1 -P 3306 -u root -p

-- Create databases
CREATE DATABASE IF NOT EXISTS `nutri_tracker_dev`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `nutri_tracker_prod`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create application user with native password authentication
CREATE USER IF NOT EXISTS 'remote_user'@'%' IDENTIFIED WITH mysql_native_password BY 'BuGr@d@N4@loB6!';

-- Grant privileges
GRANT ALL PRIVILEGES ON `nutri_tracker_dev`.* TO 'remote_user'@'%';
GRANT ALL PRIVILEGES ON `nutri_tracker_prod`.* TO 'remote_user'@'%';

-- Flush privileges
FLUSH PRIVILEGES;
```

## Step 2: Test MySQL Connection

After setting up the databases, test the connection:

```bash
python test_mysql_connection.py
```

This will:
- Test connection to both development and production databases
- Verify the databases exist and are accessible
- Show available databases on the server

## Step 3: Migrate Database

### Basic Migration (Development)

To migrate your local `database.db` to the development MySQL database:

```bash
python migrate_to_mysql.py
```

### Production Migration

To migrate the production SQLite database to production MySQL:

```bash
python migrate_to_mysql.py --env production --source production
```

### Advanced Options

```bash
# Migrate specific tables only
python migrate_to_mysql.py --tables users recipes consumption

# Migrate schema only (no data)
python migrate_to_mysql.py --schema-only

# Migrate data only (assumes schema exists)
python migrate_to_mysql.py --data-only

# Drop existing tables before migration
python migrate_to_mysql.py --drop-existing

# Use custom batch size for large datasets
python migrate_to_mysql.py --batch-size 5000

# Skip verification after migration
python migrate_to_mysql.py --skip-verification

# Use custom source database path
python migrate_to_mysql.py --source-path /path/to/database.db

# Enable debug logging
python migrate_to_mysql.py --log-level DEBUG
```

## Step 4: Update Application Configuration

After successful migration, update your application to use MySQL:

### Environment Variables

Set these environment variables:

```bash
export FLASK_ENV=development  # or production
export USE_MYSQL=true
export DB_HOST=192.168.11.1
export DB_PORT=3306
export DB_USER=remote_user
export DB_PASS=BuGr@d@N4@loB6!
export DB_NAME_DEV=nutri_tracker_dev
export DB_NAME_PROD=nutri_tracker_prod
```

### Docker Configuration

If using Docker, these are already configured in `docker-compose.yml`.

## Migration Process

The migration follows these steps:

1. **Schema Migration**: Creates all tables, indexes, and constraints in MySQL
2. **Data Migration**: Transfers all data from SQLite to MySQL in batches
3. **Verification**: Compares row counts between source and target databases
4. **Report Generation**: Creates a detailed JSON report of the migration

## Migration Reports

After migration, a detailed report is generated:
- `migration_report_YYYYMMDD_HHMMSS.json`: Contains migration statistics and verification results
- `migration_YYYYMMDD_HHMMSS.log`: Detailed log of the migration process

## Troubleshooting

### Connection Issues

1. **Docker network issues**:
   - Try using `network_mode: "host"` in docker-compose.yml
   - Or use the actual IP address instead of `host.docker.internal`

2. **Access denied errors**:
   - Verify MySQL user has proper permissions
   - Check if the user can connect from your host

3. **Database not found**:
   - The migration script will create databases automatically
   - Ensure the MySQL user has CREATE DATABASE permissions

### Migration Issues

1. **Foreign key errors**:
   - The migration temporarily disables foreign key checks
   - If issues persist, use `--drop-existing` to recreate tables

2. **Data type mismatches**:
   - Check migration logs for specific error messages
   - The migrator handles most SQLite to MySQL type conversions automatically

3. **Large datasets**:
   - Increase batch size with `--batch-size 10000`
   - Monitor MySQL connection timeouts

## Rollback

If you need to rollback to SQLite:

1. Stop the application
2. Set `USE_MYSQL=false`
3. Restart the application

The original SQLite database remains unchanged during migration.

## Monitoring

After migration, monitor:
- Application performance
- MySQL connection pool usage
- Query execution times
- Error logs for any database-related issues

## Next Steps

1. Update any direct SQL queries in the application to use MySQL syntax
2. Configure MySQL backups
3. Set up monitoring for the MySQL server
4. Consider implementing read replicas for scaling
