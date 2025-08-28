# app/services/auth_service.py - Simplified version with datetime fixes

import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from marshmallow import Schema, fields, validate, ValidationError
from typing import Dict, List, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask import current_app, request

from app.utils.db_abstraction import db
from app.schemas.auth_schema import (
    UserRegistrationSchema, UserLoginSchema, UserUpdateSchema,
    UserResponseSchema, PasswordChangeSchema
)

from app.utils.db_abstraction import db
from app.utils.password_utils import verify_password, is_valid_hash, hash_password
from app.utils.auth import generate_token

# Configure logging
logger = logging.getLogger(__name__)


class LoginSchema(Schema):
    """Schema for user login."""
    username = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=128))


# Configure logging
logger = logging.getLogger(__name__)


def get_current_timestamp():
    """Get current timestamp as string for database storage."""
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


class AuthService:
    """
    Service class for handling authentication and user management operations.
    Provides business logic for user registration, login, profile management,
    and password operations with proper validation and audit logging.
    """

    @staticmethod
    def register_user(user_data: Dict, created_by_user_id: Optional[int] = None, 
                     ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Register a new user in the system.
        
        Args:
            user_data (Dict): User registration data
            created_by_user_id (int, optional): ID of user creating this account
            ip_address (str, optional): IP address of the request
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: Success status, message, user data
        """
        try:
            # Validate input data
            schema = UserRegistrationSchema()
            validated_data = schema.load(user_data)
            
            # Check if username already exists
            if db.record_exists('users', 'username = ?', [validated_data['username']]):
                logger.warning(f"Registration attempt with existing username: {validated_data['username']}")
                return False, "Username already exists", None
            
            # Check if email already exists
            if db.record_exists('users', 'email = ?', [validated_data['email']]):
                logger.warning(f"Registration attempt with existing email: {validated_data['email']}")
                return False, "Email already exists", None
            
            # Hash the password
            # password_hash = generate_password_hash(validated_data['password'])
            password_hash = hash_password(validated_data['password'])
            
            # Get current timestamp
            current_time = get_current_timestamp()
            
            # Prepare user data for insertion
            insert_data = {
                'username': validated_data['username'],
                'password_hash': password_hash,
                'email': validated_data['email'],
                'first_name': validated_data.get('first_name'),
                'last_name': validated_data.get('last_name'),
                'role': validated_data.get('role', 'employee'),
                'is_active': 1,  # Use 1/0 for SQLite boolean
                'created_at': current_time,
                'updated_at': current_time
            }
            
            # Insert user into database
            user_id = db.insert('users', insert_data)
            
            if user_id:
                # Log the registration
                try:
                    db.log_audit(
                        user_id=created_by_user_id,
                        action='CREATE',
                        entity_type='user',
                        entity_id=user_id,
                        changes={'action': 'user_registration', 'username': validated_data['username']},
                        ip_address=ip_address
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")
                
                # Get the created user data
                user = db.get_by_id('users', user_id)
                if user:
                    # Remove sensitive data before returning
                    user_response = UserResponseSchema().dump(user)
                    logger.info(f"User registered successfully: {validated_data['username']}")
                    return True, "User registered successfully", user_response
            
            logger.error("Failed to create user record")
            return False, "Failed to create user", None
            
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            return False, f"Registration failed: {str(e)}", None

    @staticmethod
    def login(credentials: Dict, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate user and return JWT token.
        
        Args:
            credentials (Dict): Login credentials
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, auth_data)
        """
        try:
            # Validate input
            login_schema = LoginSchema()
            try:
                validated_data = login_schema.load(credentials)
            except ValidationError as e:
                logger.warning(f"Login validation error: {e.messages}")
                return False, f"Validation error: {e.messages}", None
            
            username = validated_data['username']
            password = validated_data['password']
            
            query = """
                SELECT *
                FROM users 
                WHERE username = ?
            """
            users = db.execute_raw_query(query, [username])
            
            if not users:  # No user found
                logger.warning(f"Login attempt with invalid username: {username}")
                return False, "Invalid username or password", None

            user = users[0]

            if not user.get("is_active"):
                return False, "Please verify your account.", None

            stored_hash = user.get('password_hash')
            
            if not stored_hash:
                logger.error(f"No password hash found for user: {username}")
                return False, "Authentication failed", None
            
            # Validate hash format
            if not is_valid_hash(stored_hash):
                logger.error(f"Invalid hash format for user: {username}")
                return False, "Authentication failed", None
            
            # Verify password
            if not verify_password(password, stored_hash):
                logger.warning(f"Invalid password for user: {username}")
                # Log failed login attempt
                db.log_audit(
                    user_id=user.get('id'),
                    action='LOGIN_FAILED',
                    entity_type='user',
                    entity_id=user.get('id'),
                    changes={'reason': 'invalid_password'},
                    ip_address=ip_address
                )
                return False, "Invalid username or password", None
            
            # Update last login
            db.update(
                'users',
                {'last_login': datetime.utcnow().isoformat()},
                'id = ?',
                [user.get('id')]
            )
            
            # Generate JWT token
            try:
                token = generate_token(user)
            except Exception as e:
                logger.error(f"Token generation failed: {str(e)}")
                return False, "Authentication failed", None
            
            # Log successful login
            db.log_audit(
                user_id=user.get('id'),
                action='LOGIN',
                entity_type='user',
                entity_id=user.get('id'),
                changes={'login_time': datetime.utcnow().isoformat()},
                ip_address=ip_address
            )
            
            # -------------------------
            # Fetch role-specific data
            # -------------------------
            profile_completed = False
            profile_data = {}
            
            if user.get('role') == "employee":
                employee_query = "SELECT * FROM employees WHERE user_id = ?"
                employees = db.execute_raw_query(employee_query, [user.get('id')])
                if employees:
                    profile_data = employees[0]
                    print(profile_data)
                    if profile_data.get('address'):
                        profile_completed = True

            elif user.get('role') == "employer":
                employer_query = "SELECT * FROM employers WHERE user_id = ?"
                employers = db.execute_raw_query(employer_query, [user.get('id')])
                if employers:
                    profile_data = employers[0]
            
            # Prepare response data
            auth_data = {
                'token': token,
                'user': {
                    'id': user.get('id'),
                    'username': user.get('username'),
                    'email': user.get('email'),
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'role': user.get('role'),
                    'profile_url': profile_data.get('profile_url') if profile_data else None,
                    'profile_completed': profile_completed
                }
            }
            
            logger.info(f"Successful login for user: {username}")
            return True, "Login successful", auth_data
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, "Authentication failed", None

        
    @staticmethod
    def verify_email_token(token: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify email using verification token and activate user account.
        
        Args:
            token (str): Email verification token
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, user_data)
        """
        try:
            
            # Find user by verification token
            query = """
                SELECT id, username, password_hash, email, first_name, last_name, 
                    role, is_active, last_login, created_at, updated_at,
                    email_verification_token, email_verification_token_expires
                FROM users 
                WHERE email_verification_token = ? AND is_active = ?
            """
            users = db.execute_raw_query(query, [token, 0])
            print(f"users: {users}")
            
            if not users:
                logger.warning(f"Invalid or already used verification token: {token[:10]}...")
                return False, "Invalid or expired verification token", None
            
            user = users[0]  # Get the first (and should be only) user
            
            if not user:
                logger.warning(f"Invalid or already used verification token: {token[:10]}...")
                return False, "Invalid or expired verification token", None
            
            # Check if token has expired
            if user.get('email_verification_token_expires'):
                try:
                    expiry_time = datetime.fromisoformat(user['email_verification_token_expires'])
                    if datetime.utcnow() > expiry_time:
                        logger.warning(f"Expired verification token for user: {user['username']}")
                        return False, "Verification token has expired", None
                except ValueError as e:
                    logger.error(f"Invalid token expiry format for user {user['id']}: {e}")
                    return False, "Invalid token expiry format", None
            
            # Update user account - activate and clear verification token
            update_data = {
                'is_active': 1,  # Use 1 for True in SQLite
                'email_verification_token': None,
                'email_verification_token_expires': None,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Update users table
            user_updated = db.update('users', update_data, 'id = ?', [user['id']])
            
            if not user_updated:
                logger.error(f"Failed to update user verification status for user: {user['id']}")
                return False, "Failed to verify email", None
            
            verification_data = {
                'is_verified': 1,  # Use 1 for True in SQLite
                'verification_date': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Update employee record - set verification status
            employee_updated = db.update('employees', verification_data, 'user_id = ?', [user['id']])
            if not employee_updated:
                logger.warning(f"Failed to update employee verification status for user: {user['id']}")

            # Update employers table
            employer_updated = db.update('employers', verification_data, 'user_id = ?', [user['id']])
            if not employer_updated:
                logger.warning(f"Failed to update employer verification status for user: {user['id']}")
            
            if not employee_updated:
                logger.warning(f"Failed to update employee verification status for user: {user['id']}")
            
            
            # Log audit trail
            db.log_audit(
                user_id=user['id'],
                action='VERIFY_EMAIL',
                entity_type='user',
                entity_id=user['id'],
                changes={
                    'email_verified': 1,  # Use 1 for True in SQLite
                    'is_active': 1,
                    'verification_token_cleared': 1
                },
                ip_address=None
            )
            
            # Prepare user data for response (exclude sensitive information)
            user_data = {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'role': user['role'],
                'is_active': True,  # Return as boolean for API response
                'verified_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Email verification successful for user: {user['username']} (ID: {user['id']})")
            return True, "Email verified successfully. Your account is now active.", user_data
            
        except Exception as e:
            logger.error(f"Error in email verification: {str(e)}")
            return False, "Email verification failed due to server error", None

    @staticmethod
    def logout(user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """
        Logout user (mainly for audit logging).
        
        Args:
            user_id (int): User ID
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Log logout
            db.log_audit(
                user_id=user_id,
                action='LOGOUT',
                entity_type='user',
                entity_id=user_id,
                changes={'logout_time': datetime.utcnow().isoformat()},
                ip_address=ip_address
            )
            
            logger.info(f"User logged out: {user_id}")
            return True, "Logout successful"
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False, "Logout failed"
    

    @staticmethod
    def authenticate_user(login_data: Dict, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate a user and generate JWT token.
        
        Args:
            login_data (Dict): Login credentials
            ip_address (str, optional): IP address of the request
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: Success status, message, auth data
        """
        try:
            # Validate input data
            schema = UserLoginSchema()
            validated_data = schema.load(login_data)
            
            # Get user by username or email
            user = db.select(
                'users',
                ['id', 'username', 'password_hash', 'email', 'first_name', 'last_name', 'role', 'is_active'],
                'username = ? OR email = ?',
                [validated_data['username'], validated_data['username']]
            )
            
            if not user:
                logger.warning(f"Login attempt with invalid username/email: {validated_data['username']}")
                return False, "Invalid credentials", None
            
            user = user[0]  # Get first result
            
            # Check if user is active (handle both boolean and int values)
            is_active = user.get('is_active')
            if not is_active or (isinstance(is_active, int) and is_active == 0):
                logger.warning(f"Login attempt with inactive account: {user['username']}")
                return False, "Account is inactive", None
            
            # Verify password
            if not check_password_hash(user['password_hash'], validated_data['password']):
                logger.warning(f"Login attempt with wrong password for user: {user['username']}")
                return False, "Invalid credentials", None
            
            # Update last login
            current_time = get_current_timestamp()
            db.update(
                'users',
                {'last_login': current_time, 'updated_at': current_time},
                'id = ?',
                [user['id']]
            )

            # Generate JWT token
            token = AuthService._generate_jwt_token(user)
            
            # Log successful login
            try:
                db.log_audit(
                    user_id=user['id'],
                    action='LOGIN',
                    entity_type='user',
                    entity_id=user['id'],
                    changes={'action': 'successful_login'},
                    ip_address=ip_address
                )
            except Exception as audit_error:
                logger.warning(f"Audit logging failed: {audit_error}")
            
            # Prepare response data
            user_data = UserResponseSchema().dump(user)
            auth_data = {
                'token': token,
                'user': user_data,
                'expires_in': current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
            }
            
            logger.info(f"User authenticated successfully: {user['username']}")
            return True, "Login successful", auth_data
            
        except Exception as e:
            logger.error(f"Error during user authentication: {str(e)}")
            return False, f"Authentication failed: {str(e)}", None

    @staticmethod
    def get_user_profile(user_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get user profile information.
        
        Args:
            user_id (int): User ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: Success status, message, user data
        """
        try:
            user = db.get_by_id('users', user_id)
            if not user:
                return False, "User not found", None
            user_data = UserResponseSchema().dump(user)
            return True, "User profile retrieved successfully", user_data
            
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}")
            return False, f"Failed to retrieve profile: {str(e)}", None

    @staticmethod
    def update_user_profile(user_id: int, update_data: Dict, updated_by_user_id: int,
                           ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Update user profile information.
        
        Args:
            user_id (int): User ID to update
            update_data (Dict): Data to update
            updated_by_user_id (int): ID of user making the update
            ip_address (str, optional): IP address of the request
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: Success status, message, updated user data
        """
        try:
            # Validate input data
            schema = UserUpdateSchema()
            validated_data = schema.load(update_data)
            
            # Check if user exists
            existing_user = db.get_by_id('users', user_id)
            if not existing_user:
                return False, "User not found", None
            
            # Check for unique constraints if email is being updated
            if 'email' in validated_data and validated_data['email'] != existing_user['email']:
                if db.record_exists('users', 'email = ? AND id != ?', [validated_data['email'], user_id]):
                    return False, "Email already exists", None
            
            # Prepare update data
            validated_data['updated_at'] = get_current_timestamp()
            
            # Track changes for audit log
            changes = {}
            for key, value in validated_data.items():
                if key in existing_user and existing_user[key] != value:
                    changes[key] = {'old': existing_user[key], 'new': value}
            
            # Update user
            success = db.update('users', validated_data, 'id = ?', [user_id])
            
            if success:
                # Log the update
                try:
                    db.log_audit(
                        user_id=updated_by_user_id,
                        action='UPDATE',
                        entity_type='user',
                        entity_id=user_id,
                        changes=changes,
                        ip_address=ip_address
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")
                
                # Get updated user data
                updated_user = db.get_by_id('users', user_id)
                user_data = UserResponseSchema().dump(updated_user)
                
                logger.info(f"User profile updated successfully: {user_id}")
                return True, "Profile updated successfully", user_data
            
            return False, "Failed to update profile", None
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False, f"Profile update failed: {str(e)}", None


    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str, ip_address: str = None) -> Tuple[bool, str]:
        """
        Change user password.
        
        Args:
            user_id (int): User ID
            old_password (str): Current password
            new_password (str): New password
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validate new password length
            if len(new_password) < 8:
                return False, "New password must be at least 8 characters long"
            
            # Get user data
            user = db.get_by_id('users', user_id)
            if not user:
                return False, "User not found"
            
            stored_hash = user.get('password_hash')
            if not stored_hash or not is_valid_hash(stored_hash):
                return False, "Current password verification failed"
            
            # Verify old password
            if not verify_password(old_password, stored_hash):
                logger.warning(f"Invalid old password for user: {user_id}")
                return False, "Current password is incorrect"
            
            # Hash new password
            from app.utils.password_utils import hash_password
            try:
                new_password_hash = hash_password(new_password)
            except Exception as e:
                logger.error(f"Password hashing failed: {str(e)}")
                return False, "Password update failed"
            
            # Update password
            success = db.update(
                'users',
                {
                    'password_hash': new_password_hash,
                    'updated_at': datetime.utcnow().isoformat()
                },
                'id = ?',
                [user_id]
            )
            
            if not success:
                return False, "Password update failed"
            
            # Log password change
            db.log_audit(
                user_id=user_id,
                action='PASSWORD_CHANGE',
                entity_type='user',
                entity_id=user_id,
                changes={'password_changed': True},
                ip_address=ip_address
            )
            
            logger.info(f"Password changed for user: {user_id}")
            return True, "Password changed successfully"
            
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            return False, "Password change failed"


    @staticmethod
    def change_password_old(user_id: int, password_data: Dict, ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Change user password.
        
        Args:
            user_id (int): User ID
            password_data (Dict): Current and new password data
            ip_address (str, optional): IP address of the request
            
        Returns:
            Tuple[bool, str]: Success status, message
        """
        try:
            # Validate input data
            schema = PasswordChangeSchema()
            validated_data = schema.load(password_data)
            
            # Get user
            user = db.get_by_id('users', user_id)
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not check_password_hash(user['password_hash'], validated_data['current_password']):
                logger.warning(f"Password change attempt with wrong current password for user: {user_id}")
                return False, "Current password is incorrect"
            
            # Hash new password
            new_password_hash = generate_password_hash(validated_data['new_password'])
            
            # Update password
            success = db.update(
                'users',
                {'password_hash': new_password_hash, 'updated_at': get_current_timestamp()},
                'id = ?',
                [user_id]
            )
            
            if success:
                # Log password change
                try:
                    db.log_audit(
                        user_id=user_id,
                        action='UPDATE',
                        entity_type='user',
                        entity_id=user_id,
                        changes={'action': 'password_change'},
                        ip_address=ip_address
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")
                
                logger.info(f"Password changed successfully for user: {user_id}")
                return True, "Password changed successfully"
            
            return False, "Failed to change password"
            
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return False, f"Password change failed: {str(e)}"

    @staticmethod
    def list_users(filters: Dict = None, page: int = 1, per_page: int = 20) -> Tuple[bool, str, Optional[Dict]]:
        """
        List users with optional filtering and pagination.
        
        Args:
            filters (Dict, optional): Filtering criteria
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: Success status, message, users data
        """
        try:
            # Build query conditions
            conditions = []
            params = []
            
            if filters:
                if filters.get('role'):
                    conditions.append('role = ?')
                    params.append(filters['role'])
                
                if filters.get('is_active') is not None:
                    # Handle boolean conversion for SQLite
                    is_active_value = 1 if filters['is_active'] else 0
                    conditions.append('is_active = ?')
                    params.append(is_active_value)
                
                if filters.get('search'):
                    search_term = f"%{filters['search']}%"
                    conditions.append('(username LIKE ? OR email LIKE ? OR first_name LIKE ? OR last_name LIKE ?)')
                    params.extend([search_term, search_term, search_term, search_term])
            
            condition_str = ' AND '.join(conditions) if conditions else None
            
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Get users
            users = db.select(
                'users',
                ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'last_login', 'created_at'],
                condition_str,
                params,
                order_by='created_at DESC',
                limit=f'{per_page} OFFSET {offset}'
            )
            
            # Get total count for pagination
            count_result = db.select(
                'users',
                ['COUNT(*) as count'],
                condition_str,
                params
            )
            total_count = count_result[0]['count'] if count_result else 0
            
            # Format response
            users_data = [UserResponseSchema().dump(user) for user in (users or [])]
            
            response_data = {
                'users': users_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                }
            }
            
            return True, "Users retrieved successfully", response_data
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return False, f"Failed to retrieve users: {str(e)}", None

    @staticmethod
    def deactivate_user(user_id: int, deactivated_by_user_id: int, 
                       ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deactivate a user account.
        
        Args:
            user_id (int): User ID to deactivate
            deactivated_by_user_id (int): ID of user performing the action
            ip_address (str, optional): IP address of the request
            
        Returns:
            Tuple[bool, str]: Success status, message
        """
        try:
            # Check if user exists
            user = db.get_by_id('users', user_id)
            if not user:
                return False, "User not found"
            
            # Update user status
            success = db.update(
                'users',
                {'is_active': 0, 'updated_at': get_current_timestamp()},  # Use 0 for SQLite
                'id = ?',
                [user_id]
            )
            
            if success:
                # Log the deactivation
                try:
                    db.log_audit(
                        user_id=deactivated_by_user_id,
                        action='UPDATE',
                        entity_type='user',
                        entity_id=user_id,
                        changes={'action': 'user_deactivation', 'is_active': {'old': True, 'new': False}},
                        ip_address=ip_address
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")
                
                logger.info(f"User deactivated successfully: {user_id}")
                return True, "User deactivated successfully"
            
            return False, "Failed to deactivate user"
            
        except Exception as e:
            logger.error(f"Error deactivating user: {str(e)}")
            return False, f"User deactivation failed: {str(e)}"

    @staticmethod
    def _generate_jwt_token(user: Dict) -> str:
        """
        Generate JWT token for authenticated user.
        
        Args:
            user (Dict): User data
            
        Returns:
            str: JWT token
        """
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(seconds=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_jwt_token(token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify and decode JWT token.
        
        Args:
            token (str): JWT token
            
        Returns:
            Tuple[bool, Optional[Dict]]: Success status, decoded payload
        """
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            return True, payload
            
        except jwt.ExpiredSignatureError:
            return False, None
        except jwt.InvalidTokenError:
            return False, None

# Service instance for easy import
auth_service = AuthService()