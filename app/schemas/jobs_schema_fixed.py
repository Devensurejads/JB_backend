# app/schemas/jobs_schema_fixed.py
# Fixed version without context dependency issues

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from datetime import datetime, date
import re
import json

class JobSkillSchema(Schema):
    """Schema for job skills validation."""
    
    skill_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    skill_category = fields.Str(
        validate=validate.OneOf(['technical', 'soft', 'language', 'certification', 'tool'])
    )
    is_required = fields.Bool()
    proficiency_level = fields.Str(
        validate=validate.OneOf(['beginner', 'intermediate', 'advanced', 'expert'])
    )
    years_experience = fields.Int(validate=validate.Range(min=0, max=50))
    
    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        defaults = {
            'skill_category': 'technical',
            'is_required': True,
            'proficiency_level': 'intermediate',
            'years_experience': 0
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        return data


class JobQuestionSchema(Schema):
    """Schema for job application questions validation."""
    
    question_text = fields.Str(required=True, validate=validate.Length(min=5, max=1000))
    question_type = fields.Str(
        validate=validate.OneOf(['text', 'textarea', 'multiple_choice', 'yes_no', 'number', 'date'])
    )
    options = fields.List(fields.Str(), allow_none=True)
    is_required = fields.Bool()
    order_index = fields.Int(validate=validate.Range(min=0))
    max_length = fields.Int(validate=validate.Range(min=1, max=5000), allow_none=True)
    
    @post_load
    def validate_and_set_defaults(self, data, **kwargs):
        """Validate options for multiple choice and set default values."""
        
        # Validate options for multiple choice questions
        if data.get('question_type') == 'multiple_choice' and not data.get('options'):
            raise ValidationError({'options': ['Options are required for multiple choice questions']})
        
        # Set default values
        defaults = {
            'question_type': 'text',
            'is_required': False,
            'order_index': 0
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        return data


class JobCreateSchema(Schema):
    """Schema for job creation validation."""
    
    # Basic Job Information
    title = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=255)
    )
    description = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=10000)
    )
    short_description = fields.Str(validate=validate.Length(max=500))
    requirements = fields.Str(validate=validate.Length(max=5000))
    responsibilities = fields.Str(validate=validate.Length(max=5000))
    benefits = fields.Str(validate=validate.Length(max=2000))
    
    # Job Details
    employment_type = fields.Str(
        required=True,
        validate=validate.OneOf(['full-time', 'part-time', 'contract', 'freelance', 'internship'])
    )
    experience_level = fields.Str(
        validate=validate.OneOf(['entry', 'junior', 'mid', 'senior', 'executive'])
    )
    education_level = fields.Str(
        validate=validate.OneOf(['high_school', 'associate', 'bachelor', 'master', 'phd', 'none'])
    )
    category_id = fields.Int(validate=validate.Range(min=1))
    
    # Location Information
    location = fields.Str(validate=validate.Length(max=255))
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    is_remote = fields.Bool()
    remote_type = fields.Str(
        validate=validate.OneOf(['fully_remote', 'hybrid', 'onsite'])
    )
    
    # Compensation
    salary_min = fields.Decimal(places=2, validate=validate.Range(min=0))
    salary_max = fields.Decimal(places=2, validate=validate.Range(min=0))
    salary_currency = fields.Str(validate=validate.Length(max=10))
    salary_type = fields.Str(
        validate=validate.OneOf(['hourly', 'daily', 'weekly', 'monthly', 'annual'])
    )
    show_salary = fields.Bool()
    
    # Job Status and Settings
    status = fields.Str(
        validate=validate.OneOf(['draft', 'active', 'paused', 'closed', 'expired'])
    )
    priority = fields.Str(
        validate=validate.OneOf(['low', 'normal', 'high', 'urgent'])
    )
    is_featured = fields.Bool()
    is_urgent = fields.Bool()
    
    # Application Settings
    application_deadline = fields.Date(allow_none=True)
    max_applications = fields.Int(validate=validate.Range(min=1), allow_none=True)
    auto_close_after_deadline = fields.Bool()
    
    # Contact Information
    contact_email = fields.Email(validate=validate.Length(max=255))
    contact_phone = fields.Str(validate=validate.Length(max=20))
    contact_person = fields.Str(validate=validate.Length(max=255))
    application_method = fields.Str(
        validate=validate.OneOf(['internal', 'external', 'email'])
    )
    external_url = fields.Url(allow_none=True)
    
    # Skills and Requirements (as lists)
    required_skills = fields.List(fields.Str())
    preferred_skills = fields.List(fields.Str())
    languages = fields.List(fields.Str())
    
    # Additional Information
    company_overview = fields.Str(validate=validate.Length(max=2000))
    work_environment = fields.Str(validate=validate.Length(max=2000))
    growth_opportunities = fields.Str(validate=validate.Length(max=2000))
    
    # SEO and Visibility
    seo_title = fields.Str(validate=validate.Length(max=255))
    seo_description = fields.Str(validate=validate.Length(max=500))
    keywords = fields.List(fields.Str())
    
    # Scheduling
    start_date = fields.Date(allow_none=True)
    expires_at = fields.DateTime(allow_none=True)
    
    # Skills and questions as nested objects
    skills = fields.List(fields.Nested(JobSkillSchema), allow_none=True)
    questions = fields.List(fields.Nested(JobQuestionSchema), allow_none=True)
    
    @validates('contact_phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('application_deadline')
    def validate_application_deadline(self, value, **kwargs):
        if value and value <= date.today():
            raise ValidationError('Application deadline must be in the future')
    
    @validates('start_date')
    def validate_start_date(self, value, **kwargs):
        if value and value < date.today():
            raise ValidationError('Start date cannot be in the past')
    
    @validates('expires_at')
    def validate_expires_at(self, value, **kwargs):
        if value and value <= datetime.now():
            raise ValidationError('Expiry date must be in the future')
    
    @post_load
    def validate_and_set_defaults(self, data, **kwargs):
        """Validate salary range and set default values after loading."""
        
        # Validate salary range
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        if salary_min and salary_max and salary_max < salary_min:
            raise ValidationError({'salary_max': ['Maximum salary must be greater than or equal to minimum salary']})
        
        # Set default values
        defaults = {
            'experience_level': 'mid',
            'education_level': 'bachelor',
            'is_remote': False,
            'remote_type': 'onsite',
            'salary_currency': 'USD',
            'salary_type': 'annual',
            'show_salary': True,
            'status': 'draft',
            'priority': 'normal',
            'is_featured': False,
            'is_urgent': False,
            'auto_close_after_deadline': True,
            'application_method': 'internal'
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        return data


# Create schema instances
job_create_schema_fixed = JobCreateSchema()
job_skill_schema_fixed = JobSkillSchema()
job_question_schema_fixed = JobQuestionSchema()