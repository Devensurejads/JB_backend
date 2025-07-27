# app/schemas/employer_schema.py
# Compatible with both older and newer versions of Marshmallow

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from datetime import datetime
import re

class EmployerRegistrationSchema(Schema):
    """Schema for employer registration/creation."""
    
    # User Information (for user table)
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r'^[a-zA-Z0-9_]+$', error='Username can only contain letters, numbers, and underscores')
        ]
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128),
        load_only=True
    )
    email = fields.Email(required=True, validate=validate.Length(max=255))
    first_name = fields.Str(validate=validate.Length(min=1, max=100))
    last_name = fields.Str(validate=validate.Length(min=1, max=100))
    
    # Company Information
    company_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255)
    )
    company_description = fields.Str(validate=validate.Length(max=2000))
    industry = fields.Str(validate=validate.Length(max=100))
    company_size = fields.Str(
        validate=validate.OneOf(['startup', 'small', 'medium', 'large', 'enterprise'])
    )
    website = fields.Url(allow_none=True)
    phone = fields.Str(validate=validate.Length(max=20))
    
    # Address Information
    address = fields.Str(validate=validate.Length(max=255))
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    zip_code = fields.Str(validate=validate.Length(max=20))
    
    # Additional Company Details
    linkedin_company_url = fields.Url(allow_none=True)
    founded_year = fields.Int(
        validate=validate.Range(min=1800, max=datetime.now().year),
        allow_none=True
    )
    company_type = fields.Str(
        validate=validate.OneOf(['private', 'public', 'nonprofit', 'government'])
    )
    registration_number = fields.Str(validate=validate.Length(max=100))
    tax_id = fields.Str(validate=validate.Length(max=50))
    
    # Contact Person (if different from user)
    contact_person_name = fields.Str(validate=validate.Length(max=255))
    contact_person_email = fields.Email(validate=validate.Length(max=255))
    contact_person_phone = fields.Str(validate=validate.Length(max=20))
    contact_person_position = fields.Str(validate=validate.Length(max=100))
    
    @validates('phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('contact_person_phone')
    def validate_contact_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        if 'company_type' not in data or data['company_type'] is None:
            data['company_type'] = 'private'
        return data


class EmployerUpdateSchema(Schema):
    """Schema for employer profile updates."""
    
    # Company Information
    company_name = fields.Str(validate=validate.Length(min=2, max=255))
    company_description = fields.Str(validate=validate.Length(max=2000))
    industry = fields.Str(validate=validate.Length(max=100))
    company_size = fields.Str(
        validate=validate.OneOf(['startup', 'small', 'medium', 'large', 'enterprise'])
    )
    website = fields.Url(allow_none=True)
    phone = fields.Str(validate=validate.Length(max=20))
    
    # Address Information
    address = fields.Str(validate=validate.Length(max=255))
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    zip_code = fields.Str(validate=validate.Length(max=20))
    
    # Additional Company Details
    linkedin_company_url = fields.Url(allow_none=True)
    founded_year = fields.Int(
        validate=validate.Range(min=1800, max=datetime.now().year),
        allow_none=True
    )
    company_type = fields.Str(
        validate=validate.OneOf(['private', 'public', 'nonprofit', 'government'])
    )
    registration_number = fields.Str(validate=validate.Length(max=100))
    tax_id = fields.Str(validate=validate.Length(max=50))
    
    # Contact Person
    contact_person_name = fields.Str(validate=validate.Length(max=255))
    contact_person_email = fields.Email(validate=validate.Length(max=255))
    contact_person_phone = fields.Str(validate=validate.Length(max=20))
    contact_person_position = fields.Str(validate=validate.Length(max=100))
    
    @validates('phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('contact_person_phone')
    def validate_contact_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')


class EmployerResponseSchema(Schema):
    """Schema for employer response data."""
    
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    
    # User Information
    username = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    first_name = fields.Str(dump_only=True)
    last_name = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)
    
    # Company Information
    company_name = fields.Str()
    company_description = fields.Str()
    industry = fields.Str()
    company_size = fields.Str()
    website = fields.Url()
    phone = fields.Str()
    logo_url = fields.Url()
    
    # Address Information
    address = fields.Str()
    city = fields.Str()
    state = fields.Str()
    country = fields.Str()
    zip_code = fields.Str()
    
    # Additional Company Details
    linkedin_company_url = fields.Url()
    founded_year = fields.Int()
    company_type = fields.Str()
    registration_number = fields.Str()
    tax_id = fields.Str()
    
    # Verification Status
    is_verified = fields.Bool(dump_only=True)
    verification_date = fields.DateTime(dump_only=True, format='iso')
    verified_by = fields.Int(dump_only=True)
    
    # Subscription Information
    subscription_plan = fields.Str(dump_only=True)
    subscription_expires_at = fields.DateTime(dump_only=True, format='iso')
    monthly_job_limit = fields.Int(dump_only=True)
    jobs_posted_this_month = fields.Int(dump_only=True)
    
    # Contact Person
    contact_person_name = fields.Str()
    contact_person_email = fields.Email()
    contact_person_phone = fields.Str()
    contact_person_position = fields.Str()
    
    # Features and Permissions
    can_post_jobs = fields.Bool(dump_only=True)
    can_view_applications = fields.Bool(dump_only=True)
    can_message_candidates = fields.Bool(dump_only=True)
    can_access_analytics = fields.Bool(dump_only=True)
    
    # Metadata
    is_active = fields.Bool(dump_only=True)
    # created_at = fields.DateTime(dump_only=True, format='iso')
    # updated_at = fields.DateTime(dump_only=True, format='iso')
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)

