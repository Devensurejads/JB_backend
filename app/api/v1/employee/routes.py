# app/api/v1/employee/routes.py

from flask import Blueprint, request, jsonify, g
import logging
from marshmallow import ValidationError
from werkzeug.utils import secure_filename
import os

from app.utils.auth import (
    login_required, admin_required, employee_required, employer_required,
    get_current_user, can_access_user_data
)
from app.services.employee_service import employee_service
from app.utils.db_abstraction import db
from app.utils.email import EmailService


email_service = EmailService(
    smtp_server="smtp.gmail.com",  # e.g., "smtp.gmail.com"
    smtp_port=587,  # Usually 587 for TLS
    smtp_username="devensurejads@gmail.com",
    smtp_password="sqohkreztwpnjket",
    from_email="devensurejads@gmail.com"
)

# Base URL for your application
BASE_URL = "http://localhost:4200" 
# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
employee_bp = Blueprint('employee', __name__, url_prefix='/api/v1/employees')


def get_client_ip():
    """Get client IP address from request."""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR')


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


@employee_bp.route('', methods=['POST'])
def create_employee():
    """
    Create a new employee account.
    ---
    Public endpoint for employee registration.
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Create employee
        success, message, employee_data = employee_service.create_employee(
            data=data,
            current_user_id=None,  # Public registration
            ip_address=ip_address,
            email_service=email_service,
            base_url=BASE_URL
        )
        
        if success:
            logger.info(f"Employee registration successful: {employee_data.get('username')}")
            return create_response(True, message, employee_data, 201)
        else:
            logger.warning(f"Employee registration failed: {message}")
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in create_employee endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('', methods=['GET'])
@admin_required
def list_employees():
    """
    List all employees with filtering and pagination.
    ---
    Admin only endpoint.
    """
    try:
        # Get query parameters
        filters = request.args.to_dict()
        
        # Convert string booleans to actual booleans
        bool_fields = ['is_verified', 'is_active', 'willing_to_relocate']
        for field in bool_fields:
            if field in filters:
                filters[field] = filters[field].lower() in ['true', '1', 'yes']
        
        # Convert numeric fields
        numeric_fields = ['page', 'per_page', 'experience_years_min', 'experience_years_max']
        for field in numeric_fields:
            if field in filters:
                try:
                    filters[field] = int(filters[field])
                except ValueError:
                    return create_response(False, f"Invalid {field} parameter", status_code=400)
        
        # Convert decimal fields
        decimal_fields = ['salary_min', 'salary_max']
        for field in decimal_fields:
            if field in filters:
                try:
                    filters[field] = float(filters[field])
                except ValueError:
                    return create_response(False, f"Invalid {field} parameter", status_code=400)
        
        # Handle skills array
        if 'skills' in filters:
            if isinstance(filters['skills'], str):
                filters['skills'] = [skill.strip() for skill in filters['skills'].split(',')]
        
        # List employees
        success, message, result_data = employee_service.list_employees(filters)
        
        if success:
            return create_response(True, message, result_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in list_employees endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>', methods=['GET'])
@login_required
def get_employee(employee_id):
    """
    Get employee details by ID.
    ---
    Accessible by: Admin, the employee themselves, or staff.
    """
    try:
        current_user = get_current_user()
        
        # Get employee data
        success, message, employee_data = employee_service.get_employee_by_id(employee_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        # Check access permissions
        user_role = current_user.get('role')
        employee_user_id = employee_data.get('user_id')
        
        # Admin and staff can access any employee
        if user_role in ['admin', 'superadmin', 'staff']:
            pass
        # Employee can access their own data
        elif user_role == 'employee' and current_user.get('user_id') == employee_user_id:
            pass
        # Employers can access public profiles
        elif user_role == 'employer' and employee_data.get('profile_visibility') in ['public', 'employers_only']:
            # Filter sensitive information for employers
            sensitive_fields = ['email', 'phone'] if not employee_data.get('show_contact_info', True) else []
            for field in sensitive_fields:
                employee_data.pop(field, None)
        else:
            return create_response(False, "Access denied", status_code=403)
        
        return create_response(True, message, employee_data)
    
    except Exception as e:
        logger.error(f"Error in get_employee endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/profile', methods=['GET'])
@employee_required
def get_my_profile():
    """
    Get current employee's profile.
    ---
    Accessible by: Employees only.
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        
        # Get employee by user ID
        success, message, employee_data = employee_service.get_employee_by_user_id(user_id)
        
        if success:
            return create_response(True, message, employee_data)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in get_my_profile endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)
    
    
