# app/schemas/employee_schema.py

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load, pre_load, post_dump
from datetime import datetime, date
import re
import json

class EmployeeRegistrationSchema(Schema):
    """Schema for employee registration/creation."""
    
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
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    
    # Personal Information
    date_of_birth = fields.Str(allow_none=True)
    gender = fields.Str(
        validate=validate.OneOf(['male', 'female', 'other', 'prefer_not_to_say'])
    )
    phone = fields.Str(validate=validate.Length(max=20))
    
    # Address Information
    address = fields.Str(validate=validate.Length(max=255))
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    zip_code = fields.Str(validate=validate.Length(max=20))
    
    # Professional Information
    current_position = fields.Str(validate=validate.Length(max=255))
    current_company = fields.Str(validate=validate.Length(max=255))
    experience_years = fields.Int(validate=validate.Range(min=0, max=50))
    
    # Profile URLs
    linkedin_url = fields.Url(allow_none=True)
    github_url = fields.Url(allow_none=True)
    portfolio_url = fields.Url(allow_none=True)
    
    # Job Preferences
    preferred_job_type = fields.Str(
        validate=validate.OneOf(['full-time', 'part-time', 'contract', 'freelance', 'internship'])
    )
    preferred_location = fields.Str(validate=validate.Length(max=255))
    willing_to_relocate = fields.Bool()
    preferred_salary_min = fields.Decimal(places=2, validate=validate.Range(min=0))
    preferred_salary_max = fields.Decimal(places=2, validate=validate.Range(min=0))
    preferred_currency = fields.Str(validate=validate.Length(max=10))
    remote_work_preference = fields.Str(
        validate=validate.OneOf(['onsite', 'remote', 'hybrid', 'no_preference'])
    )
    
    # Availability
    availability_status = fields.Str(
        validate=validate.OneOf(['available', 'employed', 'not_looking', 'interview_only'])
    )
    available_from = fields.Str(allow_none=True)
    notice_period_days = fields.Int(validate=validate.Range(min=0, max=365))
    
    # Profile Information
    summary = fields.Str(validate=validate.Length(max=2000))
    
    @validates('phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('date_of_birth')
    def validate_date_of_birth(self, str_value, **kwargs):
        if str_value:
            value = datetime.strptime(str_value, "%Y-%m-%d").date()
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 16 or age > 100:
                raise ValidationError('Age must be between 16 and 100 years')
    
    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        defaults = {
            'experience_years': 0,
            'willing_to_relocate': False,
            'preferred_currency': 'USD',
            'remote_work_preference': 'hybrid',
            'availability_status': 'available',
            'notice_period_days': 0
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        return data


class EmployeeUpdateSchema(Schema):
    """Schema for employee profile updates."""
    
    # Personal Information
    first_name = fields.Str(validate=validate.Length(min=1, max=100))
    last_name = fields.Str(validate=validate.Length(min=1, max=100))
    date_of_birth = fields.Str(allow_none=True)
    gender = fields.Str(
        validate=validate.OneOf(['male', 'female', 'other', 'prefer_not_to_say'])
    )
    phone = fields.Str(validate=validate.Length(max=20))
    
    # Address Information
    address = fields.Str(validate=validate.Length(max=255))
    office_address = fields.Str(validate=validate.Length(max=255))
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    zip_code = fields.Str(validate=validate.Length(max=20))
    
    # Professional Information
    current_position = fields.Str(validate=validate.Length(max=255))
    current_company = fields.Str(validate=validate.Length(max=255))
    experience_years = fields.Int(validate=validate.Range(min=0, max=50))
    qualification = fields.Str(validate=validate.Length(max=255))
    bio = fields.Str(validate=validate.Length(max=255))  
    resume_url = fields.Str(validate=validate.Length(max=255), allow_none=True)
    profile_url = fields.Str(validate=validate.Length(max=255), allow_none=True)
    skills = fields.Str(validate=validate.Length(max=1000), allow_none=True)
    # Profile URLs
    linkedin_url = fields.Url(allow_none=True)
    github_url = fields.Url(allow_none=True)
    portfolio_url = fields.Url(allow_none=True)
    
    # Job Preferences
    preferred_job_type = fields.Str(
        validate=validate.OneOf(['full-time', 'part-time', 'contract', 'freelance', 'internship'])
    )
    preferred_location = fields.Str(validate=validate.Length(max=255))
    willing_to_relocate = fields.Bool()
    preferred_salary_min = fields.Decimal(places=2, validate=validate.Range(min=0))
    preferred_salary_max = fields.Decimal(places=2, validate=validate.Range(min=0))
    preferred_currency = fields.Str(validate=validate.Length(max=10))
    remote_work_preference = fields.Str(
        validate=validate.OneOf(['onsite', 'remote', 'hybrid', 'no_preference'])
    )
    
    # Availability
    availability_status = fields.Str(
        validate=validate.OneOf(['available', 'employed', 'not_looking', 'interview_only'])
    )
    available_from = fields.Str(allow_none=True)
    notice_period_days = fields.Int(validate=validate.Range(min=0, max=365))
    
    # Profile Information
    summary = fields.Str(validate=validate.Length(max=2000))
    
    # Privacy Settings
    profile_visibility = fields.Str(
        validate=validate.OneOf(['public', 'private', 'employers_only'])
    )
    show_contact_info = fields.Bool()
    allow_recruiter_contact = fields.Bool()
    
    @validates('phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('date_of_birth')
    def validate_date_of_birth(self, value, **kwargs):
        if value:
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 16 or age > 100:
                raise ValidationError('Age must be between 16 and 100 years')


class EmployeeSkillSchema(Schema):
    """Schema for employee skills."""
    
    skill_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    skill_category = fields.Str(
        validate=validate.OneOf(['technical', 'soft', 'language', 'certification', 'tool'])
    )
    proficiency_level = fields.Str(
        required=True,
        validate=validate.OneOf(['beginner', 'intermediate', 'advanced', 'expert'])
    )
    years_experience = fields.Int(validate=validate.Range(min=0, max=50))
    is_primary = fields.Bool()
    
    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        if 'years_experience' not in data:
            data['years_experience'] = 0
        if 'is_primary' not in data:
            data['is_primary'] = False
        if 'skill_category' not in data:
            data['skill_category'] = 'technical'
        return data


class EmployeeEducationSchema(Schema):
    """Schema for employee education."""
    
    institution_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    degree_type = fields.Str(
        validate=validate.OneOf(['high_school', 'associate', 'bachelor', 'master', 'phd', 'certificate', 'diploma'])
    )
    degree_title = fields.Str(validate=validate.Length(max=255))
    field_of_study = fields.Str(validate=validate.Length(max=255))
    start_date = fields.Date()
    end_date = fields.Date(allow_none=True)
    is_current = fields.Bool()
    gpa = fields.Decimal(places=2, validate=validate.Range(min=0, max=4.0))
    description = fields.Str(validate=validate.Length(max=1000))
    
    @validates('end_date')
    def validate_end_date(self, value, **kwargs):
        if value and 'start_date' in self.context:
            start_date = self.context['start_date']
            if value < start_date:
                raise ValidationError('End date must be after start date')


class EmployeeWorkExperienceSchema(Schema):
    """Schema for employee work experience."""
    
    company_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    position_title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    employment_type = fields.Str(
        validate=validate.OneOf(['full-time', 'part-time', 'contract', 'freelance', 'internship'])
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(allow_none=True)
    is_current = fields.Bool()
    location = fields.Str(validate=validate.Length(max=255))
    description = fields.Str(validate=validate.Length(max=2000))
    achievements = fields.Str(validate=validate.Length(max=2000))
    
    @validates('end_date')
    def validate_end_date(self, value, **kwargs):
        if value and 'start_date' in self.context:
            start_date = self.context['start_date']
            if value < start_date:
                raise ValidationError('End date must be after start date')


class EmployeeCertificationSchema(Schema):
    """Schema for employee certifications."""
    
    certification_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    issuing_organization = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    credential_id = fields.Str(validate=validate.Length(max=100))
    issue_date = fields.Date()
    expiry_date = fields.Date(allow_none=True)
    never_expires = fields.Bool()
    verification_url = fields.Url(allow_none=True)
    description = fields.Str(validate=validate.Length(max=1000))
    
    @validates('expiry_date')
    def validate_expiry_date(self, value, **kwargs):
        if value and 'issue_date' in self.context:
            issue_date = self.context['issue_date']
            if value < issue_date:
                raise ValidationError('Expiry date must be after issue date')


class EmployeeResponseSchema(Schema):
    """Schema for employee response data."""
    
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    
    # User Information
    username = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    first_name = fields.Str(dump_only=True)
    last_name = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)
    
    # Personal Information
    date_of_birth = fields.Str()
    gender = fields.Str()
    phone = fields.Str()
    
    # Address Information
    address = fields.Str()
    city = fields.Str()
    state = fields.Str()
    country = fields.Str()
    zip_code = fields.Str()
    
    # Professional Information
    current_position = fields.Str()
    current_company = fields.Str()
    experience_years = fields.Int()
    resume_url = fields.Url()
    portfolio_url = fields.Url()
    linkedin_url = fields.Url()
    github_url = fields.Url()
    qualification = fields.Str()
    office_address = fields.Str()
    profile_url = fields.Url()
    education = fields.List(fields.Nested(EmployeeEducationSchema), dump_only=True)
    
    # Job Preferences
    preferred_job_type = fields.Str()
    preferred_location = fields.Str()
    willing_to_relocate = fields.Bool()
    preferred_salary_min = fields.Decimal(places=2)
    preferred_salary_max = fields.Decimal(places=2)
    preferred_currency = fields.Str()
    remote_work_preference = fields.Str()
    skills = fields.Str()
    
    # Availability
    availability_status = fields.Str()
    available_from = fields.Str()
    notice_period_days = fields.Int()
    
    # Profile Information
    summary = fields.Str()
    profile_completion = fields.Decimal(places=2, dump_only=True)
    
    # Privacy Settings
    profile_visibility = fields.Str()
    show_contact_info = fields.Bool()
    allow_recruiter_contact = fields.Bool()
    
    # Verification Status
    is_verified = fields.Bool(dump_only=True)
    verification_date = fields.Str(dump_only=True)
    
    # Metadata
    is_active = fields.Bool(dump_only=True)
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)


class EmployeeListResponseSchema(Schema):
    """Schema for employee list responses."""
    
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
    first_name = fields.Str(dump_only=True)
    last_name = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    current_position = fields.Str()
    current_company = fields.Str()
    city = fields.Str()
    country = fields.Str()
    experience_years = fields.Int()
    availability_status = fields.Str()
    preferred_job_type = fields.Str()
    is_verified = fields.Bool(dump_only=True)
    profile_completion = fields.Decimal(places=2, dump_only=True)
    created_at = fields.Str(dump_only=True)


class EmployeeFilterSchema(Schema):
    """Schema for employee filtering and search."""
    
    # Search parameters
    search = fields.Str(validate=validate.Length(max=255))
    first_name = fields.Str(validate=validate.Length(max=100))
    last_name = fields.Str(validate=validate.Length(max=100))
    current_position = fields.Str(validate=validate.Length(max=255))
    current_company = fields.Str(validate=validate.Length(max=255))
    
    # Location filters
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    
    # Professional filters
    experience_years_min = fields.Int(validate=validate.Range(min=0))
    experience_years_max = fields.Int(validate=validate.Range(min=0))
    preferred_job_type = fields.Str(
        validate=validate.OneOf(['full-time', 'part-time', 'contract', 'freelance', 'internship'])
    )
    availability_status = fields.Str(
        validate=validate.OneOf(['available', 'employed', 'not_looking', 'interview_only'])
    )
    remote_work_preference = fields.Str(
        validate=validate.OneOf(['onsite', 'remote', 'hybrid', 'no_preference'])
    )
    
    # Salary filters
    salary_min = fields.Decimal(places=2, validate=validate.Range(min=0))
    salary_max = fields.Decimal(places=2, validate=validate.Range(min=0))
    
    # Status filters
    is_verified = fields.Bool()
    is_active = fields.Bool()
    profile_visibility = fields.Str(
        validate=validate.OneOf(['public', 'private', 'employers_only'])
    )
    
    # Date range filters
    created_after = fields.DateTime(format='iso')
    created_before = fields.DateTime(format='iso')
    
    # Skills filter
    skills = fields.List(fields.Str())
    
    # Pagination
    page = fields.Int(validate=validate.Range(min=1))
    per_page = fields.Int(validate=validate.Range(min=1, max=100))
    
    # Sorting
    sort_by = fields.Str(
        validate=validate.OneOf([
            'created_at', 'first_name', 'last_name', 'experience_years',
            'current_position', 'city', 'profile_completion'
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


class EmployeeVerificationSchema(Schema):
    """Schema for employee verification by admin."""
    
    is_verified = fields.Bool(required=True)
    notes = fields.Str(validate=validate.Length(max=1000))


class EmployeeStatsSchema(Schema):
    """Schema for employee statistics."""
    
    total_applications = fields.Int(dump_only=True)
    active_applications = fields.Int(dump_only=True)
    interviews_scheduled = fields.Int(dump_only=True)
    offers_received = fields.Int(dump_only=True)
    profile_views = fields.Int(dump_only=True)
    profile_completion = fields.Decimal(places=2, dump_only=True)
    skills_count = fields.Int(dump_only=True)
    education_count = fields.Int(dump_only=True)
    experience_count = fields.Int(dump_only=True)
    certifications_count = fields.Int(dump_only=True)
    last_activity = fields.Str(dump_only=True)


# Schema instances for easy import
employee_registration_schema = EmployeeRegistrationSchema()
employee_update_schema = EmployeeUpdateSchema()
employee_skill_schema = EmployeeSkillSchema()
employee_education_schema = EmployeeEducationSchema()
employee_work_experience_schema = EmployeeWorkExperienceSchema()
employee_certification_schema = EmployeeCertificationSchema()
employee_response_schema = EmployeeResponseSchema()
employee_list_response_schema = EmployeeListResponseSchema()
employee_filter_schema = EmployeeFilterSchema()
employee_verification_schema = EmployeeVerificationSchema()
employee_stats_schema = EmployeeStatsSchema()