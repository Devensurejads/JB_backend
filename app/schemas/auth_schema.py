# app/schemas/auth_schema.py - Simplified version to avoid validation errors

from marshmallow import Schema, fields, validate, ValidationError, post_load
import re


class UserRegistrationSchema(Schema):
    """Schema for user registration validation."""
    
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=50, error="Username must be between 3 and 50 characters")
    )
    
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, error="Password must be at least 6 characters long")
    )
    
    confirm_password = fields.Str(required=True)
    
    email = fields.Email(
        required=True,
        validate=validate.Length(max=120, error="Email must be less than 120 characters")
    )
    
    first_name = fields.Str(
        validate=validate.Length(max=50, error="First name must be less than 50 characters"),
        allow_none=True
    )
    
    last_name = fields.Str(
        validate=validate.Length(max=50, error="Last name must be less than 50 characters"),
        allow_none=True
    )
    
    role = fields.Str(
        validate=validate.OneOf(
            ['superadmin', 'admin', 'staff', 'employee', 'employer'],
            error="Invalid role specified"
        ),
        load_default='employee'
    )

    @post_load
    def validate_password_confirmation(self, data, **kwargs):
        """Validate that password and confirm_password match."""
        if data.get('password') != data.get('confirm_password'):
            raise ValidationError({'confirm_password': ['Passwords do not match']})
        
        # Remove confirm_password from final data
        data.pop('confirm_password', None)
        return data


class UserLoginSchema(Schema):
    """Schema for user login validation."""
    
    username = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Username or email is required")
    )
    
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Password is required")
    )


class UserUpdateSchema(Schema):
    """Schema for user profile update validation."""
    
    email = fields.Email(
        validate=validate.Length(max=120, error="Email must be less than 120 characters")
    )
    
    first_name = fields.Str(
        validate=validate.Length(max=50, error="First name must be less than 50 characters"),
        allow_none=True
    )
    
    last_name = fields.Str(
        validate=validate.Length(max=50, error="Last name must be less than 50 characters"),
        allow_none=True
    )
    
    role = fields.Str(
        validate=validate.OneOf(
            ['superadmin', 'admin', 'staff', 'employee', 'employer'],
            error="Invalid role specified"
        )
    )
    
    is_active = fields.Bool()


class PasswordChangeSchema(Schema):
    """Schema for password change validation."""
    
    current_password = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Current password is required")
    )
    
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=6, error="New password must be at least 6 characters long")
    )
    
    confirm_new_password = fields.Str(required=True)

    @post_load
    def validate_password_confirmation(self, data, **kwargs):
        """Validate that new_password and confirm_new_password match."""
        if data.get('new_password') != data.get('confirm_new_password'):
            raise ValidationError({'confirm_new_password': ['New passwords do not match']})
        
        # Remove confirm_new_password from final data
        data.pop('confirm_new_password', None)
        return data


class PasswordResetSchema(Schema):
    """Schema for password reset validation."""
    
    email = fields.Email(
        required=True,
        validate=validate.Length(max=120, error="Email must be less than 120 characters")
    )


class PasswordResetConfirmSchema(Schema):
    """Schema for password reset confirmation validation."""
    
    token = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Reset token is required")
    )
    
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=6, error="New password must be at least 6 characters long")
    )
    
    confirm_new_password = fields.Str(required=True)

    @post_load
    def validate_password_confirmation(self, data, **kwargs):
        """Validate that new_password and confirm_new_password match."""
        if data.get('new_password') != data.get('confirm_new_password'):
            raise ValidationError({'confirm_new_password': ['New passwords do not match']})
        
        # Remove confirm_new_password from final data
        data.pop('confirm_new_password', None)
        return data


class UserResponseSchema(Schema):
    """Schema for user data output (excludes sensitive information)."""
    
    id = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    first_name = fields.Str(dump_only=True, allow_none=True)
    last_name = fields.Str(dump_only=True, allow_none=True)
    role = fields.Str(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    # last_login = fields.DateTime(dump_only=True, allow_none=True)
    last_login = fields.Str(dump_only=True, allow_none=True)
    # created_at = fields.DateTime(dump_only=True)
    # updated_at = fields.DateTime(dump_only=True)
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)


class UserListFilterSchema(Schema):
    """Schema for user list filtering parameters."""
    
    role = fields.Str(
        validate=validate.OneOf(
            ['superadmin', 'admin', 'staff', 'employee', 'employer'],
            error="Invalid role specified"
        )
    )
    
    is_active = fields.Bool()
    
    search = fields.Str(
        validate=validate.Length(max=100, error="Search term must be less than 100 characters")
    )
    
    page = fields.Int(
        validate=validate.Range(min=1, error="Page must be a positive integer"),
        load_default=1
    )
    
    per_page = fields.Int(
        validate=validate.Range(min=1, max=100, error="Items per page must be between 1 and 100"),
        load_default=20
    )


class TokenRefreshSchema(Schema):
    """Schema for token refresh validation."""
    
    refresh_token = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Refresh token is required")
    )


class RoleUpdateSchema(Schema):
    """Schema for role update validation (admin only)."""
    
    role = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['superadmin', 'admin', 'staff', 'employee', 'employer'],
            error="Invalid role specified"
        )
    )


class BulkUserActionSchema(Schema):
    """Schema for bulk user actions validation."""
    
    user_ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate.Length(min=1, error="At least one user ID is required")
    )
    
    action = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['activate', 'deactivate', 'delete'],
            error="Invalid action specified"
        )
    )