# app/services/employee_service.py

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from marshmallow import ValidationError
import json

from app.utils.db_abstraction import db
from app.utils.password_utils import hash_password
from app.utils.date_utils import safe_isoformat
from app.schemas.employee_schema import (
    employee_registration_schema, employee_update_schema,
    employee_skill_schema, employee_education_schema,
    employee_work_experience_schema, employee_certification_schema,
    employee_response_schema, employee_list_response_schema,
    employee_filter_schema, employee_verification_schema,
    employee_stats_schema
)

# Configure logging
logger = logging.getLogger(__name__)


class EmployeeService:
    """Service class for employee management operations."""
    
    @staticmethod
    def create_employee(data: Dict, current_user_id: int = None, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Create a new employee account.
        
        Args:
            data (Dict): Employee registration data
            current_user_id (int): ID of user creating the employee
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employee_data)
        """
        try:
            # Validate input data
            try:
                validated_data = employee_registration_schema.load(data)
            except ValidationError as e:
                logger.warning(f"Validation error in employee creation: {e.messages}")
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
                'first_name': validated_data['first_name'],
                'last_name': validated_data['last_name'],
                'role': 'employee',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Create user account
            user_id = db.insert('users', user_data)
            if not user_id:
                return False, "Failed to create user account", None
            
            # Prepare employee data
            employee_data = {
                'user_id': user_id,
                'date_of_birth': safe_isoformat(validated_data.get('date_of_birth')),
                'gender': validated_data.get('gender'),
                'phone': validated_data.get('phone'),
                'address': validated_data.get('address'),
                'city': validated_data.get('city'),
                'state': validated_data.get('state'),
                'country': validated_data.get('country'),
                'zip_code': validated_data.get('zip_code'),
                'current_position': validated_data.get('current_position'),
                'current_company': validated_data.get('current_company'),
                'experience_years': validated_data.get('experience_years', 0),
                'linkedin_url': validated_data.get('linkedin_url'),
                'github_url': validated_data.get('github_url'),
                'portfolio_url': validated_data.get('portfolio_url'),
                'preferred_job_type': validated_data.get('preferred_job_type'),
                'preferred_location': validated_data.get('preferred_location'),
                'willing_to_relocate': validated_data.get('willing_to_relocate', False),
                'preferred_salary_min': float(validated_data['preferred_salary_min']) if validated_data.get('preferred_salary_min') else None,
                'preferred_salary_max': float(validated_data['preferred_salary_max']) if validated_data.get('preferred_salary_max') else None,
                'preferred_currency': validated_data.get('preferred_currency', 'USD'),
                'remote_work_preference': validated_data.get('remote_work_preference', 'hybrid'),
                'availability_status': validated_data.get('availability_status', 'available'),
                'available_from': safe_isoformat(validated_data.get('available_from')),
                'notice_period_days': validated_data.get('notice_period_days', 0),
                'summary': validated_data.get('summary'),
                'profile_visibility': 'public',
                'show_contact_info': True,
                'allow_recruiter_contact': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Create employee profile
            employee_id = db.insert('employees', employee_data)
            if not employee_id:
                # Rollback user creation
                db.delete('users', 'id = ?', [user_id])
                return False, "Failed to create employee profile", None
            
            # Calculate and update profile completion
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='CREATE',
                entity_type='employee',
                entity_id=employee_id,
                changes={'created': 'New employee account created'},
                ip_address=ip_address
            )

            # Get complete employee data for response
            employee = EmployeeService.get_employee_by_id(employee_id)
            
            logger.info(f"Employee created successfully: {employee_id}")
            return True, "Employee account created successfully", employee[2]
            
        except Exception as e:
            logger.error(f"Error creating employee: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employee_by_id(employee_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get employee by ID with user information.
        
        Args:
            employee_id (int): Employee ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employee_data)
        """
        try:
            # Get employee with user data using JOIN
            query = """
                SELECT e.*, u.username, u.email, u.first_name, u.last_name, u.role,
                       u.is_active as user_is_active, u.created_at as user_created_at
                FROM employees e
                JOIN users u ON e.user_id = u.id
                WHERE e.id = ?
            """
            
            result = db.execute_raw_query(query, [employee_id])
            
            if not result:
                return False, "Employee not found", None
            
            employee_data = result[0]
            
            # Serialize with schema
            serialized_data = employee_response_schema.dump(employee_data)
            
            return True, "Employee retrieved successfully", serialized_data
            
        except Exception as e:
            logger.error(f"Error getting employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employee_by_user_id(user_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get employee by user ID.
        
        Args:
            user_id (int): User ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employee_data)
        """
        try:
            # Get employee with user data using JOIN
            query = """
                SELECT e.*, u.username, u.email, u.first_name, u.last_name, u.role,
                       u.is_active as user_is_active, u.created_at as user_created_at
                FROM employees e
                JOIN users u ON e.user_id = u.id
                WHERE e.user_id = ?
            """
            
            result = db.execute_raw_query(query, [user_id])
            
            if not result:
                return False, "Employee not found", None
            
            employee_data = result[0]
            
            # Serialize with schema
            serialized_data = employee_response_schema.dump(employee_data)
            
            return True, "Employee retrieved successfully", serialized_data
            
        except Exception as e:
            logger.error(f"Error getting employee by user ID {user_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def update_employee(employee_id: int, data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Update employee profile.
        
        Args:
            employee_id (int): Employee ID
            data (Dict): Update data
            current_user_id (int): ID of user making the update
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, employee_data)
        """
        try:
            # Validate input data
            try:
                validated_data = employee_update_schema.load(data)
            except ValidationError as e:
                logger.warning(f"Validation error in employee update: {e.messages}")
                return False, f"Validation error: {e.messages}", None
            
            # Check if employee exists
            existing_employee = db.get_by_id('employees', employee_id)
            if not existing_employee:
                return False, "Employee not found", None
            
            # Prepare update data with proper date handling
            update_data = {}
            for key, value in validated_data.items():
                if key in ['date_of_birth', 'available_from']:
                    update_data[key] = safe_isoformat(value)
                elif key in ['preferred_salary_min', 'preferred_salary_max'] and value is not None:
                    update_data[key] = float(value)
                else:
                    update_data[key] = value
            
            update_data['updated_at'] = datetime.utcnow().isoformat()
            update_data['last_profile_update'] = datetime.utcnow().isoformat()
            
            # Update employee
            success = db.update('employees', update_data, 'id = ?', [employee_id])
            
            if not success:
                return False, "Failed to update employee", None
            
            # Recalculate profile completion
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='UPDATE',
                entity_type='employee',
                entity_id=employee_id,
                changes={'updated_fields': list(validated_data.keys())},
                ip_address=ip_address
            )
            
            # Get updated employee data
            employee = EmployeeService.get_employee_by_id(employee_id)
            
            logger.info(f"Employee updated successfully: {employee_id}")
            return True, "Employee updated successfully", employee[2]
            
        except Exception as e:
            logger.error(f"Error updating employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def delete_employee(employee_id: int, current_user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """
        Delete employee (soft delete by deactivating).
        
        Args:
            employee_id (int): Employee ID
            current_user_id (int): ID of user making the deletion
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Check if employee exists
            existing_employee = db.get_by_id('employees', employee_id)
            if not existing_employee:
                return False, "Employee not found"
            
            # Soft delete by deactivating
            update_data = {
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            success = db.update('employees', update_data, 'id = ?', [employee_id])
            
            if not success:
                return False, "Failed to deactivate employee"
            
            # Also deactivate the user account
            db.update('users', {'is_active': False}, 'id = ?', [existing_employee['user_id']])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='DELETE',
                entity_type='employee',
                entity_id=employee_id,
                changes={'deactivated': True},
                ip_address=ip_address
            )
            
            logger.info(f"Employee deactivated successfully: {employee_id}")
            return True, "Employee deactivated successfully"
            
        except Exception as e:
            logger.error(f"Error deactivating employee {employee_id}: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def list_employees(filters: Dict = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        List employees with filtering and pagination.
        
        Args:
            filters (Dict): Filter parameters
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, result_data)
        """
        try:
            # Validate filters
            if filters:
                try:
                    validated_filters = employee_filter_schema.load(filters)
                except ValidationError as e:
                    return False, f"Filter validation error: {e.messages}", None
            else:
                validated_filters = employee_filter_schema.load({})
            
            # Build WHERE conditions
            where_conditions = []
            params = []
            
            # Search functionality
            if validated_filters.get('search'):
                search_term = f"%{validated_filters['search']}%"
                where_conditions.append("""
                    (u.first_name LIKE ? OR u.last_name LIKE ? OR 
                     e.current_position LIKE ? OR e.current_company LIKE ? OR 
                     e.city LIKE ? OR u.username LIKE ?)
                """)
                params.extend([search_term] * 6)
            
            # Specific filters
            if validated_filters.get('first_name'):
                where_conditions.append("u.first_name LIKE ?")
                params.append(f"%{validated_filters['first_name']}%")
            
            if validated_filters.get('last_name'):
                where_conditions.append("u.last_name LIKE ?")
                params.append(f"%{validated_filters['last_name']}%")
            
            if validated_filters.get('current_position'):
                where_conditions.append("e.current_position LIKE ?")
                params.append(f"%{validated_filters['current_position']}%")
            
            if validated_filters.get('current_company'):
                where_conditions.append("e.current_company LIKE ?")
                params.append(f"%{validated_filters['current_company']}%")
            
            if validated_filters.get('city'):
                where_conditions.append("e.city = ?")
                params.append(validated_filters['city'])
            
            if validated_filters.get('country'):
                where_conditions.append("e.country = ?")
                params.append(validated_filters['country'])
            
            if validated_filters.get('preferred_job_type'):
                where_conditions.append("e.preferred_job_type = ?")
                params.append(validated_filters['preferred_job_type'])
            
            if validated_filters.get('availability_status'):
                where_conditions.append("e.availability_status = ?")
                params.append(validated_filters['availability_status'])
            
            if validated_filters.get('remote_work_preference'):
                where_conditions.append("e.remote_work_preference = ?")
                params.append(validated_filters['remote_work_preference'])
            
            # Experience range filters
            if validated_filters.get('experience_years_min') is not None:
                where_conditions.append("e.experience_years >= ?")
                params.append(validated_filters['experience_years_min'])
            
            if validated_filters.get('experience_years_max') is not None:
                where_conditions.append("e.experience_years <= ?")
                params.append(validated_filters['experience_years_max'])
            
            # Salary range filters
            if validated_filters.get('salary_min') is not None:
                where_conditions.append("e.preferred_salary_min >= ?")
                params.append(float(validated_filters['salary_min']))
            
            if validated_filters.get('salary_max') is not None:
                where_conditions.append("e.preferred_salary_max <= ?")
                params.append(float(validated_filters['salary_max']))
            
            # Status filters
            if validated_filters.get('is_verified') is not None:
                where_conditions.append("e.is_verified = ?")
                params.append(validated_filters['is_verified'])
            
            if validated_filters.get('is_active') is not None:
                where_conditions.append("e.is_active = ?")
                params.append(validated_filters['is_active'])
            
            if validated_filters.get('profile_visibility'):
                where_conditions.append("e.profile_visibility = ?")
                params.append(validated_filters['profile_visibility'])
            
            # Date range filters
            if validated_filters.get('created_after'):
                where_conditions.append("e.created_at >= ?")
                params.append(validated_filters['created_after'].isoformat())
            
            if validated_filters.get('created_before'):
                where_conditions.append("e.created_at <= ?")
                params.append(validated_filters['created_before'].isoformat())
            
            # Skills filter (if provided)
            if validated_filters.get('skills'):
                skills_conditions = []
                for skill in validated_filters['skills']:
                    skills_conditions.append("EXISTS (SELECT 1 FROM employee_skills es WHERE es.employee_id = e.id AND es.skill_name LIKE ?)")
                    params.append(f"%{skill}%")
                
                if skills_conditions:
                    where_conditions.append("(" + " AND ".join(skills_conditions) + ")")
            
            # Build final WHERE clause
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Count total records
            count_query = f"""
                SELECT COUNT(*) as total
                FROM employees e
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
                'first_name': 'u.first_name',
                'last_name': 'u.last_name',
                'experience_years': 'e.experience_years',
                'current_position': 'e.current_position',
                'city': 'e.city',
                'profile_completion': 'e.profile_completion'
            }
            
            order_by = f"{sort_mapping.get(sort_by, 'e.created_at')} {sort_order.upper()}"
            
            # Pagination
            page = validated_filters.get('page', 1)
            per_page = validated_filters.get('per_page', 20)
            offset = (page - 1) * per_page
            
            # Main query
            query = f"""
                SELECT e.id, e.user_id, u.username, u.first_name, u.last_name, u.email,
                       e.current_position, e.current_company, e.city, e.country,
                       e.experience_years, e.availability_status, e.preferred_job_type,
                       e.is_verified, e.profile_completion, e.created_at
                FROM employees e
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
            employees = employee_list_response_schema.dump(result, many=True)
            
            # Calculate pagination info
            total_pages = (total_count + per_page - 1) // per_page
            
            response_data = {
                'employees': employees,
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
            
            return True, "Employees retrieved successfully", response_data
            
        except Exception as e:
            logger.error(f"Error listing employees: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def verify_employee(employee_id: int, verification_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """
        Verify or unverify an employee (admin only).
        
        Args:
            employee_id (int): Employee ID
            verification_data (Dict): Verification data
            current_user_id (int): ID of admin performing verification
            ip_address (str): IP address for audit logging
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validate input data
            try:
                validated_data = employee_verification_schema.load(verification_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}"
            
            # Check if employee exists
            existing_employee = db.get_by_id('employees', employee_id)
            if not existing_employee:
                return False, "Employee not found"
            
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
            
            # Update employee
            success = db.update('employees', update_data, 'id = ?', [employee_id])
            
            if not success:
                return False, "Failed to update verification status"
            
            # Log audit trail
            action = 'VERIFY' if validated_data['is_verified'] else 'UNVERIFY'
            db.log_audit(
                user_id=current_user_id,
                action=action,
                entity_type='employee',
                entity_id=employee_id,
                changes={'verified': validated_data['is_verified'], 'notes': validated_data.get('notes')},
                ip_address=ip_address
            )
            
            status = "verified" if validated_data['is_verified'] else "unverified"
            logger.info(f"Employee {status} successfully: {employee_id}")
            return True, f"Employee {status} successfully"
            
        except Exception as e:
            logger.error(f"Error verifying employee {employee_id}: {str(e)}")
            return False, "Internal server error"
    
    @staticmethod
    def get_employee_stats(employee_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get employee statistics.
        
        Args:
            employee_id (int): Employee ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, stats_data)
        """
        try:
            # Check if employee exists
            existing_employee = db.get_by_id('employees', employee_id)
            if not existing_employee:
                return False, "Employee not found", None
            
            # Get application statistics (when job applications table is available)
            # For now, using placeholder values
            application_stats = {
                'total_applications': 0,
                'active_applications': 0,
                'interviews_scheduled': 0,
                'offers_received': 0,
                'profile_views': 0
            }
            
            # Get profile-related statistics
            skills_count = len(db.select('employee_skills', condition='employee_id = ?', params=[employee_id]) or [])
            education_count = len(db.select('employee_education', condition='employee_id = ?', params=[employee_id]) or [])
            experience_count = len(db.select('employee_work_experience', condition='employee_id = ?', params=[employee_id]) or [])
            certifications_count = len(db.select('employee_certifications', condition='employee_id = ?', params=[employee_id]) or [])
            
            # Prepare stats data
            stats_data = {
                'total_applications': application_stats['total_applications'],
                'active_applications': application_stats['active_applications'],
                'interviews_scheduled': application_stats['interviews_scheduled'],
                'offers_received': application_stats['offers_received'],
                'profile_views': application_stats['profile_views'],
                'profile_completion': existing_employee.get('profile_completion', 0),
                'skills_count': skills_count,
                'education_count': education_count,
                'experience_count': experience_count,
                'certifications_count': certifications_count,
                'last_activity': existing_employee.get('last_profile_update') or existing_employee.get('updated_at')
            }
            
            # Serialize with schema
            serialized_stats = employee_stats_schema.dump(stats_data)
            
            return True, "Statistics retrieved successfully", serialized_stats
            
        except Exception as e:
            logger.error(f"Error getting employee stats {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def _calculate_profile_completion(employee_id: int) -> float:
        """
        Calculate profile completion percentage.
        
        Args:
            employee_id (int): Employee ID
            
        Returns:
            float: Profile completion percentage
        """
        try:
            employee = db.get_by_id('employees', employee_id)
            if not employee:
                return 0.0
            
            # Define profile fields and their weights
            profile_fields = {
                'date_of_birth': 5,
                'phone': 5,
                'address': 5,
                'city': 5,
                'current_position': 10,
                'current_company': 5,
                'summary': 15,
                'linkedin_url': 5,
                'preferred_job_type': 5,
                'availability_status': 5
            }
            
            # Calculate basic profile completion
            total_weight = sum(profile_fields.values())
            completed_weight = 0
            
            for field, weight in profile_fields.items():
                if employee.get(field):
                    completed_weight += weight
            
            # Add weight for related data
            skills_count = len(db.select('employee_skills', condition='employee_id = ?', params=[employee_id]) or [])
            if skills_count > 0:
                completed_weight += 15  # Skills weight
                
            education_count = len(db.select('employee_education', condition='employee_id = ?', params=[employee_id]) or [])
            if education_count > 0:
                completed_weight += 10  # Education weight
                
            experience_count = len(db.select('employee_work_experience', condition='employee_id = ?', params=[employee_id]) or [])
            if experience_count > 0:
                completed_weight += 15  # Experience weight
            
            # Total possible weight including related data
            total_possible_weight = total_weight + 15 + 10 + 15  # Basic + Skills + Education + Experience
            
            # Calculate percentage
            completion_percentage = (completed_weight / total_possible_weight) * 100
            return round(completion_percentage, 2)
            
        except Exception as e:
            logger.error(f"Error calculating profile completion for employee {employee_id}: {str(e)}")
            return 0.0
    
    # Skill Management Methods
    @staticmethod
    def add_skill(employee_id: int, skill_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Add a skill to employee profile."""
        try:
            # Validate input data
            try:
                validated_data = employee_skill_schema.load(skill_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}", None
            
            # Check if employee exists
            if not db.get_by_id('employees', employee_id):
                return False, "Employee not found", None
            
            # Check if skill already exists for this employee
            if db.record_exists('employee_skills', 'employee_id = ? AND skill_name = ?', 
                              [employee_id, validated_data['skill_name']]):
                return False, "Skill already exists for this employee", None
            
            # Prepare skill data
            skill_insert_data = validated_data.copy()
            skill_insert_data['employee_id'] = employee_id
            skill_insert_data['created_at'] = datetime.utcnow().isoformat()
            
            # Insert skill
            skill_id = db.insert('employee_skills', skill_insert_data)
            if not skill_id:
                return False, "Failed to add skill", None
            
            # Update profile completion
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='CREATE',
                entity_type='employee_skill',
                entity_id=skill_id,
                changes={'skill_added': validated_data['skill_name']},
                ip_address=ip_address
            )
            
            # Get the created skill
            skill = db.get_by_id('employee_skills', skill_id)
            
            return True, "Skill added successfully", skill
            
        except Exception as e:
            logger.error(f"Error adding skill for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employee_skills(employee_id: int) -> Tuple[bool, str, Optional[List[Dict]]]:
        """Get all skills for an employee."""
        try:
            skills = db.select('employee_skills', condition='employee_id = ?', params=[employee_id])
            return True, "Skills retrieved successfully", skills or []
        except Exception as e:
            logger.error(f"Error getting skills for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def update_skill(skill_id: int, skill_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Update a skill."""
        try:
            # Validate input data
            try:
                validated_data = employee_skill_schema.load(skill_data, partial=True)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}", None
            
            # Check if skill exists
            existing_skill = db.get_by_id('employee_skills', skill_id)
            if not existing_skill:
                return False, "Skill not found", None
            
            # Update skill
            success = db.update('employee_skills', validated_data, 'id = ?', [skill_id])
            if not success:
                return False, "Failed to update skill", None
            
            # Update profile completion
            employee_id = existing_skill['employee_id']
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='UPDATE',
                entity_type='employee_skill',
                entity_id=skill_id,
                changes={'updated_fields': list(validated_data.keys())},
                ip_address=ip_address
            )
            
            # Get updated skill
            skill = db.get_by_id('employee_skills', skill_id)
            
            return True, "Skill updated successfully", skill
            
        except Exception as e:
            logger.error(f"Error updating skill {skill_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def delete_skill(skill_id: int, current_user_id: int, ip_address: str = None) -> Tuple[bool, str]:
        """Delete a skill."""
        try:
            # Get skill to find employee_id for profile completion update
            existing_skill = db.get_by_id('employee_skills', skill_id)
            if not existing_skill:
                return False, "Skill not found"
            
            # Delete skill
            success = db.delete('employee_skills', 'id = ?', [skill_id])
            if not success:
                return False, "Failed to delete skill"
            
            # Update profile completion
            employee_id = existing_skill['employee_id']
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='DELETE',
                entity_type='employee_skill',
                entity_id=skill_id,
                changes={'skill_deleted': existing_skill['skill_name']},
                ip_address=ip_address
            )
            
            return True, "Skill deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting skill {skill_id}: {str(e)}")
            return False, "Internal server error"
    
    # Education Management Methods
    @staticmethod
    def add_education(employee_id: int, education_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Add education to employee profile."""
        try:
            # Validate input data
            try:
                validated_data = employee_education_schema.load(education_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}", None
            
            # Check if employee exists
            if not db.get_by_id('employees', employee_id):
                return False, "Employee not found", None
            
            # Prepare education data
            education_insert_data = validated_data.copy()
            education_insert_data['employee_id'] = employee_id
            education_insert_data['created_at'] = datetime.utcnow().isoformat()
            
            # Convert dates to ISO format using safe utility
            education_insert_data['start_date'] = safe_isoformat(education_insert_data.get('start_date'))
            education_insert_data['end_date'] = safe_isoformat(education_insert_data.get('end_date'))
            
            # Convert GPA to float
            if 'gpa' in education_insert_data and education_insert_data['gpa']:
                education_insert_data['gpa'] = float(education_insert_data['gpa'])
            
            # Insert education
            education_id = db.insert('employee_education', education_insert_data)
            if not education_id:
                return False, "Failed to add education", None
            
            # Update profile completion
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='CREATE',
                entity_type='employee_education',
                entity_id=education_id,
                changes={'education_added': validated_data['institution_name']},
                ip_address=ip_address
            )
            
            # Get the created education
            education = db.get_by_id('employee_education', education_id)
            
            return True, "Education added successfully", education
            
        except Exception as e:
            logger.error(f"Error adding education for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employee_education(employee_id: int) -> Tuple[bool, str, Optional[List[Dict]]]:
        """Get all education for an employee."""
        try:
            education = db.select('employee_education', condition='employee_id = ?', params=[employee_id], order_by='start_date DESC')
            return True, "Education retrieved successfully", education or []
        except Exception as e:
            logger.error(f"Error getting education for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    # Work Experience Management Methods
    @staticmethod
    def add_work_experience(employee_id: int, experience_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Add work experience to employee profile."""
        try:
            # Validate input data
            try:
                validated_data = employee_work_experience_schema.load(experience_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}", None
            
            # Check if employee exists
            if not db.get_by_id('employees', employee_id):
                return False, "Employee not found", None
            
            # Prepare experience data
            experience_insert_data = validated_data.copy()
            experience_insert_data['employee_id'] = employee_id
            experience_insert_data['created_at'] = datetime.utcnow().isoformat()
            
            # Convert dates to ISO format using safe utility
            experience_insert_data['start_date'] = safe_isoformat(experience_insert_data.get('start_date'))
            experience_insert_data['end_date'] = safe_isoformat(experience_insert_data.get('end_date'))
            
            # Insert work experience
            experience_id = db.insert('employee_work_experience', experience_insert_data)
            if not experience_id:
                return False, "Failed to add work experience", None
            
            # Update profile completion
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='CREATE',
                entity_type='employee_work_experience',
                entity_id=experience_id,
                changes={'experience_added': f"{validated_data['position_title']} at {validated_data['company_name']}"},
                ip_address=ip_address
            )
            
            # Get the created experience
            experience = db.get_by_id('employee_work_experience', experience_id)
            
            return True, "Work experience added successfully", experience
            
        except Exception as e:
            logger.error(f"Error adding work experience for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employee_work_experience(employee_id: int) -> Tuple[bool, str, Optional[List[Dict]]]:
        """Get all work experience for an employee."""
        try:
            experience = db.select('employee_work_experience', condition='employee_id = ?', params=[employee_id], order_by='start_date DESC')
            return True, "Work experience retrieved successfully", experience or []
        except Exception as e:
            logger.error(f"Error getting work experience for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    # Certification Management Methods
    @staticmethod
    def add_certification(employee_id: int, certification_data: Dict, current_user_id: int, ip_address: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Add certification to employee profile."""
        try:
            # Validate input data
            try:
                validated_data = employee_certification_schema.load(certification_data)
            except ValidationError as e:
                return False, f"Validation error: {e.messages}", None
            
            # Check if employee exists
            if not db.get_by_id('employees', employee_id):
                return False, "Employee not found", None
            
            # Prepare certification data
            certification_insert_data = validated_data.copy()
            certification_insert_data['employee_id'] = employee_id
            certification_insert_data['created_at'] = datetime.utcnow().isoformat()
            
            # Convert dates to ISO format using safe utility
            certification_insert_data['issue_date'] = safe_isoformat(certification_insert_data.get('issue_date'))
            certification_insert_data['expiry_date'] = safe_isoformat(certification_insert_data.get('expiry_date'))
            
            # Insert certification
            certification_id = db.insert('employee_certifications', certification_insert_data)
            if not certification_id:
                return False, "Failed to add certification", None
            
            # Update profile completion
            completion_percentage = EmployeeService._calculate_profile_completion(employee_id)
            db.update('employees', {'profile_completion': completion_percentage}, 'id = ?', [employee_id])
            
            # Log audit trail
            db.log_audit(
                user_id=current_user_id,
                action='CREATE',
                entity_type='employee_certification',
                entity_id=certification_id,
                changes={'certification_added': validated_data['certification_name']},
                ip_address=ip_address
            )
            
            # Get the created certification
            certification = db.get_by_id('employee_certifications', certification_id)
            
            return True, "Certification added successfully", certification
            
        except Exception as e:
            logger.error(f"Error adding certification for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    def get_employee_certifications(employee_id: int) -> Tuple[bool, str, Optional[List[Dict]]]:
        """Get all certifications for an employee."""
        try:
            certifications = db.select('employee_certifications', condition='employee_id = ?', params=[employee_id], order_by='issue_date DESC')
            return True, "Certifications retrieved successfully", certifications or []
        except Exception as e:
            logger.error(f"Error getting certifications for employee {employee_id}: {str(e)}")
            return False, "Internal server error", None


# Service instance for easy import
employee_service = EmployeeService()