# app/api/v1/jobs/routes.py

import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from marshmallow import ValidationError
from functools import wraps
from app.utils.db_abstraction import db
from werkzeug.utils import secure_filename
from datetime import datetime
import os


from app.services.jobs_service import JobsService
from app.utils.auth import login_required, admin_required, employer_required
from app.schemas.jobs_schema import (
    job_create_schema, job_update_schema, job_filter_schema,
    job_bookmark_schema, job_template_schema, job_category_schema
)

# Create blueprint
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/v1/jobs')

logger = logging.getLogger(__name__)


def get_client_ip():
    """Get client IP address from request."""
    return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)



def employee_required(f):
    """Decorator to ensure the user is an employee."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user') or g.current_user['role'] != 'employee':
            return jsonify({'error': 'Employee role is required to apply for the job'}), 403
        return f(*args, **kwargs)
    return decorated_function


def employer_or_admin_required(f):
    """Decorator that requires user to be employer or admin."""
    @wraps(f)
    @login_required  # Ensure login_required is applied first
    def decorated_function(*args, **kwargs):
        # Double-check that we have current_user after login_required
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_role = g.current_user.get('role')
        if user_role not in ['employer', 'admin', 'superadmin']:
            return jsonify({'error': 'Employer or admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@jobs_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle Marshmallow validation errors."""
    return jsonify({
        'error': 'Validation failed',
        'details': error.messages
    }), 400


@jobs_bp.errorhandler(ValueError)
def handle_value_error(error):
    """Handle ValueError exceptions."""
    return jsonify({'error': str(error)}), 400


