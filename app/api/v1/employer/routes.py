# app/api/v1/employer/routes.py

from flask import Blueprint, request, jsonify, g
import logging
from marshmallow import ValidationError
from werkzeug.utils import secure_filename
import os

from app.utils.auth import (
    login_required, admin_required, employer_required,
    get_current_user, can_access_user_data
)
from app.services.employer_service import employer_service
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
employer_bp = Blueprint('employer', __name__, url_prefix='/api/v1/employers')


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


@employer_bp.route('', methods=['POST'])
def create_employer():
    """
    Create a new employer account.
    ---
    Public endpoint for employer registration.
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Create employer
        success, message, employer_data = employer_service.create_employer(
            data=data,
            current_user_id=None,  # Public registration
            ip_address=ip_address,
            email_service=email_service,
            base_url=BASE_URL
        )
        
        if success:
            logger.info(f"Employer registration successful: {employer_data.get('company_name')}")
            return create_response(True, message, employer_data, 201)
        else:
            logger.warning(f"Employer registration failed: {message}")
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in create_employer endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('', methods=['GET'])
@admin_required
def list_employers():
    """
    List all employers with filtering and pagination.
    ---
    Admin only endpoint.
    """
    try:
        # Get query parameters
        filters = request.args.to_dict()
        
        # Convert string booleans to actual booleans
        bool_fields = ['is_verified', 'is_active']
        for field in bool_fields:
            if field in filters:
                filters[field] = filters[field].lower() in ['true', '1', 'yes']
        
        # Convert numeric fields
        numeric_fields = ['page', 'per_page']
        for field in numeric_fields:
            if field in filters:
                try:
                    filters[field] = int(filters[field])
                except ValueError:
                    return create_response(False, f"Invalid {field} parameter", status_code=400)
        
        # List employers
        success, message, result_data = employer_service.list_employers(filters)
        
        if success:
            return create_response(True, message, result_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in list_employers endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/<int:employer_id>', methods=['GET'])
@login_required
def get_employer(employer_id):
    """
    Get employer details by ID.
    ---
    Accessible by: Admin, the employer themselves, or staff.
    """
    try:
        current_user = get_current_user()
        
        # Get employer data
        success, message, employer_data = employer_service.get_employer_by_id(employer_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        # Check access permissions
        user_role = current_user.get('role')
        employer_user_id = employer_data.get('user_id')
        
        # Admin and staff can access any employer
        if user_role in ['admin', 'superadmin', 'staff']:
            pass
        # Employer can access their own data
        elif user_role == 'employer' and current_user.get('user_id') == employer_user_id:
            pass
        else:
            return create_response(False, "Access denied", status_code=403)
        
        return create_response(True, message, employer_data)
    
    except Exception as e:
        logger.error(f"Error in get_employer endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/profile', methods=['GET'])
@employer_required
def get_my_profile():
    """
    Get current employer's profile.
    ---
    Accessible by: Employers only.
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        
        # Get employer by user ID
        success, message, employer_data = employer_service.get_employer_by_user_id(user_id)
        
        if success:
            return create_response(True, message, employer_data)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in get_my_profile endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/<int:employer_id>', methods=['PUT'])
