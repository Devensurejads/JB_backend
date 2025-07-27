# app/utils/db_abstraction.py

import sqlite3
import json
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
import os

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database abstraction layer providing CRUD operations, transaction management,
    and audit logging for SQLite with potential PostgreSQL migration support.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database manager.
        
        Args:
            db_path (str): Path to SQLite database file
        """
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'job_management.db')
        self._local = threading.local()
        self._ensure_database_exists()
    
    def _convert_datetime_to_string(self, value):
        """Convert datetime object to string, handle if already string."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, str):
            return value  # Already a string
        return value
    
    def _ensure_database_exists(self):
        """Ensure database file and directory exist."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        # Create database file if it doesn't exist
        if not os.path.exists(self.db_path):
            open(self.db_path, 'a').close()
    
    @contextmanager
    def get_connection(self, commit: bool = True):
        """
        Get database connection with automatic transaction management.
        
        Args:
            commit (bool): Whether to commit transaction automatically
            
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
            yield conn
            if commit:
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_script(self, script: str) -> bool:
        """
        Execute SQL script (for initialization).
        
        Args:
            script (str): SQL script content
            
        Returns:
            bool: Success status
        """
        try:
            with self.get_connection() as conn:
                conn.executescript(script)
                logger.info("Database script executed successfully")
                return True
        except Exception as e:
            logger.error(f"Error executing database script: {str(e)}")
            return False
    
    def insert(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a record and return the ID.
        
        Args:
            table (str): Table name
            data (Dict): Data to insert
            
        Returns:
            Optional[int]: Inserted record ID
        """
        try:
            # Filter out None values and prepare data
            clean_data = {}
            for k, v in data.items():
                
                if v is not None:
                    # Convert datetime objects to ISO format strings for SQLite
                    clean_data[k] = self._convert_datetime_to_string(v)

            if not clean_data:
                logger.warning("No data provided for insertion")
                return None
            
            # Build query
            columns = ', '.join(clean_data.keys())
            placeholders = ', '.join(['?' for _ in clean_data])
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            with self.get_connection() as conn:
                cursor = conn.execute(query, list(clean_data.values()))
                record_id = cursor.lastrowid
                logger.debug(f"Inserted record in {table} with ID: {record_id}")
                return record_id
                
        except Exception as e:
            logger.error(f"Error inserting into {table}: {str(e)}")
            return None
    
    def update(self, table: str, data: Dict[str, Any], condition: str, params: List = None) -> bool:
        """
        Update records.
        
        Args:
            table (str): Table name
            data (Dict): Data to update
            condition (str): WHERE condition
            params (List): Parameters for condition
            
        Returns:
            bool: Success status
        """
        try:
            # Filter out None values and handle datetime objects
            clean_data = {}
            for k, v in data.items():
                if v is not None:
                    # Convert datetime objects to ISO format strings for SQLite
                    clean_data[k] = self._convert_datetime_to_string(v)
            
            if not clean_data:
                logger.warning("No data provided for update")
                return False
            
            # Build query
            set_clause = ', '.join([f"{k} = ?" for k in clean_data.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
            
            # Combine update values with condition parameters
            all_params = list(clean_data.values()) + (params or [])
            
            with self.get_connection() as conn:
                cursor = conn.execute(query, all_params)
                affected_rows = cursor.rowcount
                logger.debug(f"Updated {affected_rows} records in {table}")
                return affected_rows > 0
                
        except Exception as e:
            logger.error(f"Error updating {table}: {str(e)}")
            return False
    
    def delete(self, table: str, condition: str, params: List = None) -> bool:
        """
        Delete records.
        
        Args:
            table (str): Table name
            condition (str): WHERE condition
            params (List): Parameters for condition
            
        Returns:
            bool: Success status
        """
        try:
            query = f"DELETE FROM {table} WHERE {condition}"
            
            with self.get_connection() as conn:
                cursor = conn.execute(query, params or [])
                affected_rows = cursor.rowcount
                logger.debug(f"Deleted {affected_rows} records from {table}")
                return affected_rows > 0
                
        except Exception as e:
            logger.error(f"Error deleting from {table}: {str(e)}")
            return False
    
    def select(self, table: str, fields: List[str] = None, condition: str = None, 
               params: List = None, order_by: str = None, limit: Union[int, str] = None) -> Optional[List[Dict]]:
        """
        Select records.
        
        Args:
            table (str): Table name
            fields (List[str]): Fields to select
            condition (str): WHERE condition
            params (List): Parameters for condition
            order_by (str): ORDER BY clause
            limit (Union[int, str]): LIMIT clause
            
        Returns:
            Optional[List[Dict]]: Selected records
        """
        try:
            # Build query
            fields_str = ', '.join(fields) if fields else '*'
            query = f"SELECT {fields_str} FROM {table}"
            
            if condition:
                query += f" WHERE {condition}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
            with self.get_connection() as conn:
                cursor = conn.execute(query, params or [])
                rows = cursor.fetchall()
                # Convert to list of dictionaries
                result = [dict(row) for row in rows]
                logger.debug(f"Selected {len(result)} records from {table}")
                return result
                
        except Exception as e:
            # logger.error(f"Error selecting from {table}: {str(e)}")
            print(f"Error selecting from {table}: {str(e)}")
            return None
    
    def get_by_id(self, table: str, record_id: int) -> Optional[Dict]:
        """
        Get a record by ID.
        
        Args:
            table (str): Table name
            record_id (int): Record ID
            
        Returns:
            Optional[Dict]: Record data
        """
        try:
            records = self.select(table, condition='id = ?', params=[record_id])
            if records:
                return records[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting record from {table} with ID {record_id}: {str(e)}")
            return None
    
    def record_exists(self, table: str, condition: str, params: List = None) -> bool:
        """
        Check if a record exists.
        
        Args:
            table (str): Table name
            condition (str): WHERE condition
            params (List): Parameters for condition
            
        Returns:
            bool: Whether record exists
        """
        try:
            records = self.select(table, fields=['1'], condition=condition, params=params, limit=1)
            return bool(records)
            
        except Exception as e:
            logger.error(f"Error checking record existence in {table}: {str(e)}")
            return False
    
    def log_audit(self, user_id: Optional[int], action: str, entity_type: str, 
                  entity_id: Optional[int], changes: Dict = None, ip_address: str = None) -> bool:
        """
        Log an audit entry.
        
        Args:
            user_id (Optional[int]): User performing the action
            action (str): Action performed (CREATE, UPDATE, DELETE, etc.)
            entity_type (str): Type of entity (user, job, etc.)
            entity_id (Optional[int]): ID of the entity
            changes (Dict): Changes made
            ip_address (str): IP address of the request
            
        Returns:
            bool: Success status
        """
        try:
            audit_data = {
                'user_id': user_id,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'changes': json.dumps(changes) if changes else None,
                'ip_address': ip_address,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            audit_id = self.insert('audit_logs', audit_data)
            if audit_id:
                logger.debug(f"Audit log created: {action} on {entity_type}:{entity_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            return False
    
    def execute_raw_query(self, query: str, params: List = None, fetch: bool = True) -> Optional[Any]:
        """
        Execute raw SQL query.
        
        Args:
            query (str): SQL query
            params (List): Query parameters
            fetch (bool): Whether to fetch results
            
        Returns:
            Optional[Any]: Query results or success status
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params or [])
                
                if fetch:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    return cursor.rowcount > 0
                    
        except Exception as e:
            logger.error(f"Error executing raw query: {str(e)}")
            return None
    
    def get_table_info(self, table: str) -> Optional[List[Dict]]:
        """
        Get table schema information.
        
        Args:
            table (str): Table name
            
        Returns:
            Optional[List[Dict]]: Table schema info
        """
        try:
            return self.execute_raw_query(f"PRAGMA table_info({table})")
        except Exception as e:
            logger.error(f"Error getting table info for {table}: {str(e)}")
            return None


