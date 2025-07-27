import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from marshmallow import ValidationError
from functools import wraps
from app.utils.db_abstraction import db

from app.utils.auth import login_required, admin_required, employer_required
from app.schemas.jobs_schema import (
    job_create_schema, job_update_schema, job_filter_schema,
    job_bookmark_schema, job_template_schema, job_category_schema
)


# Create a blueprint for footer routes

footer_bp = Blueprint('footer', __name__, url_prefix='/api/v1/footer')

logger = logging.getLogger(__name__)



def get_client_ip():
    """Get client IP address from request."""
    return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)

@footer_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle Marshmallow validation errors."""
    return jsonify({
        'error': 'Validation failed',
        'details': error.messages
    }), 400


@footer_bp.errorhandler(ValueError)
def handle_value_error(error):
    """Handle ValueError exceptions."""
    return jsonify({'error': str(error)}), 400


@footer_bp.errorhandler(Exception)
def handle_general_error(error):
    """Handle general exceptions."""
    logger.error(f"Unexpected error in jobs API: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

# -- Contact Us Route
@footer_bp.route('/contact', methods=['POST'])
def submit_contact_form():
    """Submit contact form data"""
    try:
        # Get data from the request (form data)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract fields from the form
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        subject = data.get('subject')
        message = data.get('message')
        
        # Validate required fields
        if not all([first_name, last_name, email, phone_number, subject, message]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Insert the contact form data into the database
        contact_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_number': phone_number,
            'subject': subject,
            'message': message
        }
        
        # Insert into the 'contact_us' table
        db.insert('contact_us', contact_data)
        
        # Return a success response
        return jsonify({
            'message': 'Your message has been successfully sent. We will get back to you soon.'
        }), 201

    except Exception as e:
        logger.error(f"Error submitting contact form: {str(e)}")
 
 
        return jsonify({'error': 'Failed to submit the form. Please try again later.'}), 500


# -- Get All Contact Requests Route
@footer_bp.route('/contact', methods=['GET'])
@admin_required  
def get_all_contact_requests():
    """Get all contact us requests"""
    try:
        contact_requests = db.select('contact_us', '*', '', [])
        if not contact_requests:
            return jsonify({'message': 'No contact requests found'}), 404

        return jsonify(contact_requests)
    
    except Exception as e:
        logger.error(f"Error fetching contact requests: {str(e)}")
        return jsonify({'error': 'Failed to fetch contact requests'}), 500


#-- Terms of Service Route 
@footer_bp.route('/terms', methods=['GET'])
def get_terms_of_service():
    """Fetch the Terms of Service content"""
    try:
       
        terms = db.select('terms_of_service', ['title', 'content', 'updated_at'], '', [])
        
        if not terms:
            return jsonify({'error': 'Terms of Service not found'}), 404
        
        return jsonify({
            'title': terms[0]['title'],
            'content': terms[0]['content'],
            'updated_at': terms[0]['updated_at']
        })

    except Exception as e:
        logger.error(f"Error fetching Terms of Service: {str(e)}")
        return jsonify({'error': 'Failed to fetch Terms of Service'}), 500


#-- Privacy Policy Route
@footer_bp.route('/privacy', methods=['GET'])
def get_privacy_policy():
    """Fetch the Privacy Policy content"""
    try:
        privacy_policy = db.select('privacy_policy', ['title', 'content', 'updated_at'], '', [])

        if not privacy_policy:
            return jsonify({'error': 'Privacy Policy not found'}), 404

        return jsonify({
            'title': privacy_policy[0]['title'],
            'content': privacy_policy[0]['content'],
            'updated_at': privacy_policy[0]['updated_at']
        })

    except Exception as e:
        logger.error(f"Error fetching Privacy Policy: {str(e)}")
        return jsonify({'error': 'Failed to fetch Privacy Policy'}), 500





# Health Check
@footer_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        
    })


# Register error handlers
@footer_bp.app_errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Resource not found'}), 404


@footer_bp.app_errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({'error': 'Method not allowed'}), 405

def register_footer_routes(app):
    """Register employee routes with the Flask app."""
    app.register_blueprint(footer_bp)

