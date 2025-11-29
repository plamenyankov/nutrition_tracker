import mysql.connector
from mysql.connector import pooling
import os
import logging
from contextlib import contextmanager
from typing import Optional, Union, Dict, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_database_config, DatabaseConfig, ensure_database_exists

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """MySQL-only database connection manager"""

    def __init__(self):
        self.config = get_database_config()
        self.connection_pool = None

        # Ensure database exists before creating pool
        if ensure_database_exists(self.config):
            self._init_mysql_pool()
        else:
            logger.error("Failed to ensure database exists")
            raise Exception("Cannot connect to MySQL database")

    def _init_mysql_pool(self):
        """Initialize MySQL connection pool"""
        try:
            pool_config = {
                'pool_name': f'{self.config.database}_pool',
                'pool_size': self.config.pool_size,
                'pool_reset_session': True,
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'user': self.config.username,
                'password': self.config.password,
                'charset': self.config.charset,
                'autocommit': self.config.autocommit,
                'time_zone': '+00:00',
                'ssl_disabled': self.config.ssl_disabled
            }
            
            # Configure SSL for DigitalOcean databases
            if not self.config.ssl_disabled:
                # DigitalOcean requires SSL but doesn't require certificate verification
                pool_config['ssl_verify_cert'] = False
                pool_config['ssl_verify_identity'] = False

            self.connection_pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"MySQL connection pool initialized for {self.config.database} at {self.config.host}:{self.config.port}")

        except mysql.connector.Error as e:
            logger.error(f"Failed to initialize MySQL connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get MySQL database connection (context manager)"""
        connection = None
        try:
            if self.connection_pool is None:
                raise Exception("Connection pool not initialized")
            connection = self.connection_pool.get_connection()
            # Ensure connection is in a clean state
            if connection.is_connected():
                pass  # Connection autocommit is handled by pool config
            yield connection
        except mysql.connector.Error as e:
            if connection and connection.is_connected():
                try:
                    connection.rollback()
                except:
                    pass
            logger.error(f"MySQL connection error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                try:
                    # Ensure all pending results are consumed
                    try:
                        # Try to get any unread results
                        connection.get_warnings()
                    except:
                        pass
                    # Commit any pending transactions
                    connection.commit()
                except:
                    pass
                finally:
                    connection.close()

    def execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute query with automatic connection management"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            try:
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount

                conn.commit()
                return result

            except Exception as e:
                conn.rollback()
                logger.error(f"Query execution error: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise
            finally:
                cursor.close()

    def execute_many(self, query: str, params_list: list):
        """Execute query multiple times with different parameters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                logger.error(f"Execute many error: {e}")
                raise
            finally:
                cursor.close()

    def get_table_info(self) -> Dict[str, Any]:
        """Get information about all tables in the database"""
        tables = {}

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # MySQL table info
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
            """, (self.config.database,))

            for row in cursor.fetchall():
                tables[row[0]] = {
                    'row_count': row[1],
                    'data_size': row[2],
                    'index_size': row[3]
                }

            cursor.close()

        return tables

    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        return {
            'type': 'MySQL',
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'pool_size': self.config.pool_size
        }

    def cleanup_connections(self):
        """Clean up connection pool"""
        if self.connection_pool:
            try:
                # MySQL connector doesn't have explicit pool cleanup
                logger.info("Connection pool cleanup requested")
            except Exception as e:
                logger.error(f"Error during connection cleanup: {e}")

    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup_connections()
        except:
            pass

# Global instance
_db_manager = None

def get_db_manager() -> DatabaseConnectionManager:
    """Get singleton database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
    return _db_manager
