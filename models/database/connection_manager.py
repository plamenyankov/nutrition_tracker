import mysql.connector
from mysql.connector import pooling
import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Optional, Union, Dict, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_database_config, DatabaseConfig, ensure_database_exists

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Unified database connection manager supporting both SQLite and MySQL"""

    def __init__(self, use_mysql: bool = None, sqlite_path: str = None):
        self.use_mysql = use_mysql if use_mysql is not None else os.getenv('USE_MYSQL', 'false').lower() == 'true'
        self.sqlite_path = sqlite_path or os.getenv('DATABASE_PATH', 'database.db')
        self.config = None
        self.connection_pool = None

        if self.use_mysql:
            self.config = get_database_config()
            # Ensure database exists before creating pool
            if ensure_database_exists(self.config):
                self._init_mysql_pool()
            else:
                logger.error("Failed to ensure database exists, falling back to SQLite")
                self.use_mysql = False

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

            self.connection_pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"MySQL connection pool initialized for {self.config.database} at {self.config.host}:{self.config.port}")

        except mysql.connector.Error as e:
            logger.error(f"Failed to initialize MySQL connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get database connection (context manager)"""
        if self.use_mysql:
            connection = None
            try:
                connection = self.connection_pool.get_connection()
                # Ensure connection is in a clean state
                if connection.is_connected():
                    connection.autocommit = False
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
        else:
            # SQLite fallback
            connection = sqlite3.connect(self.sqlite_path)
            connection.row_factory = sqlite3.Row  # Enable column access by name
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA foreign_keys=ON")
                yield connection
            except sqlite3.Error as e:
                connection.rollback()
                logger.error(f"SQLite connection error: {e}")
                raise
            finally:
                connection.close()

    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute query with automatic connection management"""
        with self.get_connection() as conn:
            if self.use_mysql:
                cursor = conn.cursor(dictionary=True)
            else:
                cursor = conn.cursor()

            try:
                if params:
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

            if self.use_mysql:
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
            else:
                # SQLite table info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                table_names = [row[0] for row in cursor.fetchall()]

                for table_name in table_names:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    tables[table_name] = {'row_count': row_count}

            cursor.close()

        return tables

    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if self.use_mysql:
                    cursor.execute("SELECT 1")
                else:
                    cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def cleanup_connections(self):
        """Cleanup and reset connection pool"""
        if self.use_mysql and self.connection_pool:
            try:
                # Close all connections in the pool
                while True:
                    try:
                        conn = self.connection_pool.get_connection(timeout=1)
                        if conn.is_connected():
                            conn.close()
                    except:
                        break
                logger.info("Connection pool cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up connections: {e}")

    def __del__(self):
        """Cleanup when manager is destroyed"""
        try:
            self.cleanup_connections()
        except:
            pass

# Global connection manager instance (will be initialized when needed)
_db_manager = None

def get_db_manager(use_mysql: bool = None, sqlite_path: str = None) -> DatabaseConnectionManager:
    """Get or create database connection manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager(use_mysql=use_mysql, sqlite_path=sqlite_path)
    return _db_manager
