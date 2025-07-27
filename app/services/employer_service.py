# app/services/employer_service.py

import logging
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from marshmallow import ValidationError

from app.utils.db_abstraction import db
from app.utils.password_utils import hash_password
from app.schemas.employer_schema import (
    employer_registration_schema, employer_update_schema,
    employer_response_schema, employer_list_response_schema,
    employer_filter_schema, employer_verification_schema,
    employer_subscription_schema, employer_stats_schema
)

# Configure logging
logger = logging.getLogger(__name__)


class EmployerService:
    """Service class for employer management operations."""
    
    @staticmethod
    def create_employer(data: Dict, current_user_id: int = None, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Create a new employer account.
        
        Args:
            data (Dict): Employer registration data
            current_user_id (int): ID of user creating the employer
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employer_data)
        """
        try:
            # Validate input data
            try:
                validated_data = employer_registration_schema.load(data)
            except ValidationError as e:
                logger.warning(f"Validation error in employer creation: {e.messages}")
                return False, f"Validation error: {e.messages}", None
            
            # Check if username already exists
            if db.record_exists('users', 'username = ?', [validated_data['username']]):
                return False, "Username already exists", None
            
            # Check if email already exists
            if db.record_exists('users', 'email = ?', [validated_data['email']]):
                return False, "Email already exists", None
            
            # Hash password using improved utility
            try:
                password_hash = hash_password(validated_data['password'])
            except Exception as e:
                logger.error(f"Password hashing failed: {str(e)}")
                return False, "Password hashing failed", None
            
            # Prepare user data
            user_data = {
                'username': validated_data['username'],
                'password_hash': password_hash,
                'email': validated_data['email'],
                'first_name': validated_data.get('first_name'),
                'last_name': validated_data.get('last_name'),
                'role': 'employer',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Create user account
            user_id = db.insert('users', user_data)
            if not user_id:
                return False, "Failed to create user account", None
            
            # Prepare employer data
            employer_data = {
                'user_id': user_id,
                'company_name': validated_data['company_name'],
                'company_description': validated_data.get('company_description'),
                'industry': validated_data.get('industry'),
                'company_size': validated_data.get('company_size'),
                'website': validated_data.get('website'),
                'phone': validated_data.get('phone'),
                'address': validated_data.get('address'),
                'city': validated_data.get('city'),
                'state': validated_data.get('state'),
                'country': validated_data.get('country'),
                'zip_code': validated_data.get('zip_code'),
                'linkedin_company_url': validated_data.get('linkedin_company_url'),
                'founded_year': validated_data.get('founded_year'),
                'company_type': validated_data.get('company_type', 'private'),
                'registration_number': validated_data.get('registration_number'),
                'tax_id': validated_data.get('tax_id'),
                'contact_person_name': validated_data.get('contact_person_name'),
                'contact_person_email': validated_data.get('contact_person_email'),
                'contact_person_phone': validated_data.get('contact_person_phone'),
                'contact_person_position': validated_data.get('contact_person_position'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Create employer profile
            employer_id = db.insert('employers', employer_data)
            if not employer_id:
                # Rollback user creation
                db.delete('users', 'id = ?', [user_id])
                return False, "Failed to create employer profile", None
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='CREATE',
                entity_type='employer',
                entity_id=employer_id,
                changes={'created': 'New employer account created'},
                ip_address=ip_address
            )
            
            # Get complete employer data for response
            employer = EmployerService.get_employer_by_id(employer_id)
            
            logger.info(f"Employer created successfully: {employer_id}")
            return True, "Employer account created successfully", employer[2]
            
        except Exception as e:
            logger.error(f"Error creating employer: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employer_by_id(employer_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get employer by ID with user information.
        
        Args:
            employer_id (int): Employer ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employer_data)
        """
        try:
            # Get employer with user data using JOIN
            query = """
                SELECT e.*, u.username, u.email, u.first_name, u.last_name, u.role,
                       u.is_active as user_is_active, u.created_at as user_created_at
                FROM employers e
                JOIN users u ON e.user_id = u.id
                WHERE e.id = ?
            """
            
            result = db.execute_raw_query(query, [employer_id])
            
            if not result:
                return False, "Employer not found", None
            
            employer_data = result[0]
            
            # Serialize with schema
            serialized_data = employer_response_schema.dump(employer_data)
            
            return True, "Employer retrieved successfully", serialized_data
            
        except Exception as e:
            logger.error(f"Error getting employer {employer_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employer_by_user_id(user_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get employer by user ID.
        
        Args:
            user_id (int): User ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employer_data)
        """
        try:
            # Get employer with user data using JOIN
            query = """
                SELECT e.*, u.username, u.email, u.first_name, u.last_name, u.role,
                       u.is_active as user_is_active, u.created_at as user_created_at
                FROM employers e
                JOIN users u ON e.user_id = u.id
                WHERE e.user_id = ?
            """
            
            result = db.execute_raw_query(query, [user_id])
            
            if not result:
                return False, "Employer not found", None
            
            employer_data = result[0]
            
            # Serialize with schema
            serialized_data = employer_response_schema.dump(employer_data)
            
            return True, "Employer retrieved successfully", serialized_data
            
        except Exception as e:
            logger.error(f"Error getting employer by user ID {user_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def update_employer(employer_id: int, data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Update employer profile.
        
        Args:
            employer_id (int): Employer ID
            data (Dict): Update data
            current_user_id (int): ID of user making the update
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employer_data)
        """
        try:
            # Validate input data
            try:
                validated_data = employer_update_schema.load(data)
            except ValidationError as e:
                logger.warning(f"Validation error in employer update: {e.messages}")
                return False, f"Validation error: {e.messages}", None
            
            # Check if employer exists
            existing_employer = db.get_by_id('employers', employer_id)
            if not existing_employer:
                return False, "Employer not found", None
            
            # Prepare update data
            update_data = validated_data.copy()
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Update employer
            success = db.update('employers', update_data, 'id = ?', [employer_id])
            
            if not success:
                return False, "Failed to update employer", None
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='UPDATE',
                entity_type='employer',
                entity_id=employer_id,
                changes={'updated_fields': list(validated_data.keys())},
                ip_address=ip_address
            )
            
            # Get updated employer data
            employer = EmployerService.get_employer_by_id(employer_id)
            
            logger.info(f"Employer updated successfully: {employer_id}")
            return True, "Employer updated successfully", employer[2]
            
        except Exception as e:
            logger.error(f"Error updating employer {employer_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def delete_employer(employer_id: int, current_user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """
        Delete employer (soft delete by deactivating).
        
        Args:
            employer_id (int): Employer ID
            current_user_id (int): ID of user making the deletion
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Check if employer exists
            existing_employer = db.get_by_id('employers', employer_id)
            if not existing_employer:
                return False, "Employer not found"
            
            # Soft delete by deactivating
            update_data = {
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            success = db.update('employers', update_data, 'id = ?', [employer_id])
            
            if not success:
                return False, "Failed to deactivate employer"
            
            # Also deactivate the user account
            db.update('users', {'is_active': False}, 'id = ?', [existing_employer['user_id']])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='DELETE',
                entity_type='employer',
                entity_id=employer_id,
                changes={'deactivated': True},
                ip_address=ip_address
            )
            
            logger.info(f"Employer deactivated successfully: {employer_id}")
            return True, "Employer deactivated successfully"
            
        except Exception as e:
            logger.error(f"Error deactivating employer {employer_id}: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def list_employers(filters: Dict = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        List employers with filtering and pagination.
        
        Args:
            filters (Dict): Filter parameters
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, result_data)
        """
        try:
            # Validate filters
            if filters:
                try:
                    validated_filters = employer_filter_schema.load(filters)
                except ValidationError as e:
                    return False, f"Filter validation error: {e.messages}", None
            else:
                validated_filters = employer_filter_schema.load({})

            # Build WHERE conditions
            where_conditions = []
            params = []
            
            # Search functionality
            if validated_filters.get('search'):
                search_term = f"%{validated_filters['search']}%"
                where_conditions.append("""
                    (e.company_name LIKE ? OR e.industry LIKE ? OR 
                     e.city LIKE ? OR e.country LIKE ? OR u.username LIKE ?)
                """)
                params.extend([search_term] * 5)
            
            # Specific filters
            if validated_filters.get('company_name'):
                where_conditions.append("e.company_name LIKE ?")
                params.append(f"%{validated_filters['company_name']}%")
            
            if validated_filters.get('industry'):
                where_conditions.append("e.industry = ?")
                params.append(validated_filters['industry'])
            
            if validated_filters.get('company_size'):
                where_conditions.append("e.company_size = ?")
                params.append(validated_filters['company_size'])
            
            if validated_filters.get('city'):
                where_conditions.append("e.city = ?")
                params.append(validated_filters['city'])
            
            if validated_filters.get('country'):
                where_conditions.append("e.country = ?")
                params.append(validated_filters['country'])
            
            if validated_filters.get('is_verified') is not None:
                where_conditions.append("e.is_verified = ?")
                params.append(validated_filters['is_verified'])
            
            if validated_filters.get('is_active') is not None:
                where_conditions.append("e.is_active = ?")
                params.append(validated_filters['is_active'])
            
            if validated_filters.get('subscription_plan'):
                where_conditions.append("e.subscription_plan = ?")
                params.append(validated_filters['subscription_plan'])
            
            # Date range filters
            if validated_filters.get('created_after'):
                where_conditions.append("e.created_at >= ?")
                params.append(validated_filters['created_after'].isoformat())
            
            if validated_filters.get('created_before'):
                where_conditions.append("e.created_at <= ?")
                params.append(validated_filters['created_before'].isoformat())
            
            # Build final WHERE clause
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Count total records
            count_query = f"""
                SELECT COUNT(*) as total
                FROM employers e
                JOIN users u ON e.user_id = u.id
                WHERE {where_clause}
            """
            count_result = db.execute_raw_query(count_query, params)
            total_count = count_result[0]['total'] if count_result else 0
            # Build ORDER BY clause
            sort_by = validated_filters.get('sort_by', 'created_at')
            sort_order = validated_filters.get('sort_order', 'desc')
            
            # Map sort fields to actual table columns
            sort_mapping = {
                'created_at': 'e.created_at',
                'company_name': 'e.company_name',
                'industry': 'e.industry',
                'city': 'e.city',
                'jobs_posted_this_month': 'e.jobs_posted_this_month',
                'subscription_plan': 'e.subscription_plan'
            }
            
            order_by = f"{sort_mapping.get(sort_by, 'e.created_at')} {sort_order.upper()}"
            
            # Pagination
            page = validated_filters.get('page', 1)
            per_page = validated_filters.get('per_page', 20)
            offset = (page - 1) * per_page
            
            # Main query
            query = f"""
                SELECT e.id, e.user_id, u.username, u.email, e.company_name,
                       e.industry, e.company_size, e.city, e.country,
                       e.is_verified, e.subscription_plan, e.jobs_posted_this_month,
                       e.is_active, e.created_at
                FROM employers e
                JOIN users u ON e.user_id = u.id
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            
            params.extend([per_page, offset])
            
            result = db.execute_raw_query(query, params)
            
            if result is None:
                return False, "Error executing query", None
            
            # Serialize data
            employers = employer_list_response_schema.dump(result, many=True)
            
            # Calculate pagination info
            total_pages = (total_count + per_page - 1) // per_page
            
            response_data = {
                'employers': employers,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters_applied': {k: v for k, v in validated_filters.items() if v is not None}
            }
            
            return True, "Employers retrieved successfully", response_data
            
        except Exception as e:
            logger.error(f"Error listing employers: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def verify_employer(employer_id: int, verification_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """
        Verify or unverify an employer (admin only).
        
        Args:
            employer_id (int): Employer ID
            verification_data (Dict): Verification data
            current_user_id (int): ID of admin performing verification
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validate input data
            try:
                validated_data = employer_verification_schema.load(verification_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}"
            
            # Check if employer exists
            existing_employer = db.get_by_id('employers', employer_id)
            if not existing_employer:
                return False, "Employer not found"
            
            # Prepare update data
            update_data = {
                'is_verified': validated_data['is_verified'],
                'notes': validated_data.get('notes'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if validated_data['is_verified']:
                update_data['verification_date'] = datetime.utcnow().isoformat()
                update_data['verified_by'] = current_user_id
            else:
                update_data['verification_date'] = None
                update_data['verified_by'] = None
            
            # Update employer
            success = db.update('employers', update_data, 'id = ?', [employer_id])
            
            if not success:
                return False, "Failed to update verification status"
            
            # Log audit trail
            action = 'VERIFY' if validated_data['is_verified'] else 'UNVERIFY'
            db.log_audit(
                user_id=current_user_id,
                action=action,
                entity_type='employer',
                entity_id=employer_id,
                changes={'verified': validated_data['is_verified'], 'notes': validated_data.get('notes')},
                ip_address=ip_address
            )
            
            status = "verified" if validated_data['is_verified'] else "unverified"
            logger.info(f"Employer {status} successfully: {employer_id}")
            return True, f"Employer {status} successfully"
            
        except Exception as e:
            logger.error(f"Error verifying employer {employer_id}: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def update_subscription(employer_id: int, subscription_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """
        Update employer subscription plan (admin only).
        
        Args:
            employer_id (int): Employer ID
            subscription_data (Dict): Subscription data
            current_user_id (int): ID of admin performing update
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validate input data
            try:
                validated_data = employer_subscription_schema.load(subscription_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}"
            
            # Check if employer exists
            existing_employer = db.get_by_id('employers', employer_id)
            if not existing_employer:
                return False, "Employer not found"
            
            # Prepare update data
            update_data = validated_data.copy()
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Set default job limits based on plan if not provided
            if 'monthly_job_limit' not in update_data:
                plan_limits = {
                    'basic': 5,
                    'premium': 25,
                    'enterprise': 100
                }
                update_data['monthly_job_limit'] = plan_limits.get(validated_data['subscription_plan'], 5)
            
            # Update employer
            success = db.update('employers', update_data, 'id = ?', [employer_id])
            
            if not success:
                return False, "Failed to update subscription"
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='UPDATE_SUBSCRIPTION',
                entity_type='employer',
                entity_id=employer_id,
                changes={'subscription_plan': validated_data['subscription_plan']},
                ip_address=ip_address
            )
            
            logger.info(f"Employer subscription updated successfully: {employer_id}")
            return True, "Subscription updated successfully"
            
        except Exception as e:
            logger.error(f"Error updating subscription for employer {employer_id}: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def get_employer_stats(employer_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get employer statistics.
        
        Args:
            employer_id (int): Employer ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, stats_data)
        """
        try:
            # Check if employer exists
            existing_employer = db.get_by_id('employers', employer_id)
            if not existing_employer:
                return False, "Employer not found", None
            
            # Get job statistics
            job_stats_query = """
                SELECT 
                    COUNT(*) as total_jobs_posted,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_jobs,
                    SUM(application_count) as total_applications
                FROM jobs 
                WHERE company_id IN (
                    SELECT c.id FROM companies c 
                    JOIN employers e ON c.created_by = e.user_id 
                    WHERE e.id = ?
                )
            """
            
            job_stats = db.execute_raw_query(job_stats_query, [employer_id])
            
            # Get reviews statistics
            review_stats_query = """
                SELECT 
                    AVG(rating) as average_rating,
                    COUNT(*) as total_reviews
                FROM employer_reviews 
                WHERE employer_id = ? AND is_approved = 1
            """
            
            review_stats = db.execute_raw_query(review_stats_query, [employer_id])
            
            # Calculate profile completion
            profile_fields = [
                'company_description', 'industry', 'company_size', 'website',
                'phone', 'address', 'city', 'country', 'linkedin_company_url'
            ]
            
            completed_fields = sum(1 for field in profile_fields if existing_employer.get(field))
            profile_completion = (completed_fields / len(profile_fields)) * 100
            
            # Prepare stats data
            stats_data = {
                'total_jobs_posted': job_stats[0]['total_jobs_posted'] if job_stats else 0,
                'active_jobs': job_stats[0]['active_jobs'] if job_stats else 0,
                'total_applications': job_stats[0]['total_applications'] if job_stats else 0,
                'jobs_posted_this_month': existing_employer.get('jobs_posted_this_month', 0),
                'average_rating': round(review_stats[0]['average_rating'], 2) if review_stats and review_stats[0]['average_rating'] else 0,
                'total_reviews': review_stats[0]['total_reviews'] if review_stats else 0,
                'profile_completion': round(profile_completion, 2),
                'last_activity': existing_employer.get('updated_at')
            }
            
            # Serialize with schema
            serialized_stats = employer_stats_schema.dump(stats_data)
            
            return True, "Statistics retrieved successfully", serialized_stats
            
        except Exception as e:
            logger.error(f"Error getting employer stats {employer_id}: {str(e)}")
            return False, "Internal server error", None


# Service instance for easy import
employer_service = EmployerService()