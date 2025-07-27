# app/utils/db_compatibility.py
# Compatibility layer for database operations

import logging
from typing import List, Dict, Any, Optional, Union
import sqlite3

logger = logging.getLogger(__name__)

class DatabaseCompatibility:
    """Compatibility wrapper for database operations."""
    
    def __init__(self, db_instance):
        self.db = db_instance
    
    def execute_query(self, query: str, params: List = None, fetch_one: bool = False):
        """
        Execute a query with compatibility for different database abstraction layers.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Whether to fetch only one result
            
        Returns:
            Query results
        """
        if params is None:
            params = []
        
        try:
            # Try the expected method first
            if hasattr(self.db, 'execute_query'):
                return self.db.execute_query(query, params, fetch_one=fetch_one)
            
            # Try execute_sql method
            elif hasattr(self.db, 'execute_sql'):
                result = self.db.execute_sql(query, params)
                if fetch_one:
                    return result[0] if result else None
                else:
                    return result
            
            # Try query method
            elif hasattr(self.db, 'query'):
                result = self.db.query(query, params)
                if fetch_one:
                    return result[0] if result else None
                else:
                    return result
            
            # Handle context manager (with statement)
            elif hasattr(self.db, '__enter__') and hasattr(self.db, '__exit__'):
                with self.db as conn:
                    if hasattr(conn, 'cursor'):
                        cursor = conn.cursor()
                        cursor.execute(query, params)
                        if fetch_one:
                            row = cursor.fetchone()
                            return dict(row) if row else None
                        else:
                            rows = cursor.fetchall()
                            return [dict(row) for row in rows] if rows else []
                    elif hasattr(conn, 'execute'):
                        result = conn.execute(query, params)
                        if fetch_one:
                            row = result.fetchone()
                            return dict(row) if row else None
                        else:
                            rows = result.fetchall()
                            return [dict(row) for row in rows] if rows else []
            
            # Try get_connection method that returns context manager
            elif hasattr(self.db, 'get_connection'):
                conn_context = self.db.get_connection()
                if hasattr(conn_context, '__enter__'):
                    with conn_context as conn:
                        cursor = conn.cursor()
                        cursor.execute(query, params)
                        if fetch_one:
                            row = cursor.fetchone()
                            return dict(row) if row else None
                        else:
                            rows = cursor.fetchall()
                            return [dict(row) for row in rows] if rows else []
                else:
                    # Direct connection
                    cursor = conn_context.cursor()
                    cursor.execute(query, params)
                    if fetch_one:
                        row = cursor.fetchone()
                        return dict(row) if row else None
                    else:
                        rows = cursor.fetchall()
                        return [dict(row) for row in rows] if rows else []
            
            # Alternative method names
            elif hasattr(self.db, 'execute'):
                result = self.db.execute(query, params)
                if hasattr(result, 'fetchone'):
                    if fetch_one:
                        row = result.fetchone()
                        return dict(row) if row else None
                    else:
                        rows = result.fetchall()
                        return [dict(row) for row in rows] if rows else []
                else:
                    return result
            
            # Raw SQLite connection
            elif hasattr(self.db, 'connection'):
                conn = self.db.connection
                if hasattr(conn, '__enter__'):
                    with conn as cursor:
                        cursor.execute(query, params)
                        if fetch_one:
                            row = cursor.fetchone()
                            return dict(row) if row else None
                        else:
                            rows = cursor.fetchall()
                            return [dict(row) for row in rows] if rows else []
                else:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    if fetch_one:
                        row = cursor.fetchone()
                        return dict(row) if row else None
                    else:
                        rows = cursor.fetchall()
                        return [dict(row) for row in rows] if rows else []
            
            # Direct connection
            elif hasattr(self.db, 'cursor'):
                cursor = self.db.cursor()
                cursor.execute(query, params)
                if fetch_one:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                else:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows] if rows else []
            
            else:
                # Last resort: try to access the underlying database connection
                logger.error(f"Available methods in db object: {dir(self.db)}")
                logger.error(f"DB object type: {type(self.db)}")
                raise AttributeError("No compatible database execution method found")
                
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            logger.error(f"DB object type: {type(self.db)}")
            raise
    
    def select_custom(self, query: str, params: List = None):
        """Execute a custom SELECT query."""
        return self.execute_query(query, params, fetch_one=False)
    
    def insert(self, table: str, data: Dict) -> Optional[int]:
        """
        Insert data into table with proper type conversion.
        
        Args:
            table: Table name
            data: Data to insert
            
        Returns:
            Inserted record ID
        """
        try:
            # Convert data types for SQLite compatibility
            converted_data = self._convert_data_types(data)
            
            # Use existing insert method if available
            if hasattr(self.db, 'insert'):
                return self.db.insert(table, converted_data)
            
            # Manual insert
            columns = list(converted_data.keys())
            placeholders = ['?' for _ in columns]
            values = list(converted_data.values())
            
            query = f"""
                INSERT INTO {table} ({', '.join(columns)}) 
                VALUES ({', '.join(placeholders)})
            """
            
            if hasattr(self.db, 'connection'):
                cursor = self.db.connection.cursor()
                cursor.execute(query, values)
                self.db.connection.commit()
                return cursor.lastrowid
            else:
                raise AttributeError("No compatible database insert method found")
                
        except Exception as e:
            logger.error(f"Database insert error: {str(e)}")
            logger.error(f"Table: {table}")
            logger.error(f"Data: {data}")
            raise
    
    def update(self, table: str, data: Dict, condition: str, params: List):
        """Update records in table."""
        try:
            converted_data = self._convert_data_types(data)
            
            if hasattr(self.db, 'update'):
                return self.db.update(table, converted_data, condition, params)
            
            # Manual update
            set_clauses = [f"{key} = ?" for key in converted_data.keys()]
            values = list(converted_data.values()) + params
            
            query = f"""
                UPDATE {table} 
                SET {', '.join(set_clauses)} 
                WHERE {condition}
            """
            
            return self.execute_query(query, values)
            
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")
            raise
    
    def select(self, table: str, fields: str = '*', condition: str = None, 
               params: List = None, order_by: str = None, limit: int = None):
        """Select records from table."""
        try:
            if hasattr(self.db, 'select'):
                return self.db.select(table, fields, condition, params, order_by, limit)
            
            # Manual select
            query = f"SELECT {fields} FROM {table}"
            
            if condition:
                query += f" WHERE {condition}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            return self.execute_query(query, params or [])
            
        except Exception as e:
            logger.error(f"Database select error: {str(e)}")
            raise
    
    def delete(self, table: str, condition: str, params: List):
        """Delete records from table."""
        try:
            if hasattr(self.db, 'delete'):
                return self.db.delete(table, condition, params)
            
            query = f"DELETE FROM {table} WHERE {condition}"
            return self.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Database delete error: {str(e)}")
            raise
    
    def get_by_id(self, table: str, record_id: int):
        """Get a record by ID."""
        try:
            if hasattr(self.db, 'get_by_id'):
                return self.db.get_by_id(table, record_id)
            
            query = f"SELECT * FROM {table} WHERE id = ?"
            return self.execute_query(query, [record_id], fetch_one=True)
            
        except Exception as e:
            logger.error(f"Database get_by_id error: {str(e)}")
            raise
    
    def record_exists(self, table: str, condition: str, params: List) -> bool:
        """Check if a record exists."""
        try:
            if hasattr(self.db, 'record_exists'):
                return self.db.record_exists(table, condition, params)
            
            query = f"SELECT 1 FROM {table} WHERE {condition} LIMIT 1"
            result = self.execute_query(query, params, fetch_one=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"Database record_exists error: {str(e)}")
            raise
    
    def log_audit(self, user_id: int, action: str, entity_type: str, 
                  entity_id: int, changes: str, ip_address: str = None):
        """Log an audit entry."""
        try:
            if hasattr(self.db, 'log_audit'):
                return self.db.log_audit(user_id, action, entity_type, entity_id, changes, ip_address)
            
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
            logger.error(f"Audit logging error: {str(e)}")
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


# Create a global compatible database instance
def get_compatible_db():
    """Get a compatible database instance."""
    from app.utils.db_abstraction import db
    return DatabaseCompatibility(db)