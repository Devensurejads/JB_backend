# app/utils/password_utils.py
# Improved password hashing utilities

import bcrypt
import logging
# from typing import str

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    try:
        # Ensure password is bytes
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password, salt)
        
        # Return as string
        return hashed.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password (str): Plain text password
        hashed_password (str): Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # Handle empty or None values
        if not password or not hashed_password:
            logger.warning("Empty password or hash provided")
            return False
        
        # Ensure inputs are proper format
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        
        # Verify password
        result = bcrypt.checkpw(password, hashed_password)
        return result
        
    except ValueError as e:
        logger.error(f"Invalid hash format: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False


def is_valid_hash(hashed_password: str) -> bool:
    """
    Check if a string is a valid bcrypt hash.
    
    Args:
        hashed_password (str): Hash to validate
        
    Returns:
        bool: True if valid bcrypt hash, False otherwise
    """
    try:
        if not hashed_password:
            return False
        
        # Bcrypt hashes start with $2a$, $2b$, $2x$, or $2y$
        if not hashed_password.startswith(('$2a$', '$2b$', '$2x$', '$2y$')):
            return False
        
        # Bcrypt hashes should be 60 characters long
        if len(hashed_password) != 60:
            return False
        
        return True
        
    except Exception:
        return False