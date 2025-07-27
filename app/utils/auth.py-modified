# app/utils/auth.py

import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, g
from typing import Dict, Optional, Callable

# Configure logging
logger = logging.getLogger(__name__)


def extract_token_from_request() -> Optional[str]:
    """
    Extract JWT token from request headers.
    
    Returns:
        Optional[str]: JWT token if found
    """
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    return None


def verify_token(token: str) -> tuple[bool, Optional[Dict]]:
    """
    Verify JWT token and return payload.
    
    Args:
        token (str): JWT token
        
    Returns:
        tuple[bool, Optional[Dict]]: (is_valid, payload)
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        
        # Check if token is expired
        if payload.get('exp', 0) < datetime.utcnow().timestamp():
            logger.warning("Token has expired")
            return False, None
        
        return True, payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return False, None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return False, None


def generate_token(user_data: Dict) -> str:
    """
    Generate JWT token for user.
    
    Args:
        user_data (Dict): User data to include in token
        
    Returns:
        str: JWT token
    """
    try:
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'exp': datetime.utcnow() + timedelta(
                seconds=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
            ),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise


def get_current_user() -> Optional[Dict]:
    """
    Get current authenticated user from request context.
    
    Returns:
        Optional[Dict]: Current user data
    """
    return getattr(request, 'current_user', None)


def login_required(f: Callable) -> Callable:
    """
    Decorator to require user authentication.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token_from_request()
        
        if not token:
            logger.warning("No token provided for protected route")
            return jsonify({
                'success': False,
                'message': 'Authentication required',
                'data': None
            }), 401
        
        is_valid, payload = verify_token(token)
        
        if not is_valid or not payload:
            logger.warning("Invalid token provided for protected route")
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token',
                'data': None
            }), 401
        
        # Check if user is active
        from app.utils.db_abstraction import db
        user = db.get_by_id('users', payload['user_id'])
        if not user or not user.get('is_active', False):
            logger.warning(f"Inactive user attempted access: {payload.get('username')}")
            return jsonify({
                'success': False,
                'message': 'Account is inactive',
                'data': None
            }), 401
        
        # Store user info in request context
        request.current_user = payload
        g.current_user = payload
        
        return f(*args, **kwargs)
    
    return decorated_function


def role_required(required_roles: list) -> Callable:
    """
    Decorator to require specific roles.
    
    Args:
        required_roles (list): List of required roles
        
    Returns:
        Callable: Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required',
                    'data': None
                }), 401
            
            user_role = user.get('role')
            
            if user_role not in required_roles:
                logger.warning(f"Insufficient permissions for user {user.get('username')}: {user_role} not in {required_roles}")
                return jsonify({
                    'success': False,
                    'message': 'Insufficient permissions',
                    'data': None
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin role.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required(['admin', 'superadmin'])(f)


def staff_required(f: Callable) -> Callable:
    """
    Decorator to require staff role or higher.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required(['staff', 'admin', 'superadmin'])(f)


def superadmin_required(f: Callable) -> Callable:
    """
    Decorator to require superadmin role.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required(['superadmin'])(f)


def employer_required(f: Callable) -> Callable:
    """
    Decorator to require employer role or higher.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required(['employer', 'staff', 'admin', 'superadmin'])(f)


def employee_required(f: Callable) -> Callable:
    """
    Decorator to require employee role or higher (any authenticated user).
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required(['employee', 'employer', 'staff', 'admin', 'superadmin'])(f)


def employee_or_higher(f: Callable) -> Callable:
    """
    Decorator to require employee role or higher (any authenticated user).
    This is an alias for employee_required for backward compatibility.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return employee_required(f)


def check_permission(user_role: str, required_roles: list) -> bool:
    """
    Check if user role has required permissions.
    
    Args:
        user_role (str): User's role
        required_roles (list): List of required roles
        
    Returns:
        bool: Whether user has permission
    """
    return user_role in required_roles


def is_admin(user: Dict = None) -> bool:
    """
    Check if current user is admin.
    
    Args:
        user (Dict, optional): User data (uses current user if not provided)
        
    Returns:
        bool: Whether user is admin
    """
    if not user:
        user = get_current_user()
    
    if not user:
        return False
    
    return user.get('role') in ['admin', 'superadmin']


def is_superadmin(user: Dict = None) -> bool:
    """
    Check if current user is superadmin.
    
    Args:
        user (Dict, optional): User data (uses current user if not provided)
        
    Returns:
        bool: Whether user is superadmin
    """
    if not user:
        user = get_current_user()
    
    if not user:
        return False
    
    return user.get('role') == 'superadmin'


def can_access_user_data(target_user_id: int, user: Dict = None) -> bool:
    """
    Check if current user can access another user's data.
    
    Args:
        target_user_id (int): ID of user whose data is being accessed
        user (Dict, optional): Current user data
        
    Returns:
        bool: Whether access is allowed
    """
    if not user:
        user = get_current_user()
    
    if not user:
        return False
    
    # Users can access their own data
    if user.get('user_id') == target_user_id:
        return True
    
    # Admins and staff can access any user data
    if user.get('role') in ['admin', 'superadmin', 'staff']:
        return True
    
    return False


def get_role_hierarchy() -> Dict[str, int]:
    """
    Get role hierarchy levels.
    
    Returns:
        Dict[str, int]: Role hierarchy mapping
    """
    return {
        'employee': 1,
        'employer': 2,
        'staff': 3,
        'admin': 4,
        'superadmin': 5
    }


def role_level(role: str) -> int:
    """
    Get numeric level for role.
    
    Args:
        role (str): Role name
        
    Returns:
        int: Role level
    """
    hierarchy = get_role_hierarchy()
    return hierarchy.get(role, 0)


def has_higher_role(user_role: str, target_role: str) -> bool:
    """
    Check if user role is higher than target role.
    
    Args:
        user_role (str): User's role
        target_role (str): Target role to compare
        
    Returns:
        bool: Whether user role is higher
    """
    return role_level(user_role) > role_level(target_role)


def optional_auth(f: Callable) -> Callable:
    """
    Decorator for optional authentication (doesn't fail if no token).
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token_from_request()
        
        if token:
            is_valid, payload = verify_token(token)
            if is_valid and payload:
                # Check if user is active
                from app.utils.db_abstraction import db
                user = db.get_by_id('users', payload['user_id'])
                
                if user and user.get('is_active', False):
                    request.current_user = payload
                    g.current_user = payload
        
        return f(*args, **kwargs)
    
    return decorated_function


class AuthMiddleware:
    """Middleware class for authentication (future use)."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.before_request(self.before_request)
    
    def before_request(self):
        """Process request before route handler."""
        # Future implementation for request preprocessing
        pass