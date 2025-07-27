# app/utils/fallback_db.py
# Fallback database manager for basic SQLite operations

import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class FallbackDatabaseManager:
    """Basic SQLite database manager as fallback."""
    
    def __init__(self, db_path: str = 'job_management.db'):
        self.db_path = db_path
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like row access
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: List = None, fetch_one: bool = False):
        """Execute a query and return results."""
        if params is None:
            params = []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                if fetch_one:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                else:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows] if rows else []
            else:
                self.connection.commit()
                return cursor.lastrowid
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Query execution failed: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def insert(self, table: str, data: Dict) -> int:
        """Insert data into table and return ID."""
        try:
            # Convert data types
            converted_data = self._convert_data_types(data)
            
            columns = list(converted_data.keys())
            placeholders = ['?' for _ in columns]
            values = list(converted_data.values())
            
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            self.connection.commit()
            
            return cursor.lastrowid
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Insert failed: {str(e)}")
            logger.error(f"Table: {table}")
            logger.error(f"Data: {data}")
            raise
    
    def update(self, table: str, data: Dict, condition: str, params: List):
        """Update records in table."""
        try:
            converted_data = self._convert_data_types(data)
            
            set_clauses = [f"{key} = ?" for key in converted_data.keys()]
            values = list(converted_data.values()) + params
            
            query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {condition}"
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            self.connection.commit()
            
            return cursor.rowcount
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Update failed: {str(e)}")
            raise
    
    def select(self, table: str, fields: str = '*', condition: str = None, 
               params: List = None, order_by: str = None, limit: int = None):
        """Select records from table."""
        try:
            query = f"SELECT {fields} FROM {table}"
            
            if condition:
                query += f" WHERE {condition}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            return self.execute_query(query, params or [])
            
        except Exception as e:
            logger.error(f"Select failed: {str(e)}")
            raise
    
    def delete(self, table: str, condition: str, params: List):
        """Delete records from table."""
        try:
            query = f"DELETE FROM {table} WHERE {condition}"
            
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            
            return cursor.rowcount
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Delete failed: {str(e)}")
            raise
    
    def get_by_id(self, table: str, record_id: int):
        """Get a record by ID."""
        try:
            query = f"SELECT * FROM {table} WHERE id = ?"
            return self.execute_query(query, [record_id], fetch_one=True)
            
        except Exception as e:
            logger.error(f"Get by ID failed: {str(e)}")
            raise
    
    def record_exists(self, table: str, condition: str, params: List) -> bool:
        """Check if a record exists."""
        try:
            query = f"SELECT 1 FROM {table} WHERE {condition} LIMIT 1"
            result = self.execute_query(query, params, fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Record exists check failed: {str(e)}")
            raise
    
    def log_audit(self, user_id: int, action: str, entity_type: str, 
                  entity_id: int, changes: str, ip_address: str = None):
        """Log an audit entry."""
        try:
            audit_data = {
                'user_id': user_id,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'changes': changes,
                'ip_address': ip_address,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.insert('audit_logs', audit_data)
            
        except Exception as e:
            logger.error(f"Audit logging failed: {str(e)}")
            # Don't raise for audit logging failures
    
    def _convert_data_types(self, data: Dict) -> Dict:
        """Convert data types for SQLite compatibility."""
        converted = {}
        
        for key, value in data.items():
            if value is None:
                converted[key] = None
            elif hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
                # Convert Decimal to float
                converted[key] = float(value)
            elif isinstance(value, bool):
                # Convert boolean to integer for SQLite
                converted[key] = 1 if value else 0
            elif isinstance(value, (list, dict)):
                # Convert complex types to JSON
                converted[key] = json.dumps(value) if value else None
            else:
                converted[key] = value
        
        return converted
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


# Create fallback database instance
def get_fallback_db():
    """Get fallback database instance."""
    return FallbackDatabaseManager()