# Global database instance
db = DatabaseManager()


def execute_sql_files():
    # conn = sqlite3.connect(db_path)
    # cursor = conn.cursor()

    sql_folder = os.path.join(os.path.dirname(__file__), '..', 'models')

    file_cnt = 0
    print(f"execute_sql_files: Executing sql files")
    for filename in sorted(os.listdir(sql_folder)):
        if filename.endswith('.sql'):
            with open(os.path.join(sql_folder, filename), 'r') as f:
                try:
                    # print(f"reading sql file {os.path.join(sql_folder, filename)}")
                    sql = f.read()
                    file_cnt += 1
                    print(f"{file_cnt} - {filename}")
                    success = db.execute_script(sql)  # Use .execute() if single statements
                    if success:
                        logger.info("Database initialized successfully")
                    else:
                        logger.error("Failed to initialize database")
                except Exception as e:
                    logger.error(f"Error reading schema file: {str(e)}")

    # conn.commit()
    # conn.close()

def init_db():
    """Initialize database with schema."""
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'schema.sql')
    
    if os.path.exists(schema_path):
        try:
            print(f"reading sql file {schema_path}")
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            success = db.execute_script(schema_sql)
            if success:
                logger.info("Database initialized successfully")
            else:
                logger.error("Failed to initialize database")
        except Exception as e:
            logger.error(f"Error reading schema file: {str(e)}")
    else:
        logger.warning(f"Schema file not found at {schema_path}")


def reset_db():
    """Reset database (for development/testing)."""
    try:
        if os.path.exists(db.db_path):
            os.remove(db.db_path)
            logger.info("Database file removed")
        
        # init_db()
        execute_sql_files()
        logger.info("Database reset completed")
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")


# Connection pool for advanced usage (future PostgreSQL migration)
class ConnectionPool:
    """Database connection pool (placeholder for PostgreSQL migration)."""
    
    def __init__(self, database_url: str, min_connections: int = 1, max_connections: int = 20):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        # Implementation would go here for PostgreSQL
    
    def get_connection(self):
        """Get connection from pool."""
        # Implementation would go here for PostgreSQL
        pass
    
    def return_connection(self, conn):
        """Return connection to pool."""
        # Implementation would go here for PostgreSQL
        pass