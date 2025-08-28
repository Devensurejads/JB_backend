# app/__init__.py - Minimal working version

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS

# Import route registration functions
from app.api.v1.employer.routes import register_employer_routes
from app.api.v1.employee.routes import register_employee_routes
from app.api.v1.jobs.routes import register_jobs_routes
from app.api.v1.footer.routes import register_footer_routes

def create_app(config_name='development'):
    """
    Create and configure the Flask application.
    
    Args:
        config_name (str): Configuration environment name
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'job_management.db')
    
    # Initialize CORS
    CORS(app, origins=['http://localhost:4200', 'http://127.0.0.1:4200'])
    
    # Initialize database
    try:
        from app.utils.db_abstraction import init_db, execute_sql_files
        # init_db()
        execute_sql_files()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
    
    # Register blueprints
    register_blueprints(app)
    
    # Register employer routes
    register_employer_routes(app)
    
    # Register employee routes
    register_employee_routes(app)

    # Register jobs routes
    register_jobs_routes(app)

    # Register footer routes
    register_footer_routes(app)

    # Register error handlers
    register_error_handlers(app)

    # Setup basic logging
    setup_logging(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    print("🚀 Flask application created successfully")
    return app


def register_blueprints(app):
    """Register all application blueprints."""
    try:
        from app.api.v1.auth.routes import auth_bp
        app.register_blueprint(auth_bp)
        print("✅ Auth blueprint registered")
    except Exception as e:
        print(f"⚠️ Error registering auth blueprint: {e}")
        print("Continuing without auth blueprint...")
    
    # Add a simple health check route
    @app.route('/')
    def health_check():
        return {
            'status': 'OK', 
            'message': 'Job Management System API is running',
            'version': '1.0.0'
        }, 200
    
    @app.route('/health')
    def health():
        return {
            'status': 'healthy', 
            'service': 'job-management-api',
            'database': 'connected'
        }, 200


def setup_logging(app):
    """Setup application logging."""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Setup file handler
        file_handler = RotatingFileHandler(
            'logs/job_management.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Job Management System startup')


def register_error_handlers(app):
    """Register global error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return {
            'success': False,
            'message': 'Bad request',
            'data': None
        }, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {
            'success': False,
            'message': 'Unauthorized',
            'data': None
        }, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {
            'success': False,
            'message': 'Forbidden',
            'data': None
        }, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {
            'success': False,
            'message': 'Resource not found',
            'data': None
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {
            'success': False,
            'message': 'Internal server error',
            'data': None
        }, 500