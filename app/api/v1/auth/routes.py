# app/api/v1/auth/routes.py

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from app.services.auth_service import AuthService, auth_service

from app.schemas.auth_schema import (
    UserRegistrationSchema, UserLoginSchema, UserUpdateSchema,
    PasswordChangeSchema, UserListFilterSchema, RoleUpdateSchema,
    BulkUserActionSchema, PasswordResetSchema
)
from app.utils.auth import login_required, admin_required, staff_required

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


def get_client_ip():
    """Get client IP address from request."""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR', 'unknown')

def create_response(success: bool, message: str, data=None, status_code: int = None):
    """Create standardized API response."""
    if status_code is None:
        status_code = 200 if success else 400
    
    response = {
        'success': success,
        'message': message,
        'data': data
    }
    
    return jsonify(response), status_code

def create_error_response(message: str, status_code: int = 400, errors: dict = None):
    """Create standardized error response."""
    response = {
        'success': False,
        'message': message,
        'data': None
    }
    if errors:
        response['errors'] = errors
    
    return jsonify(response), status_code


def create_success_response(message: str, data: dict = None, status_code: int = 200):
    """Create standardized success response."""
    response = {
        'success': True,
        'message': message,
        'data': data
    }
    
    return jsonify(response), status_code


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Returns:
        JSON response with registration status and user data
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        # Get client IP
        ip_address = get_client_ip()
        
        # Get current user ID if authenticated (for admin creating accounts)
        current_user_id = getattr(request, 'current_user', {}).get('user_id')
        
        # Register user
        success, message, user_data = AuthService.register_user(
            data, 
            created_by_user_id=current_user_id,
            ip_address=ip_address
        )
        
        if success:
            logger.info(f"User registration successful: {user_data.get('username') if user_data else 'unknown'}")
            return create_success_response(message, user_data, 201)
        else:
            logger.warning(f"User registration failed: {message}")
            return create_error_response(message, 400)
    
    except ValidationError as e:
        logger.warning(f"User registration validation error: {e.messages}")
        return create_error_response("Validation failed", 400, e.messages)
    
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        return create_error_response("Registration failed", 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token.
    
    Returns:
        JSON response with authentication status and token
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return create_error_response("No data provided", 400)
        
        # Get client IP
        ip_address = get_client_ip()
        
        # Authenticate user
        # success, message, auth_data = AuthService.authenticate_user(data, ip_address)
        # Authenticate user
        success, message, auth_data = auth_service.login(
            credentials=data,
            ip_address=ip_address
        )

        if success:
            logger.info(f"User login successful: {auth_data['user']['username'] if auth_data else 'unknown'}")
            return create_success_response(message, auth_data)
        else:
            logger.warning(f"User login failed: {message}")
            return create_error_response(message, 401)
    
    except ValidationError as e:
        logger.warning(f"User login validation error: {e.messages}")
        return create_error_response("Validation failed", 400, e.messages)
    
    except Exception as e:
        logger.error(f"User login error: {str(e)}")
        return create_error_response("Login failed", 500)


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """
    Get current user profile.
    
    Returns:
        JSON response with user profile data
    """
    try:
        user_id = request.current_user['user_id']
        
        # Get user profile
        success, message, user_data = AuthService.get_user_profile(user_id)
        
        if success:
            return create_success_response(message, user_data)
        else:
            return create_error_response(message, 404)
    
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return create_error_response("Failed to retrieve profile", 500)


@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    Update current user profile.
    
    Returns:
        JSON response with updated user profile data
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        user_id = request.current_user['user_id']
        ip_address = get_client_ip()
        
        # Update user profile
        success, message, user_data = AuthService.update_user_profile(
            user_id, 
            data, 
            user_id,  # User updating their own profile
            ip_address
        )
        
        if success:
            logger.info(f"User profile updated: {user_id}")
            return create_success_response(message, user_data)
        else:
            return create_error_response(message, 400)
    
    except ValidationError as e:
        logger.warning(f"Profile update validation error: {e.messages}")
        return create_error_response("Validation failed", 400, e.messages)
    
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return create_error_response("Profile update failed", 500)


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change user password.
    
    Returns:
        JSON response with password change status
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        user_id = request.current_user['user_id']
        ip_address = get_client_ip()
        
        # Change password
        success, message = AuthService.change_password(user_id, data, ip_address)
        
        if success:
            logger.info(f"Password changed for user: {user_id}")
            return create_success_response(message)
        else:
            return create_error_response(message, 400)
    
    except ValidationError as e:
        logger.warning(f"Password change validation error: {e.messages}")
        return create_error_response("Validation failed", 400, e.messages)
    
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return create_error_response("Password change failed", 500)


@auth_bp.route('/users', methods=['GET'])
@staff_required
def list_users():
    """
    List users with optional filtering and pagination.
    
    Returns:
        JSON response with users list and pagination info
    """
    try:
        # Get query parameters
        args = request.args.to_dict()
        
        # Validate filters
        try:
            filter_schema = UserListFilterSchema()
            filters = filter_schema.load(args)
        except ValidationError as e:
            return create_error_response("Invalid filter parameters", 400, e.messages)
        
        # Extract pagination parameters
        page = filters.pop('page', 1)
        per_page = filters.pop('per_page', 20)
        
        # List users
        success, message, users_data = AuthService.list_users(filters, page, per_page)
        
        if success:
            return create_success_response(message, users_data)
        else:
            return create_error_response(message, 400)
    
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return create_error_response("Failed to retrieve users", 500)


@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@staff_required
def get_user(user_id):
    """
    Get specific user by ID.
    
    Args:
        user_id (int): User ID
        
    Returns:
        JSON response with user data
    """
    try:
        # Get user profile
        success, message, user_data = AuthService.get_user_profile(user_id)
        
        if success:
            return create_success_response(message, user_data)
        else:
            return create_error_response(message, 404)
    
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return create_error_response("Failed to retrieve user", 500)


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """
    Update specific user by ID (admin only).
    
    Args:
        user_id (int): User ID
        
    Returns:
        JSON response with updated user data
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        current_user_id = request.current_user['user_id']
        ip_address = get_client_ip()
        
        # Update user
        success, message, user_data = AuthService.update_user_profile(
            user_id, 
            data, 
            current_user_id,
            ip_address
        )
        
        if success:
            logger.info(f"User updated by admin: {user_id}")
            return create_success_response(message, user_data)
        else:
            return create_error_response(message, 400)
    
    except ValidationError as e:
        logger.warning(f"User update validation error: {e.messages}")
        return create_error_response("Validation failed", 400, e.messages)
    
    except Exception as e:
        logger.error(f"User update error: {str(e)}")
        return create_error_response("User update failed", 500)


@auth_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    """
    Deactivate specific user by ID (admin only).
    
    Args:
        user_id (int): User ID
        
    Returns:
        JSON response with deactivation status
    """
    try:
        current_user_id = request.current_user['user_id']
        ip_address = get_client_ip()
        
        # Prevent self-deactivation
        if user_id == current_user_id:
            return create_error_response("Cannot deactivate your own account", 400)
        
        # Deactivate user
        success, message = AuthService.deactivate_user(user_id, current_user_id, ip_address)
        
        if success:
            logger.info(f"User deactivated by admin: {user_id}")
            return create_success_response(message)
        else:
            return create_error_response(message, 400)
    
    except Exception as e:
        logger.error(f"User deactivation error: {str(e)}")
        return create_error_response("User deactivation failed", 500)


@auth_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    """
    Activate specific user by ID (admin only).
    
    Args:
        user_id (int): User ID
        
    Returns:
        JSON response with activation status
    """
    try:
        current_user_id = request.current_user['user_id']
        ip_address = get_client_ip()
        
        # Update user status to active
        from app.utils.db_abstraction import db
        from datetime import datetime
        
        def get_current_timestamp():
            return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        success = db.update(
            'users',
            {'is_active': 1, 'updated_at': get_current_timestamp()},  # Use 1 for SQLite boolean
            'id = ?',
            [user_id]
        )
        
        if success:
            # Log the activation
            db.log_audit(
                user_id=current_user_id,
                action='UPDATE',
                entity_type='user',
                entity_id=user_id,
                changes={'action': 'user_activation', 'is_active': {'old': False, 'new': True}},
                ip_address=ip_address
            )
            
            logger.info(f"User activated by admin: {user_id}")
            return create_success_response("User activated successfully")
        else:
            return create_error_response("Failed to activate user", 400)
    
    except Exception as e:
        logger.error(f"User activation error: {str(e)}")
        return create_error_response("User activation failed", 500)


@auth_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    """
    Update user role (admin only).
    
    Args:
        user_id (int): User ID
        
    Returns:
        JSON response with role update status
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        # Validate role data
        try:
            role_schema = RoleUpdateSchema()
            validated_data = role_schema.load(data)
        except ValidationError as e:
            return create_error_response("Validation failed", 400, e.messages)
        
        current_user_id = request.current_user['user_id']
        ip_address = get_client_ip()
        
        # Prevent changing own role to non-admin
        if user_id == current_user_id and validated_data['role'] not in ['admin', 'superadmin']:
            return create_error_response("Cannot remove admin privileges from your own account", 400)
        
        # Update user role
        success, message, user_data = AuthService.update_user_profile(
            user_id,
            {'role': validated_data['role']},
            current_user_id,
            ip_address
        )
        
        if success:
            logger.info(f"User role updated by admin: {user_id} -> {validated_data['role']}")
            return create_success_response(message, user_data)
        else:
            return create_error_response(message, 400)
    
    except Exception as e:
        logger.error(f"Role update error: {str(e)}")
        return create_error_response("Role update failed", 500)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout user (mainly for logging purposes).
    
    Returns:
        JSON response with logout status
    """
    try:
        user_id = request.current_user['user_id']
        ip_address = get_client_ip()

        # Logout user
        success, message = auth_service.logout(
            user_id=user_id,
            ip_address=ip_address
        )
        # Log logout
        from app.utils.db_abstraction import db
        db.log_audit(
            user_id=user_id,
            action='LOGOUT',
            entity_type='user',
            entity_id=user_id,
            changes={'action': 'user_logout'},
            ip_address=ip_address
        )

        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=400)

        logger.info(f"User logged out: {user_id}")
        return create_success_response("Logged out successfully")
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return create_error_response("Logout failed", 500)


@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Verify JWT token validity.
    
    Returns:
        JSON response with token validity status
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return create_error_response("No token provided", 401)
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        valid, payload = AuthService.verify_jwt_token(token)
        
        if valid:
            return create_success_response("Token is valid", {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role'],
                'expires_at': payload['exp']
            })
        else:
            return create_error_response("Invalid or expired token", 401)
    
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return create_error_response("Token verification failed", 500)


# Error handlers for the blueprint
@auth_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return create_error_response("Bad request", 400)


@auth_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors."""
    return create_error_response("Unauthorized", 401)


@auth_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors."""
    return create_error_response("Forbidden", 403)


@auth_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return create_error_response("Resource not found", 404)


@auth_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(error)}")
    return create_error_response("Internal server error", 500)