@employee_bp.route('/profile/<int:employee_id>', methods=['GET'])
@employer_required
def get_employee_profile(employee_id):
    """
    Get current employee's profile.
    ---
    Accessible by: Employees only.
    """
    try:
        # current_user = get_current_user()
        # user_id = current_user.get('user_id')
        
        # Get employee by user ID
        success, message, employee_data = employee_service.get_employee_by_user_id(employee_id)
        
        if success:
            return create_response(True, message, employee_data)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in get_my_profile endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>', methods=['PUT'])
@login_required
def update_employee(employee_id):
    """
    Update employee profile.
    ---
    Accessible by: Admin, the employee themselves, or staff.
    """
    try:
        current_user = get_current_user()
        
        # Get request data
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        # First, get employee to check permissions
        success, message, employee_data = employee_service.get_employee_by_id(employee_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        # Check access permissions
        user_role = current_user.get('role')
        employee_user_id = employee_data.get('user_id')
        
        # Admin and staff can update any employee
        if user_role in ['admin', 'superadmin', 'staff']:
            pass
        # Employee can update their own data
        elif user_role == 'employee' and current_user.get('user_id') == employee_user_id:
            pass
        else:
            return create_response(False, "Access denied", status_code=403)
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Update employee
        success, message, updated_data = employee_service.update_employee(
            employee_id=employee_id,
            data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, updated_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in update_employee endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/profile', methods=['PUT'])
@employee_required
def update_my_profile():
    """
    Update current employee's profile.
    ---
    Accessible by: Employees only.
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')

        # Collect form data
        data = request.form.to_dict()
        resume_file = request.files.get('resume')  # File key must match frontend
        profile_image = request.files.get('profile_image')

        if not data and not resume_file:
            return create_response(False, "No data provided", status_code=400)

        # If you want to parse comma-separated skills
        skills = data.get('skills')
        if isinstance(skills, list):
            data['skills'] = ', '.join(skills)
        elif isinstance(skills, str):
            # Convert string like "Python, Flask" into clean format
            data['skills'] = ', '.join([s.strip() for s in skills.split(',')])

        # Get employee by user ID
        success, message, employee_data = employee_service.get_employee_by_user_id(user_id)
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)

        employee_id = employee_data.get('id')

        # Get IP for audit log
        ip_address = get_client_ip()

        # Handle resume file upload
        if resume_file:
            filename = secure_filename(resume_file.filename)
            upload_folder = 'uploads/resumes'
            os.makedirs(upload_folder, exist_ok=True)
            resume_path = os.path.join(upload_folder, filename)
            resume_file.save(resume_path)
            data['resume_url'] = resume_path
            
        # Handle profile image upload
        if profile_image:
            filename = secure_filename(profile_image.filename)
            upload_folder = 'uploads/profile_images'
            os.makedirs(upload_folder, exist_ok=True)
            profile_image_path = os.path.join(upload_folder, filename)
            profile_image.save(profile_image_path)
            data['profile_url'] = profile_image_path

        # Update employee
        success, message, updated_data = employee_service.update_employee(
            employee_id=employee_id,
            data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )

        if success:
            return create_response(True, message, updated_data)
        else:
            return create_response(False, message, status_code=400)

    except Exception as e:
        logger.error(f"Error in update_my_profile endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>', methods=['DELETE'])
@admin_required
def delete_employee(employee_id):
    """
    Delete (deactivate) employee account.
    ---
    Admin only endpoint.
    """
    try:
        current_user = get_current_user()
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Delete employee
        success, message = employee_service.delete_employee(
            employee_id=employee_id,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in delete_employee endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>/verify', methods=['PUT'])
@admin_required
def verify_employee(employee_id):
    """
    Verify or unverify an employee.
    ---
    Admin only endpoint.
    """
    try:
        current_user = get_current_user()
        
        # Get request data
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Verify employee
        success, message = employee_service.verify_employee(
            employee_id=employee_id,
            verification_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in verify_employee endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>/stats', methods=['GET'])
@login_required
def get_employee_stats(employee_id):
    """
    Get employee statistics.
    ---
    Accessible by: Admin, the employee themselves, or staff.
    """
    try:
        current_user = get_current_user()
        
        # First, get employee to check permissions
        success, message, employee_data = employee_service.get_employee_by_id(employee_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        # Check access permissions
        user_role = current_user.get('role')
        employee_user_id = employee_data.get('user_id')
        
        # Admin and staff can access any employee stats
        if user_role in ['admin', 'superadmin', 'staff']:
            pass
        # Employee can access their own stats
        elif user_role == 'employee' and current_user.get('user_id') == employee_user_id:
            pass
        else:
            return create_response(False, "Access denied", status_code=403)
        
        # Get stats
        success, message, stats_data = employee_service.get_employee_stats(employee_id)
        
        if success:
            return create_response(True, message, stats_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_employee_stats endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/stats', methods=['GET'])
@employee_required
def get_my_stats():
    """
    Get current employee's statistics.
    ---
    Accessible by: Employees only.
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        
        # Get employee by user ID to find employee_id
        success, message, employee_data = employee_service.get_employee_by_user_id(user_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        employee_id = employee_data.get('id')
        
        # Get stats
        success, message, stats_data = employee_service.get_employee_stats(employee_id)
        
        if success:
            return create_response(True, message, stats_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_my_stats endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/search', methods=['GET'])
def search_employees():
    """
    Get all employees with pagination + filters (first_name, last_name, current_position, experience_years).
    ---
    Accessible by: Employees only.
    """
    try:
        # Pagination params (support both `per_page` and `perPage`)
        page = int(request.args.get('page', 1))
        per_page = request.args.get('per_page') or request.args.get('perPage') or 10
        per_page = int(per_page)

        # Search term
        search_term = request.args.get('searchTerm', '').strip()

        # Experience filter
        experience = request.args.get('experience', '').strip()
        experience = int(experience) if experience.isdigit() else None

        # Call service
        success, message, response_data = employee_service.get_all_employees(
            page, per_page, search_term, experience
        )

        if success:
            return create_response(True, message, response_data)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)

    except Exception as e:
        logger.error(f"Error in search_employees endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)






# Skills Management Endpoints
@employee_bp.route('/<int:employee_id>/skills', methods=['POST'])
@login_required
def add_skill(employee_id):
    """Add a skill to employee profile."""
    try:
        current_user = get_current_user()
        
        # Check permissions (employee can manage their own skills, admin can manage any)
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        ip_address = get_client_ip()
        success, message, skill_data = employee_service.add_skill(
            employee_id=employee_id,
            skill_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, skill_data, 201)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in add_skill endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>/skills', methods=['GET'])
@login_required
def get_skills(employee_id):
    """Get all skills for an employee."""
    try:
        current_user = get_current_user()
        
        if not _can_view_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        success, message, skills_data = employee_service.get_employee_skills(employee_id)
        
        if success:
            return create_response(True, message, skills_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_skills endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/skills/<int:skill_id>', methods=['PUT'])
@login_required
def update_skill(skill_id):
    """Update a skill."""
    try:
        current_user = get_current_user()
        
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        ip_address = get_client_ip()
        success, message, skill_data = employee_service.update_skill(
            skill_id=skill_id,
            skill_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, skill_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in update_skill endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/skills/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_skill(skill_id):
    """Delete a skill."""
    try:
        current_user = get_current_user()
        
        ip_address = get_client_ip()
        success, message = employee_service.delete_skill(
            skill_id=skill_id,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in delete_skill endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


# Education Management Endpoints
@employee_bp.route('/<int:employee_id>/education', methods=['POST'])
@login_required
def add_education(employee_id):
    """Add education to employee profile."""
    try:
        current_user = get_current_user()
        
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        ip_address = get_client_ip()
        success, message, education_data = employee_service.add_education(
            employee_id=employee_id,
            education_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, education_data, 201)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in add_education endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>/education', methods=['GET'])
@login_required
def get_education(employee_id):
    """Get all education for an employee."""
    try:
        current_user = get_current_user()
        
        if not _can_view_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        success, message, education_data = employee_service.get_employee_education(employee_id)
        
        if success:
            return create_response(True, message, education_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_education endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)
    
    
@employee_bp.route('/<int:employee_id>/education/<int:education_id>', methods=['PUT'])
@login_required
def update_education(employee_id, education_id):
    """Update an existing education entry for an employee."""
    try:
        current_user = get_current_user()

        # Permission check
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)

        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)

        ip_address = get_client_ip()
        success, message, updated_data = employee_service.update_education(
            employee_id=employee_id,
            education_id=education_id,
            education_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )

        if success:
            return create_response(True, message, updated_data, status_code=200)
        else:
            return create_response(False, message, status_code=400)

    except Exception as e:
        logger.error(f"Error in update_education endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)

    
    
@employee_bp.route('/<int:employee_id>/education/<int:education_id>', methods=['DELETE'])
@login_required
def delete_education(employee_id, education_id):
    """Delete education from employee profile."""
    try:
        current_user = get_current_user()

        # Check if current user can manage this employee's data
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)

        ip_address = get_client_ip()
        success, message = employee_service.delete_education(
            employee_id=employee_id,
            education_id=education_id,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )

        if success:
            return create_response(True, message, status_code=200)
        else:
            return create_response(False, message, status_code=400)

    except Exception as e:
        logger.error(f"Error in delete_education endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)



# Work Experience Management Endpoints
@employee_bp.route('/<int:employee_id>/experience', methods=['POST'])
@login_required
def add_work_experience(employee_id):
    """Add work experience to employee profile."""
    try:
        current_user = get_current_user()
        
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        ip_address = get_client_ip()
        success, message, experience_data = employee_service.add_work_experience(
            employee_id=employee_id,
            experience_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, experience_data, 201)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in add_work_experience endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>/experience', methods=['GET'])
@login_required
def get_work_experience(employee_id):
    """Get all work experience for an employee."""
    try:
        current_user = get_current_user()
        
        if not _can_view_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        success, message, experience_data = employee_service.get_employee_work_experience(employee_id)
        
        if success:
            return create_response(True, message, experience_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_work_experience endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)
    
@employee_bp.route('/<int:employee_id>/experience/<int:experience_id>', methods=['PUT'])
@login_required
def update_work_experience(employee_id, experience_id):
    """Update work experience of an employee."""
    try:
        current_user = get_current_user()

        # Permission check
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)

        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)

        ip_address = get_client_ip()
        success, message, updated_experience = employee_service.update_work_experience(
            employee_id=employee_id,
            experience_id=experience_id,
            experience_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )

        if success:
            return create_response(True, message, updated_experience)
        else:
            return create_response(False, message, status_code=400)

    except Exception as e:
        logger.error(f"Error in update_work_experience endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)

@employee_bp.route('/<int:employee_id>/experience/<int:experience_id>', methods=['DELETE'])
@login_required
def delete_work_experience(employee_id, experience_id):
    """Delete work experience of an employee."""
    try:
        current_user = get_current_user()

        # Permission check
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)

        ip_address = get_client_ip()
        success, message = employee_service.delete_work_experience(
            employee_id=employee_id,
            experience_id=experience_id,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )

        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=400)

    except Exception as e:
        logger.error(f"Error in delete_work_experience endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


# Certification Management Endpoints
@employee_bp.route('/<int:employee_id>/certifications', methods=['POST'])
@login_required
def add_certification(employee_id):
    """Add certification to employee profile."""
    try:
        current_user = get_current_user()
        
        if not _can_manage_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        ip_address = get_client_ip()
        success, message, certification_data = employee_service.add_certification(
            employee_id=employee_id,
            certification_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, certification_data, 201)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in add_certification endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employee_bp.route('/<int:employee_id>/certifications', methods=['GET'])
@login_required
def get_certifications(employee_id):
    """Get all certifications for an employee."""
    try:
        current_user = get_current_user()
        
        if not _can_view_employee_data(current_user, employee_id):
            return create_response(False, "Access denied", status_code=403)
        
        success, message, certifications_data = employee_service.get_employee_certifications(employee_id)
        
        if success:
            return create_response(True, message, certifications_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_certifications endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


# Helper functions for permission checking
def _can_view_employee_data(current_user: dict, employee_id: int) -> bool:
    """Check if current user can view employee data."""
    user_role = current_user.get('role')
    
    # Admin and staff can view any employee
    if user_role in ['admin', 'superadmin', 'staff']:
        return True
    
    # Employee can view their own data
    if user_role == 'employee':
        success, _, employee_data = employee_service.get_employee_by_id(employee_id)
        if success and employee_data.get('user_id') == current_user.get('user_id'):
            return True
    
    # Employers can view public profiles
    if user_role == 'employer':
        success, _, employee_data = employee_service.get_employee_by_id(employee_id)
        if success and employee_data.get('profile_visibility') in ['public', 'employers_only']:
            return True
    
    return False


def _can_manage_employee_data(current_user: dict, employee_id: int) -> bool:
    """Check if current user can manage employee data."""
    user_role = current_user.get('role')
    
    # Admin and staff can manage any employee
    if user_role in ['admin', 'superadmin', 'staff']:
        return True
    
    # Employee can manage their own data
    if user_role == 'employee':
        success, _, employee_data = employee_service.get_employee_by_id(employee_id)
        if success and employee_data.get('user_id') == current_user.get('user_id'):
            return True
    
    return False


# Error handlers
@employee_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return create_response(False, "Bad request", status_code=400)


@employee_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors."""
    return create_response(False, "Authentication required", status_code=401)


@employee_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors."""
    return create_response(False, "Access denied", status_code=403)


@employee_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return create_response(False, "Resource not found", status_code=404)


@employee_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle method not allowed errors."""
    return create_response(False, "Method not allowed", status_code=405)


@employee_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(error)}")
    return create_response(False, "Internal server error", status_code=500)


# Health check endpoint
@employee_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return create_response(True, "Employee service is healthy")


def register_employee_routes(app):
    """Register employee routes with the Flask app."""
    app.register_blueprint(employee_bp)