@login_required
def update_employer(employer_id):
    """
    Update employer profile.
    ---
    Accessible by: Admin, the employer themselves, or staff.
    """
    try:
        current_user = get_current_user()
        
        # Get request data
        data = request.get_json()
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        # First, get employer to check permissions
        success, message, employer_data = employer_service.get_employer_by_id(employer_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        # Check access permissions
        user_role = current_user.get('role')
        employer_user_id = employer_data.get('user_id')
        
        # Admin and staff can update any employer
        if user_role in ['admin', 'superadmin', 'staff']:
            pass
        # Employer can update their own data
        elif user_role == 'employer' and current_user.get('user_id') == employer_user_id:
            pass
        else:
            return create_response(False, "Access denied", status_code=403)
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Update employer
        success, message, updated_data = employer_service.update_employer(
            employer_id=employer_id,
            data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message, updated_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in update_employer endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/profile', methods=['PUT'])
@employer_required
def update_my_profile():
    """
    Update current employer's profile.
    Accessible by: Employers only.
    """
    try:
        current_user = get_current_user()
        print(current_user)
        user_id = current_user.get('user_id')
        
        # Get request data
        data = request.form.to_dict()
        print(data)
        profile_image = request.files.get('profile_image')
        print(profile_image)
        
        if not data:
            return create_response(False, "No data provided", status_code=400)
        
        # Get employer by user ID to find employer_id
        success, message, employer_data = employer_service.get_employer_by_user_id(user_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        employer_id = employer_data.get('id')
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        if profile_image:
            filename = secure_filename(profile_image.filename)
            upload_folder = 'uploads/profile_images'
            os.makedirs(upload_folder, exist_ok=True)
            profile_image_path = os.path.join(upload_folder, filename)
            profile_image.save(profile_image_path)
            data['profile_url'] = profile_image_path
        
        # Update employer
        success, message, updated_data = employer_service.update_employer(
            employer_id=employer_id,
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


@employer_bp.route('/<int:employer_id>', methods=['DELETE'])
@admin_required
def delete_employer(employer_id):
    """
    Delete (deactivate) employer account.
    ---
    Admin only endpoint.
    """
    try:
        current_user = get_current_user()
        
        # Get IP address for audit logging
        ip_address = get_client_ip()
        
        # Delete employer
        success, message = employer_service.delete_employer(
            employer_id=employer_id,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in delete_employer endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/<int:employer_id>/verify', methods=['PUT'])
@admin_required
def verify_employer(employer_id):
    """
    Verify or unverify an employer.
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
        
        # Verify employer
        success, message = employer_service.verify_employer(
            employer_id=employer_id,
            verification_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in verify_employer endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/<int:employer_id>/subscription', methods=['PUT'])
@admin_required
def update_subscription(employer_id):
    """
    Update employer subscription plan.
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
        
        # Update subscription
        success, message = employer_service.update_subscription(
            employer_id=employer_id,
            subscription_data=data,
            current_user_id=current_user.get('user_id'),
            ip_address=ip_address
        )
        
        if success:
            return create_response(True, message)
        else:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
    
    except Exception as e:
        logger.error(f"Error in update_subscription endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/<int:employer_id>/stats', methods=['GET'])
@login_required
def get_employer_stats(employer_id):
    """
    Get employer statistics.
    ---
    Accessible by: Admin, the employer themselves, or staff.
    """
    try:
        current_user = get_current_user()
        
        # First, get employer to check permissions
        success, message, employer_data = employer_service.get_employer_by_id(employer_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        # Check access permissions
        user_role = current_user.get('role')
        employer_user_id = employer_data.get('user_id')
        
        # Admin and staff can access any employer stats
        if user_role in ['admin', 'superadmin', 'staff']:
            pass
        # Employer can access their own stats
        elif user_role == 'employer' and current_user.get('user_id') == employer_user_id:
            pass
        else:
            return create_response(False, "Access denied", status_code=403)
        
        # Get stats
        success, message, stats_data = employer_service.get_employer_stats(employer_id)
        
        if success:
            return create_response(True, message, stats_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_employer_stats endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/stats', methods=['GET'])
@employer_required
def get_my_stats():
    """
    Get current employer's statistics.
    ---
    Accessible by: Employers only.
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('user_id')
        
        # Get employer by user ID to find employer_id
        success, message, employer_data = employer_service.get_employer_by_user_id(user_id)
        
        if not success:
            return create_response(False, message, status_code=404 if "not found" in message.lower() else 400)
        
        employer_id = employer_data.get('id')
        
        # Get stats
        success, message, stats_data = employer_service.get_employer_stats(employer_id)
        
        if success:
            return create_response(True, message, stats_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in get_my_stats endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


@employer_bp.route('/search', methods=['GET'])
def search_employers():
    """
    Search employers (public endpoint with limited data).
    ---
    Public endpoint for searching employers.
    """
    try:
        # Get query parameters
        filters = request.args.to_dict()
        
        # Force active and verified employers only for public search
        filters['is_active'] = True
        filters['is_verified'] = True
        
        # Convert string booleans to actual booleans
        bool_fields = ['is_verified', 'is_active']
        for field in bool_fields:
            if field in filters:
                filters[field] = filters[field] if isinstance(filters[field], bool) else filters[field].lower() in ['true', '1', 'yes']
        
        # Convert numeric fields
        numeric_fields = ['page', 'per_page']
        for field in numeric_fields:
            if field in filters:
                try:
                    filters[field] = int(filters[field])
                except ValueError:
                    return create_response(False, f"Invalid {field} parameter", status_code=400)
        
        # Limit per_page for public endpoint
        if filters.get('per_page', 20) > 50:
            filters['per_page'] = 50
        
        # Search employers
        success, message, result_data = employer_service.list_employers(filters)
        
        if success:
            # Filter out sensitive data for public endpoint
            if 'employers' in result_data:
                for employer in result_data['employers']:
                    # Remove sensitive fields
                    sensitive_fields = [
                        'email', 'phone', 'contact_person_email', 
                        'contact_person_phone', 'jobs_posted_this_month'
                    ]
                    for field in sensitive_fields:
                        employer.pop(field, None)
            
            return create_response(True, message, result_data)
        else:
            return create_response(False, message, status_code=400)
    
    except Exception as e:
        logger.error(f"Error in search_employers endpoint: {str(e)}")
        return create_response(False, "Internal server error", status_code=500)


# Error handlers
@employer_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return create_response(False, "Bad request", status_code=400)


@employer_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors."""
    return create_response(False, "Authentication required", status_code=401)


@employer_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors."""
    return create_response(False, "Access denied", status_code=403)


@employer_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return create_response(False, "Resource not found", status_code=404)


@employer_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle method not allowed errors."""
    return create_response(False, "Method not allowed", status_code=405)


@employer_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(error)}")
    return create_response(False, "Internal server error", status_code=500)


# Health check endpoint
@employer_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return create_response(True, "Employer service is healthy")


def register_employer_routes(app):
    """Register employer routes with the Flask app."""
    app.register_blueprint(employer_bp)