class EmployerListResponseSchema(Schema):
    """Schema for employer list responses."""
    
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    company_name = fields.Str()
    industry = fields.Str()
    company_size = fields.Str()
    city = fields.Str()
    country = fields.Str()
    is_verified = fields.Bool(dump_only=True)
    subscription_plan = fields.Str(dump_only=True)
    jobs_posted_this_month = fields.Int(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    # created_at = fields.DateTime(dump_only=True, format='iso')
    created_at = fields.Str(dump_only=True)


class EmployerFilterSchema(Schema):
    """Schema for employer filtering and search."""
    
    # Search parameters
    search = fields.Str(validate=validate.Length(max=255))
    company_name = fields.Str(validate=validate.Length(max=255))
    industry = fields.Str(validate=validate.Length(max=100))
    company_size = fields.Str(
        validate=validate.OneOf(['startup', 'small', 'medium', 'large', 'enterprise'])
    )
    city = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    
    # Status filters
    is_verified = fields.Bool()
    is_active = fields.Bool()
    subscription_plan = fields.Str(
        validate=validate.OneOf(['basic', 'premium', 'enterprise'])
    )
    
    # Date range filters
    created_after = fields.DateTime(format='iso')
    created_before = fields.DateTime(format='iso')
    
    # Pagination
    page = fields.Int(validate=validate.Range(min=1))
    per_page = fields.Int(validate=validate.Range(min=1, max=100))
    
    # Sorting
    sort_by = fields.Str(
        validate=validate.OneOf([
            'created_at', 'company_name', 'industry', 'city',
            'jobs_posted_this_month', 'subscription_plan'
        ])
    )
    sort_order = fields.Str(validate=validate.OneOf(['asc', 'desc']))
    
    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        if 'page' not in data:
            data['page'] = 1
        if 'per_page' not in data:
            data['per_page'] = 20
        if 'sort_by' not in data:
            data['sort_by'] = 'created_at'
        if 'sort_order' not in data:
            data['sort_order'] = 'desc'
        return data


class EmployerVerificationSchema(Schema):
    """Schema for employer verification by admin."""
    
    is_verified = fields.Bool(required=True)
    notes = fields.Str(validate=validate.Length(max=1000))


class EmployerSubscriptionSchema(Schema):
    """Schema for updating employer subscription."""
    
    subscription_plan = fields.Str(
        required=True,
        validate=validate.OneOf(['basic', 'premium', 'enterprise'])
    )
    subscription_expires_at = fields.DateTime(format='iso')
    monthly_job_limit = fields.Int(validate=validate.Range(min=0))
    
    # Feature permissions
    can_post_jobs = fields.Bool()
    can_view_applications = fields.Bool()
    can_message_candidates = fields.Bool()
    can_access_analytics = fields.Bool()


class EmployerStatsSchema(Schema):
    """Schema for employer statistics."""
    
    total_jobs_posted = fields.Int(dump_only=True)
    active_jobs = fields.Int(dump_only=True)
    total_applications = fields.Int(dump_only=True)
    jobs_posted_this_month = fields.Int(dump_only=True)
    average_rating = fields.Float(dump_only=True)
    total_reviews = fields.Int(dump_only=True)
    profile_completion = fields.Float(dump_only=True)
    last_activity = fields.DateTime(dump_only=True, format='iso')


# Schema instances for easy import
employer_registration_schema = EmployerRegistrationSchema()
employer_update_schema = EmployerUpdateSchema()
employer_response_schema = EmployerResponseSchema()
employer_list_response_schema = EmployerListResponseSchema()
employer_filter_schema = EmployerFilterSchema()
employer_verification_schema = EmployerVerificationSchema()
employer_subscription_schema = EmployerSubscriptionSchema()
employer_stats_schema = EmployerStatsSchema()