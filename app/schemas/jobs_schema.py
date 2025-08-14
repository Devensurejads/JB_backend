# app/schemas/jobs_schema.py

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from datetime import datetime, date
import re
import json

class JobCategorySchema(Schema):
    """Schema for job category validation."""
    
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100, error="Category name must be between 2 and 100 characters")
    )
    description = fields.Str(validate=validate.Length(max=500))
    is_active = fields.Bool()


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
    options = fields.List(fields.Str(), allow_none=True)  # For multiple choice questions
    is_required = fields.Bool()
    order_index = fields.Int(validate=validate.Range(min=0))
    max_length = fields.Int(validate=validate.Range(min=1, max=5000), allow_none=True)
    
    @validates('options')
    def validate_options(self, value, **kwargs):
        # Note: We can't access question_type from context during field validation
        # This validation will be moved to post_load
        pass
    
    @post_load
    def validate_and_set_defaults(self, data, **kwargs):
        """Validate options for multiple choice and set default values after loading."""
        
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
        validate=validate.Length(min=3, max=255, error="Job title must be between 3 and 255 characters")
    )
    description = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=10000, error="Job description must be between 10 and 10000 characters")
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
    application_deadline = fields.Str(allow_none=True)
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
    
    # Skills and Requirements
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
    
    # Skills as objects
    skills = fields.List(fields.Nested(JobSkillSchema), allow_none=True)
    questions = fields.List(fields.Nested(JobQuestionSchema), allow_none=True)
    
    @validates('contact_phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('salary_max')
    def validate_salary_range(self, value, **kwargs):
        # Get salary_min from the data being validated
        if value and hasattr(self, 'context') and self.context and 'salary_min' in self.context:
            salary_min = self.context['salary_min']
            if salary_min and value < salary_min:
                raise ValidationError('Maximum salary must be greater than or equal to minimum salary')
        # Alternative: validate in post_load instead
        return value
    
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
        
        # Validate salary range here instead of in @validates
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        if salary_min and salary_max and salary_max < salary_min:
            raise ValidationError({'salary_max': ['Maximum salary must be greater than or equal to minimum salary']})
        
        # Set default values
        defaults = {
            'employment_type': 'full-time',
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


class JobUpdateSchema(Schema):
    """Schema for job update validation."""
    
    # Basic Job Information
    title = fields.Str(validate=validate.Length(min=3, max=255))
    description = fields.Str(validate=validate.Length(min=10, max=10000))
    short_description = fields.Str(validate=validate.Length(max=500))
    requirements = fields.Str(validate=validate.Length(max=5000))
    responsibilities = fields.Str(validate=validate.Length(max=5000))
    benefits = fields.Str(validate=validate.Length(max=2000))
    
    # Job Details
    employment_type = fields.Str(
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
    application_deadline = fields.Str(allow_none=True)
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
    
    # Skills and Requirements
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
    
    # Skills as objects
    skills = fields.List(fields.Nested(JobSkillSchema), allow_none=True)
    questions = fields.List(fields.Nested(JobQuestionSchema), allow_none=True)
    
    @validates('contact_phone')
    def validate_phone(self, value, **kwargs):
        if value and not re.match(r'^\+?[\d\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')
    
    @validates('salary_max')
    def validate_salary_range(self, value, **kwargs):
        # Note: Cross-field validation moved to post_load method
        return value


class JobFilterSchema(Schema):
    """Schema for job filtering and search parameters."""
    
    # Search parameters
    search = fields.Str(validate=validate.Length(max=255))
    title = fields.Str(validate=validate.Length(max=255))
    company_name = fields.Str(validate=validate.Length(max=255))
    
    # Category and Type filters
    category_id = fields.Int(validate=validate.Range(min=1))
    employment_type = fields.List(fields.Str(
        validate=validate.OneOf(['full-time', 'part-time', 'contract', 'freelance', 'internship'])
    ))
    experience_level = fields.List(fields.Str(
        validate=validate.OneOf(['entry', 'junior', 'mid', 'senior', 'executive'])
    ))
    education_level = fields.List(fields.Str(
        validate=validate.OneOf(['high_school', 'associate', 'bachelor', 'master', 'phd', 'none'])
    ))
    
    # Location filters
    city = fields.Str(validate=validate.Length(max=100))
    state = fields.Str(validate=validate.Length(max=100))
    country = fields.Str(validate=validate.Length(max=100))
    is_remote = fields.Bool()
    remote_type = fields.List(fields.Str(
        validate=validate.OneOf(['fully_remote', 'hybrid', 'onsite'])
    ))
    
    # Salary filters
    salary_min = fields.Decimal(places=2, validate=validate.Range(min=0))
    salary_max = fields.Decimal(places=2, validate=validate.Range(min=0))
    salary_currency = fields.Str(validate=validate.Length(max=10))
    
    # Status filters
    status = fields.List(fields.Str(
        validate=validate.OneOf(['draft', 'active', 'paused', 'closed', 'expired'])
    ))
    priority = fields.List(fields.Str(
        validate=validate.OneOf(['low', 'normal', 'high', 'urgent'])
    ))
    is_featured = fields.Bool()
    is_urgent = fields.Bool()
    
    # Skills filter
    skills = fields.List(fields.Str())
    
    # Date range filters
    posted_after = fields.Date()
    posted_before = fields.Date()
    expires_after = fields.Date()
    expires_before = fields.Date()
    
    # Application filters
    accepting_applications = fields.Bool()
    
    # Employer filters
    employer_id = fields.Int(validate=validate.Range(min=1))
    employer_verified = fields.Bool()
    
    # Pagination
    page = fields.Int(validate=validate.Range(min=1))
    per_page = fields.Int(validate=validate.Range(min=1, max=100))
    
    # Sorting
    sort_by = fields.Str(
        validate=validate.OneOf([
            'created_at', 'posted_at', 'title', 'salary_min', 'salary_max',
            'application_deadline', 'views_count', 'applications_count', 'expires_at'
        ])
    )
    sort_order = fields.Str(validate=validate.OneOf(['asc', 'desc']))
    
    @post_load
    def set_defaults(self, data, **kwargs):
        """Set default values after loading."""
        defaults = {
            'page': 1,
            'per_page': 20,
            'sort_by': 'posted_at',
            'sort_order': 'desc'
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        return data


class JobResponseSchema(Schema):
    """Schema for job response data."""
    
    id = fields.Int(dump_only=True)
    employer_id = fields.Int(dump_only=True)
    category_id = fields.Int()
    
    # Basic Job Information
    title = fields.Str()
    description = fields.Str()
    short_description = fields.Str()
    requirements = fields.Str()
    responsibilities = fields.Str()
    benefits = fields.Str()
    
    # Job Details
    employment_type = fields.Str()
    experience_level = fields.Str()
    education_level = fields.Str()
    
    # Location Information
    location = fields.Str()
    city = fields.Str()
    state = fields.Str()
    country = fields.Str()
    is_remote = fields.Bool()
    remote_type = fields.Str()
    
    # Compensation
    salary_min = fields.Decimal(places=2)
    salary_max = fields.Decimal(places=2)
    salary_currency = fields.Str()
    salary_type = fields.Str()
    show_salary = fields.Bool()
    
    # Job Status and Settings
    status = fields.Str()
    priority = fields.Str()
    is_featured = fields.Bool()
    is_urgent = fields.Bool()
    
    # Application Settings
    application_deadline = fields.Str()
    max_applications = fields.Int()
    applications_count = fields.Int(dump_only=True)
    auto_close_after_deadline = fields.Bool()
    
    # Contact Information
    contact_email = fields.Email()
    contact_phone = fields.Str()
    contact_person = fields.Str()
    application_method = fields.Str()
    external_url = fields.Url()
    
    # Skills and Requirements
    required_skills = fields.List(fields.Str())
    preferred_skills = fields.List(fields.Str())
    languages = fields.List(fields.Str())
    
    # Additional Information
    company_overview = fields.Str()
    work_environment = fields.Str()
    growth_opportunities = fields.Str()
    
    # SEO and Visibility
    seo_title = fields.Str()
    seo_description = fields.Str()
    keywords = fields.List(fields.Str())
    
    # Workflow and Approval
    is_approved = fields.Bool(dump_only=True)
    approved_by = fields.Int(dump_only=True)
    approved_at = fields.Str(dump_only=True)
    rejection_reason = fields.Str(dump_only=True)
    
    # Scheduling
    start_date = fields.Date()
    posted_at = fields.Str(dump_only=True)
    expires_at = fields.Str()
    last_updated_at = fields.Str(dump_only=True)
    
    # Analytics
    views_count = fields.Int(dump_only=True)
    bookmarks_count = fields.Int(dump_only=True)
    
    # Employer Information (when joined)
    employer_company_name = fields.Str(dump_only=True)
    employer_logo_url = fields.Url(dump_only=True)
    employer_is_verified = fields.Bool(dump_only=True)
    
    # Category Information (when joined)
    category_name = fields.Str(dump_only=True)
    
    # Skills as objects
    skills = fields.List(fields.Nested(JobSkillSchema), dump_only=True)
    questions = fields.List(fields.Nested(JobQuestionSchema), dump_only=True)
    
    # Metadata
    is_active = fields.Bool(dump_only=True)
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)


class JobListResponseSchema(Schema):
    """Schema for job list response (simplified for listings)."""
    
    id = fields.Int(dump_only=True)
    employer_id = fields.Int(dump_only=True)
    title = fields.Str()
    short_description = fields.Str()
    employment_type = fields.Str()
    experience_level = fields.Str()
    location = fields.Str()
    city = fields.Str()
    department = fields.Str()
    company_name = fields.Str()
    responsibilities = fields.Str()
    country = fields.Str()
    is_remote = fields.Bool()
    remote_type = fields.Str()
    salary_min = fields.Decimal(places=2)
    salary_max = fields.Decimal(places=2)
    salary_currency = fields.Str()
    show_salary = fields.Bool()
    status = fields.Str()
    is_featured = fields.Bool()
    is_urgent = fields.Bool()
    application_deadline = fields.Str()
    applications_count = fields.Int(dump_only=True)
    views_count = fields.Int(dump_only=True)
    posted_at = fields.Str(dump_only=True)
    expires_at = fields.Str()
    employment_type = fields.Str()
    
    # Company Logo Fields
    company_logo_filename = fields.Str(dump_only=True)
    company_logo_path = fields.Str(dump_only=True)
    company_logo_size = fields.Int(dump_only=True)
    company_logo_uploaded_at = fields.Str(dump_only=True)
    
    # Computed company_logo object
    company_logo = fields.Method("get_company_logo", dump_only=True)
    
    # Employer Information
    employer_company_name = fields.Str(dump_only=True)
    employer_logo_url = fields.Url(dump_only=True)
    employer_is_verified = fields.Bool(dump_only=True)
    
    # Category Information
    category_name = fields.Str(dump_only=True)
    
    created_at = fields.Str(dump_only=True)
    
    def get_company_logo(self, obj):
        """Create company_logo object from individual fields."""
        if hasattr(obj, 'company_logo_filename') and obj.company_logo_filename:
            return {
                'filename': obj.company_logo_filename,
                'path': obj.company_logo_path,
                'size': obj.company_logo_size,
                'uploaded_at': obj.company_logo_uploaded_at
            }
        elif isinstance(obj, dict) and obj.get('company_logo_filename'):
            return {
                'filename': obj.get('company_logo_filename'),
                'path': obj.get('company_logo_path'),
                'size': obj.get('company_logo_size'),
                'uploaded_at': obj.get('company_logo_uploaded_at')
            }
        return None


class JobStatsSchema(Schema):
    """Schema for job statistics."""
    
    total_views = fields.Int(dump_only=True)
    total_applications = fields.Int(dump_only=True)
    total_bookmarks = fields.Int(dump_only=True)
    views_this_week = fields.Int(dump_only=True)
    applications_this_week = fields.Int(dump_only=True)
    avg_views_per_day = fields.Float(dump_only=True)
    avg_applications_per_day = fields.Float(dump_only=True)
    conversion_rate = fields.Float(dump_only=True)  # applications/views ratio


class JobBookmarkSchema(Schema):
    """Schema for job bookmark operations."""
    
    notes = fields.Str(validate=validate.Length(max=1000))


class JobTemplateSchema(Schema):
    """Schema for job template validation."""
    
    template_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255)
    )
    title = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=255)
    )
    description = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=10000)
    )
    requirements = fields.Str(validate=validate.Length(max=5000))
    responsibilities = fields.Str(validate=validate.Length(max=5000))
    benefits = fields.Str(validate=validate.Length(max=2000))
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
    required_skills = fields.List(fields.Str())
    preferred_skills = fields.List(fields.Str())


# Schema instances for easy import
job_category_schema = JobCategorySchema()
job_skill_schema = JobSkillSchema()
job_question_schema = JobQuestionSchema()
job_create_schema = JobCreateSchema()
job_update_schema = JobUpdateSchema()
job_filter_schema = JobFilterSchema()
job_response_schema = JobResponseSchema()
job_list_response_schema = JobListResponseSchema()
job_stats_schema = JobStatsSchema()
job_bookmark_schema = JobBookmarkSchema()
job_template_schema = JobTemplateSchema()