@jobs_bp.errorhandler(Exception)
def handle_general_error(error):
    """Handle general exceptions."""
    logger.error(f"Unexpected error in jobs API: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


# Job CRUD Operations

@jobs_bp.route('/', methods=['POST'])
@employer_or_admin_required
def create_job():
    """Create a new job posting."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user = g.current_user
        user_id = user['user_id']
        print(user_id)
        
        # Get employer_id - for employers, get their employer record
        if user['role'] == 'employer':
            # Get employer record for the user
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', ['id'], 'user_id = ? AND is_active = 1', [user_id])

            if not employer_record:
                return jsonify({'error': 'Employer profile not found'}), 400
            employer_id = list(employer_record)[0]['id']
        else:
            # Admin can specify employer_id or it must be provided
            employer_id = data.get('employer_id')
            if not employer_id:
                return jsonify({'error': 'employer_id is required for admin users'}), 400
        
        data.pop('employer_id', None)
        # Create the job
        job = JobsService.create_job(
            employer_id=employer_id,
            job_data=data,
            user_id=user_id,
            ip_address=get_client_ip()
        )
        
        return jsonify({
            'message': 'Job created successfully',
            'job': job
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'details': e.messages
        }), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        return jsonify({'error': 'Failed to create job'}), 500


@jobs_bp.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get a specific job by ID."""
    try:
        # Record job view if user is authenticated
        user_id = None
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user['id']
        
        # Record the view for analytics
        JobsService.record_job_view(
            job_id=job_id,
            user_id=user_id,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent'),
            referrer=request.headers.get('Referer')
        )
        
        job = JobsService.get_job_by_id(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({'job': job})
        
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve job'}), 500


@jobs_bp.route('/<int:job_id>', methods=['PUT'])
@employer_or_admin_required
def update_job(job_id):
    """Update an existing job."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user = g.current_user
        user_id = user['user_id']
        
        # Get employer_id for authorization
        employer_id = None
        if user['role'] == 'employer':
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', 'id', 'user_id = ? AND is_active = 1', [user_id])
            if employer_record:
                employer_id = list(employer_record)[0]['id']
        
        # Update the job
        job = JobsService.update_job(
            job_id=job_id,
            job_data=data,
            user_id=user_id,
            employer_id=employer_id,
            ip_address=get_client_ip()
        )
        
        return jsonify({
            'message': 'Job updated successfully',
            'job': job
        })
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'details': e.messages
        }), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        return jsonify({'error': 'Failed to update job'}), 500


@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
@employer_or_admin_required
def delete_job(job_id):
    """Delete a job (soft delete by default)."""
    try:
        user = g.current_user
        user_id = user['user_id']
        
        # Check if hard delete is requested (admin only)
        hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'
        if hard_delete and user['role'] not in ['admin', 'superadmin']:
            return jsonify({'error': 'Hard delete requires admin privileges'}), 403
        
        # Get employer_id for authorization
        employer_id = None
        if user['role'] == 'employer':
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', ['id'], 'user_id = ? AND is_active = 1', [user_id])
            if employer_record:
                employer_id = list(employer_record)[0]['id']
        
        # Delete the job
        success = JobsService.delete_job(
            job_id=job_id,
            user_id=user_id,
            employer_id=employer_id,
            hard_delete=hard_delete,
            ip_address=get_client_ip()
        )
        
        if success:
            return jsonify({
                'message': 'Job deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete job'}), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete job'}), 500


# Job Listing and Search

@jobs_bp.route('/', methods=['GET'])
def get_jobs():
    """Get a paginated list of jobs with filtering."""
    try:
        # Get filter parameters from query string
        filters = dict(request.args)
        
        # Handle list parameters (convert comma-separated strings to lists)
        list_params = ['employment_type', 'experience_level', 'education_level', 
                      'remote_type', 'status', 'priority', 'skills']
        for param in list_params:
            if param in filters and filters[param]:
                filters[param] = [item.strip() for item in filters[param].split(',')]
        
        # Convert boolean parameters
        bool_params = ['is_remote', 'is_featured', 'is_urgent', 'accepting_applications', 'employer_verified']
        for param in bool_params:
            if param in filters:
                filters[param] = filters[param].lower() in ['true', '1', 'yes']
        
        # Convert date parameters
        date_params = ['posted_after', 'posted_before', 'expires_after', 'expires_before']
        for param in date_params:
            if param in filters and filters[param]:
                try:
                    from datetime import datetime
                    filters[param] = datetime.fromisoformat(filters[param]).date()
                except ValueError:
                    return jsonify({'error': f'Invalid date format for {param}'}), 400
        
        # Convert numeric parameters
        numeric_params = ['category_id', 'employer_id', 'page', 'per_page']
        for param in numeric_params:
            if param in filters and filters[param]:
                try:
                    filters[param] = int(filters[param])
                except ValueError:
                    return jsonify({'error': f'Invalid numeric value for {param}'}), 400
        
        # Convert decimal parameters
        decimal_params = ['salary_min', 'salary_max']
        for param in decimal_params:
            if param in filters and filters[param]:
                try:
                    from decimal import Decimal
                    filters[param] = Decimal(filters[param])
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid decimal value for {param}'}), 400
        
        # Get jobs list
        jobs, total_count = JobsService.get_jobs_list(filters)
        
        # Calculate pagination info
        page = filters.get('page', 1)
        per_page = filters.get('per_page', 20)
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'jobs': jobs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'error': 'Invalid filter parameters',
            'details': e.messages
        }), 400
    except Exception as e:
        logger.error(f"Error retrieving jobs list: {str(e)}")
        return jsonify({'error': 'Failed to retrieve jobs'}), 500


@jobs_bp.route('/employer/<int:employer_id>', methods=['GET'])
@login_required
def get_employer_jobs(employer_id):
    """Get jobs for a specific employer."""
    try:
        # Check authorization - employers can only see their own jobs
        user = g.current_user
        if user['role'] == 'employer':
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', ['id'], 'user_id = ? AND is_active = 1', [user['user_id']])
            if not employer_record or list(employer_record)[0]['id'] != employer_id:
                return jsonify({'error': 'Not authorized to view these jobs'}), 403
        elif user['role'] not in ['admin', 'superadmin']:
            return jsonify({'error': 'Not authorized to view these jobs'}), 403
        
        # Get filter parameters
        filters = dict(request.args)
        
        # Process filters similar to get_jobs
        list_params = ['employment_type', 'experience_level', 'education_level', 
                      'remote_type', 'status', 'priority', 'skills']
        for param in list_params:
            if param in filters and filters[param]:
                filters[param] = [item.strip() for item in filters[param].split(',')]
        
        bool_params = ['is_remote', 'is_featured', 'is_urgent']
        for param in bool_params:
            if param in filters:
                filters[param] = filters[param].lower() in ['true', '1', 'yes']
        
        numeric_params = ['page', 'per_page']
        for param in numeric_params:
            if param in filters and filters[param]:
                try:
                    filters[param] = int(filters[param])
                except ValueError:
                    return jsonify({'error': f'Invalid numeric value for {param}'}), 400
        
        # Get jobs for the employer
        jobs, total_count = JobsService.get_jobs_list(filters, employer_id=employer_id)
        
        # Calculate pagination info
        page = filters.get('page', 1)
        per_page = filters.get('per_page', 20)
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'jobs': jobs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving employer jobs: {str(e)}")
        return jsonify({'error': 'Failed to retrieve jobs'}), 500


# Job Statistics

@jobs_bp.route('/<int:job_id>/stats', methods=['GET'])
@employer_or_admin_required
def get_job_stats(job_id):
    """Get statistics for a specific job."""
    try:
        user = g.current_user
        
        # Get employer_id for authorization
        employer_id = None
        if user['role'] == 'employer':
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', ['id'], 'user_id = ? AND is_active = 1', [user['user_id']])
            if employer_record:
                employer_id = list(employer_record)[0]['id']
        stats = JobsService.get_job_statistics(job_id, employer_id)
        
        return jsonify({'stats': stats})
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error retrieving job stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve job statistics'}), 500


# Job Bookmarks

@jobs_bp.route('/<int:job_id>/bookmark', methods=['POST'])
@login_required
def bookmark_job(job_id):
    """Bookmark a job."""
    try:
        data = request.get_json() or {}
        user_id = g.current_user['id']
        notes = data.get('notes')
        
        success = JobsService.bookmark_job(job_id, user_id, notes)
        
        if success:
            return jsonify({'message': 'Job bookmarked successfully'}), 201
        else:
            return jsonify({'error': 'Failed to bookmark job'}), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error bookmarking job: {str(e)}")
        return jsonify({'error': 'Failed to bookmark job'}), 500


@jobs_bp.route('/<int:job_id>/bookmark', methods=['DELETE'])
@login_required
def remove_bookmark(job_id):
    """Remove a job bookmark."""
    try:
        user_id = g.current_user['id']
        
        success = JobsService.remove_bookmark(job_id, user_id)
        
        if success:
            return jsonify({'message': 'Bookmark removed successfully'})
        else:
            return jsonify({'error': 'Failed to remove bookmark'}), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error removing bookmark: {str(e)}")
        return jsonify({'error': 'Failed to remove bookmark'}), 500


@jobs_bp.route('/bookmarks', methods=['GET'])
@login_required
def get_user_bookmarks():
    """Get bookmarked jobs for the current user."""
    try:
        user_id = g.current_user['id']
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        bookmarks, total_count = JobsService.get_user_bookmarks(user_id, page, per_page)
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'bookmarks': bookmarks,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving bookmarks: {str(e)}")
        return jsonify({'error': 'Failed to retrieve bookmarks'}), 500


# Job Categories

@jobs_bp.route('/categories', methods=['GET'])
def get_job_categories():
    """Get all job categories."""
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        categories = JobsService.get_job_categories(include_inactive)
        
        return jsonify({'categories': categories})
        
    except Exception as e:
        logger.error(f"Error retrieving categories: {str(e)}")
        return jsonify({'error': 'Failed to retrieve categories'}), 500


@jobs_bp.route('/categories', methods=['POST'])
@admin_required
def create_job_category():
    """Create a new job category (admin only)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = g.current_user['id']
        
        category = JobsService.create_job_category(
            category_data=data,
            user_id=user_id,
            ip_address=get_client_ip()
        )
        
        return jsonify({
            'message': 'Category created successfully',
            'category': category
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'details': e.messages
        }), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        return jsonify({'error': 'Failed to create category'}), 500


# Job Templates

@jobs_bp.route('/templates', methods=['GET'])
@employer_or_admin_required
def get_job_templates():
    """Get job templates for the current employer."""
    try:
        user = g.current_user
        
        if user['role'] == 'employer':
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', ['id'], 'user_id = ? AND is_active = 1', [user['user_id']])
            if not employer_record:
                return jsonify({'error': 'Employer profile not found'}), 400
            employer_id = list(employer_record)[0]['id']
        else:
            # Admin can specify employer_id
            employer_id = request.args.get('employer_id')
            if not employer_id:
                return jsonify({'error': 'employer_id parameter required for admin users'}), 400
            employer_id = int(employer_id)
        
        templates = JobsService.get_employer_templates(employer_id)
        
        return jsonify({'templates': templates})
        
    except Exception as e:
        logger.error(f"Error retrieving templates: {str(e)}")
        return jsonify({'error': 'Failed to retrieve templates'}), 500


@jobs_bp.route('/templates', methods=['POST'])
@employer_or_admin_required
def create_job_template():
    """Create a new job template."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user = g.current_user
        user_id = user['user_id']
        
        if user['role'] == 'employer':
            from app.utils.db_abstraction import db
            employer_record = db.select('employers', ['id'], 'user_id = ? AND is_active = 1', [user_id])
            if not employer_record:
                return jsonify({'error': 'Employer profile not found'}), 400
            employer_id = list(employer_record)[0]['id']
        else:
            # Admin can specify employer_id
            employer_id = data.get('employer_id')
            if not employer_id:
                return jsonify({'error': 'employer_id is required for admin users'}), 400
        
        template = JobsService.create_job_template(
            employer_id=employer_id,
            template_data=data,
            user_id=user_id,
            ip_address=get_client_ip()
        )
        
        return jsonify({
            'message': 'Template created successfully',
            'template': template
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation failed',
            'details': e.messages
        }), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        return jsonify({'error': 'Failed to create template'}), 500


# Admin Functions

@jobs_bp.route('/<int:job_id>/approve', methods=['POST'])
@admin_required
def approve_job(job_id):
    """Approve a job (admin only)."""
    try:
        user_id = g.current_user['id']
        
        success = JobsService.approve_job(
            job_id=job_id,
            admin_user_id=user_id,
            ip_address=get_client_ip()
        )
        
        if success:
            return jsonify({'message': 'Job approved successfully'})
        else:
            return jsonify({'error': 'Failed to approve job'}), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error approving job: {str(e)}")
        return jsonify({'error': 'Failed to approve job'}), 500


@jobs_bp.route('/<int:job_id>/reject', methods=['POST'])
@admin_required
def reject_job(job_id):
    """Reject a job (admin only)."""
    try:
        data = request.get_json()
        if not data or 'reason' not in data:
            return jsonify({'error': 'Rejection reason is required'}), 400
        
        user_id = g.current_user['id']
        reason = data['reason']
        
        success = JobsService.reject_job(
            job_id=job_id,
            admin_user_id=user_id,
            reason=reason,
            ip_address=get_client_ip()
        )
        
        if success:
            return jsonify({'message': 'Job rejected successfully'})
        else:
            return jsonify({'error': 'Failed to reject job'}), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error rejecting job: {str(e)}")
        return jsonify({'error': 'Failed to reject job'}), 500


# Function to check allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}  
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@jobs_bp.route('/apply', methods=['POST'])
@employee_required  
def apply_job():
    """Apply for a job"""
    try:
        # Ensure the data is provided
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400

        # Get job application data from the request
        data = request.form  # request.form is used to get form data (including file uploads)
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract user and job details from the request
        user = g.current_user
        user_id = user['user_id']
        job_id = data.get('job_id')
        
        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400
        
       
        # Validate the job exists and is still open for applications
        job = db.select('jobs', ['id', 'status', 'application_deadline', 'max_applications', 'applications_count',"employer_id"], 'id = ?', [job_id])
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Check if the user has already applied for this job
        existing_application = db.select('job_applications', ['id'], 'user_id = ? AND job_id = ?', [user_id, job_id])
        
        if existing_application:
            return jsonify({'error': 'You have already applied for this job'}), 400
        
        job = job[0]  # Unwrap the result
        
        if job['status'] != 'active':
            return jsonify({'error': 'Job is no longer active'}), 400
        
        if job['applications_count'] >= job['max_applications']:
            return jsonify({'error': 'Maximum applications reached for this job'}), 400
        
        if job['application_deadline'] and datetime.now() > datetime.strptime(job['application_deadline'], '%Y-%m-%d'):
            return jsonify({'error': 'The application deadline has passed'}), 400
        
        # Check if resume is part of the form data
        resume = request.files['resume']

        if resume.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if resume and allowed_file(resume.filename):
            # Ensure the 'uploads/resumes' directory exists, create it if it doesn't
            upload_folder = 'uploads/resumes'
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)  # Create directory if it doesn't exist

            # Secure the filename to avoid malicious characters
            filename = secure_filename(resume.filename)
            resume_path = os.path.join(upload_folder, filename)
            resume.save(resume_path)
            
            # Get file details
            resume_size = os.path.getsize(resume_path)
            resume_uploaded_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Store the application data in the database
            application_data = {
                'user_id': user_id,
                'job_id': job_id,
                'application_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'pending',
                'resume_filename': filename,
                'resume_path': resume_path,
                'resume_size': resume_size,
                'resume_uploaded_at': resume_uploaded_at
            }
            db.insert('job_applications', application_data)
            
             # Initialize count to 0
            employer_id=job['employer_id']
            applications_count= db.select('jobs', ['applications_count'], 'id = ?', [job_id])
            if not applications_count:
                return jsonify({'error': 'Job not found'}), 404
            
            applications_count = applications_count[0]['applications_count']+1
            print(applications_count)
            count_data = {
                'applications_count': applications_count  # Increment the count
            }
            

            db.execute_raw_query('UPDATE jobs SET applications_count = applications_count + 1 WHERE id = ?', [job_id],fetch=False)

            # Update the job's application count
            # db.execute_sql('UPDATE jobs SET applications_count = applications_count + 1 WHERE id = ?', [job_id])

            return jsonify({
                'message': 'Application with resume submitted successfully',
                'user_id': user_id,
                'job_id': job_id,
                'status': 'pending',
                'resume_filename': filename,
                'resume_size': resume_size
            }), 201
        
        return jsonify({'error': 'Invalid resume file format'}), 400

    except Exception as e:
        print(e)
        logger.error(f"Error applying for job: {str(e)}")
        return jsonify({'error': 'Failed to apply for job'}), 500
        
    
    except Exception as e:
        print(e)
        # Log the error and return a server error response
        logger.error(f"Error applying for job: {str(e)}")
        return jsonify({'error': 'Failed to apply for job'}), 500


# List Job Applications
@jobs_bp.route('/applications', methods=['GET'])
@login_required
def list_job_applications():
    """List job applications for the current user"""
    try:
        user = g.current_user
        user_id = user['user_id']
        role = user['role']
        

        if role == 'employee':
            applications = db.select('job_applications', '*', 'user_id = ?', [user_id])
            print(applications)
        elif role in ['employer']:
            employer = db.select('employers', ['id'], 'user_id = ?', [user_id])
            if not employer:
                return jsonify({'error': 'Employer not found'}), 404
            
            employer_id = employer[0]['id']
            employer_jobs = db.select('jobs', ['id'], 'employer_id = ?', [employer_id])
            job_ids = [job['id'] for job in employer_jobs]
            if not job_ids:
                return jsonify([])
            
            placeholders = ', '.join(['?'] * len(job_ids))
            query = f"job_id IN ({placeholders})"
            applications = db.select('job_applications', '*', query, job_ids)
        else:
            return jsonify({'error': 'Unauthorized'}), 403
        return jsonify(applications)
    
    except Exception as e:
        logger.error(f"Error fetching job applications: {str(e)}")
        return jsonify({'error': 'Failed to fetch applications'}), 500


@jobs_bp.route('/applications/<int:job_id>', methods=['GET'])
@employer_or_admin_required
def list_job_applications_by_job_id(job_id):
    """List job applications for a specific job"""
    try:
        
        job = db.select('jobs', ['id', 'status'], 'id = ?', [job_id])
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        job = job[0]   
        if job['status'] != 'active':
            return jsonify({'error': 'Job is no longer active'}), 400
        
        applications = db.select('job_applications', '*', 'job_id = ?', [job_id])
        
        return jsonify(applications)
    
    except Exception as e:
        logger.error(f"Error fetching job applications for job {job_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch applications'}), 500


@jobs_bp.route('/save', methods=['POST'])
@employee_required  # Ensures that only employees can save jobs
def save_job():
    """Save a job for the current employee"""
    try:
        # Get job save data from the request
        data = request.get_json()
        if not data or 'job_id' not in data:
            return jsonify({'error': 'Job ID is required'}), 400

        job_id = data['job_id']
        user = g.current_user
        user_id = user['user_id']

        # Validate if the job exists
        job = db.select('jobs', ['id'], 'id = ?', [job_id])
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        # Check if the user has already saved the job
        existing_saved_job = db.select('saved_jobs', ['id'], 'user_id = ? AND job_id = ?', [user_id, job_id])
        if existing_saved_job:
            return jsonify({'error': 'You have already saved this job'}), 400
        
        # Insert the saved job entry into the saved_jobs table
        saved_job_data = {
            'user_id': user_id,
            'job_id': job_id,
        }
        db.insert('saved_jobs', saved_job_data)

        return jsonify({
            'message': 'Job saved successfully',
            'user_id': user_id,
            'job_id': job_id
        }), 201

    except Exception as e:
        logger.error(f"Error saving job: {str(e)}")
        return jsonify({'error': 'Failed to save job'}), 500




@jobs_bp.route('/saved/<int:user_id>', methods=['GET'])
@employee_required  # Ensures that only employees can view saved jobs
def get_saved_jobs(user_id):
    """Get all saved jobs for a specific employee"""
    try:
       
        user = g.current_user
        if user['user_id'] != user_id and user['role'] != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Fetch saved jobs for the employee (user_id)
        saved_jobs = db.select('saved_jobs', '*', 'user_id = ?', [user_id])

        # Check if there are any saved jobs
        if not saved_jobs:
            return jsonify({'message': 'No saved jobs found for this employee'}), 404

        # Fetch job details for each saved job
        saved_jobs_with_details = []
        for saved_job in saved_jobs:
            # Get job details like title and description for each saved job
            job = db.select('jobs', ['id', 'title', 'description'], 'id = ?', [saved_job['job_id']])
            if job:
                saved_jobs_with_details.append({
                    'saved_job_id': saved_job['id'],
                    'job_id': job[0]['id'],
                    'title': job[0]['title'],
                    'description': job[0]['description'],
                    'saved_at': saved_job['created_at']
                })

        return jsonify(saved_jobs_with_details)

    except Exception as e:
        logger.error(f"Error fetching saved jobs for employee {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch saved jobs'}), 500


# Health Check
@jobs_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'jobs-api',
        'timestamp': JobsService.datetime.now().isoformat()
    })


# Register error handlers
@jobs_bp.app_errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Resource not found'}), 404


@jobs_bp.app_errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({'error': 'Method not allowed'}), 405

def register_jobs_routes(app):
    """Register employee routes with the Flask app."""
    app.register_blueprint(jobs_bp)