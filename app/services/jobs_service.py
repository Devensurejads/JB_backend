# app/services/jobs_service.py

import logging
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import math
from marshmallow import ValidationError



# Database imports with fallback
try:
    from app.utils.db_abstraction import db as raw_db
    
    # Test if the database has required methods
    required_methods = ['insert', 'select', 'update', 'delete', 'get_by_id']
    missing_methods = [method for method in required_methods if not hasattr(raw_db, method)]
    
    if missing_methods:
        logger.warning(f"Database missing methods: {missing_methods}. Using fallback database.")
        from app.utils.fallback_db import get_fallback_db
        db = get_fallback_db()
    else:
        # Use compatibility wrapper for existing database
        try:
            from app.utils.db_compatibility import get_compatible_db
            db = get_compatible_db()
        except ImportError:
            db = raw_db
            
except ImportError:
    logger.warning("Could not import db_abstraction. Using fallback database.")
    from app.utils.fallback_db import get_fallback_db
    db = get_fallback_db()
from app.schemas.jobs_schema import (
    job_update_schema, job_filter_schema,
    job_response_schema, job_list_response_schema, job_stats_schema,
    job_bookmark_schema, job_template_schema, job_category_schema,
    job_skill_schema, job_question_schema
)

# Import the fixed schema for job creation
try:
    from app.schemas.jobs_schema_fixed import job_create_schema_fixed as job_create_schema
except ImportError:
    # Fallback to original if fixed version not available
    from app.schemas.jobs_schema import job_create_schema

logger = logging.getLogger(__name__)


class JobsService:
    """Service class for job management operations."""
    
    @staticmethod
    def create_job(employer_id: int, job_data: Dict, user_id: int, ip_address: str = None) -> Dict:
        """
        Create a new job posting.
        
        Args:
            employer_id: ID of the employer creating the job
            job_data: Job data to create
            user_id: ID of the user creating the job
            ip_address: IP address for audit logging
            
        Returns:
            Dict containing the created job data
            
        Raises:
            ValueError: If validation fails or employer doesn't exist
        """
        try:
            # Validate input data
            validated_data = job_create_schema.load(job_data)
            
            # Verify employer exists and is active
            employer = db.get_by_id('employers', employer_id)
            if not employer or not employer.get('is_active'):
                raise ValueError('Invalid or inactive employer')
            
            # Verify employer can post jobs
            if not employer.get('can_post_jobs', True):
                raise ValueError('Employer is not authorized to post jobs')
            
            # Check job posting limits
            current_month = datetime.now().strftime('%Y-%m')
            monthly_limit = employer.get('monthly_job_limit', 5)
            jobs_this_month = employer.get('jobs_posted_this_month', 0)
            
            if jobs_this_month >= monthly_limit:
                raise ValueError(f'Monthly job posting limit ({monthly_limit}) exceeded')
            
            # Prepare job data for insertion
            now = datetime.now().isoformat()
            validated_data.update({
                'employer_id': employer_id,
                'created_at': now,
                'updated_at': now,
                'is_active': True,
                'applications_count': 0,
                'views_count': 0,
                'bookmarks_count': 0
            })
            
            # Set posted_at if status is active
            if validated_data.get('status') == 'active':
                validated_data['posted_at'] = now
            
            # Convert Decimal fields to float for SQLite compatibility
            decimal_fields = ['salary_min', 'salary_max', 'preferred_salary_min', 'preferred_salary_max']
            for field in decimal_fields:
                if field in validated_data and validated_data[field] is not None:
                    validated_data[field] = float(validated_data[field])
            
            # Convert list fields to JSON
            list_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
            for field in list_fields:
                if field in validated_data and validated_data[field]:
                    validated_data[field] = json.dumps(validated_data[field])
            
            # Extract skills and questions data before insertion
            skills_data = validated_data.pop('skills', [])
            questions_data = validated_data.pop('questions', [])
            
            # Insert job record
            job_id = db.insert('jobs', validated_data)
            
            if not job_id:
                raise ValueError('Failed to create job - no ID returned')
            
            # Insert job skills if provided
            if skills_data:
                for skill in skills_data:
                    skill['job_id'] = job_id
                    skill['created_at'] = now
                    # Convert decimal fields in skills
                    if 'years_experience' in skill and skill['years_experience'] is not None:
                        skill['years_experience'] = int(skill['years_experience'])
                    try:
                        db.insert('job_skills', skill)
                    except Exception as e:
                        logger.error(f"Error inserting skill {skill}: {str(e)}")
                        # Continue with other skills rather than failing completely
            
            # Insert job questions if provided
            if questions_data:
                for question in questions_data:
                    question['job_id'] = job_id
                    question['created_at'] = now
                    if question.get('options'):
                        question['options'] = json.dumps(question['options'])
                    # Convert numeric fields
                    if 'order_index' in question and question['order_index'] is not None:
                        question['order_index'] = int(question['order_index'])
                    if 'max_length' in question and question['max_length'] is not None:
                        question['max_length'] = int(question['max_length'])
                    try:
                        db.insert('job_questions', question)
                    except Exception as e:
                        logger.error(f"Error inserting question {question}: {str(e)}")
                        # Continue with other questions rather than failing completely
            
            # Update employer's monthly job count
            db.update('employers', 
                     {'jobs_posted_this_month': jobs_this_month + 1},
                     'id = ?', [employer_id])
            
            # Log the creation
            db.log_audit(user_id, 'CREATE', 'job', job_id, 
                        json.dumps({'action': 'job_created', 'job_id': job_id}), 
                        ip_address)
            
            # Retrieve and return the created job
            return JobsService.get_job_by_id(job_id)
            
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            raise
    
    @staticmethod
    def get_job_by_id(job_id: int, include_inactive: bool = False) -> Optional[Dict]:
        """
        Get a job by its ID with related data.
        
        Args:
            job_id: ID of the job to retrieve
            include_inactive: Whether to include inactive jobs
            
        Returns:
            Dict containing job data or None if not found
        """
        try:
            # First, get the basic job record
            job = db.get_by_id('jobs', job_id)
            
            if not job:
                return None
            
            # Convert to dict if it's not already
            if hasattr(job, '_asdict'):
                job_dict = job._asdict()
            elif hasattr(job, 'keys'):
                job_dict = dict(job)
            else:
                job_dict = job
            
            # Check if job is active (if required)
            if not include_inactive and not job_dict.get('is_active', True):
                return None
            
            # Get employer information
            try:
                employer = db.get_by_id('employers', job_dict['employer_id'])
                if employer:
                    if hasattr(employer, '_asdict'):
                        employer_dict = employer._asdict()
                    elif hasattr(employer, 'keys'):
                        employer_dict = dict(employer)
                    else:
                        employer_dict = employer
                    
                    job_dict['employer_company_name'] = employer_dict.get('company_name')
                    job_dict['employer_logo_url'] = employer_dict.get('logo_url')
                    job_dict['employer_is_verified'] = employer_dict.get('is_verified')
            except Exception as e:
                logger.warning(f"Could not fetch employer data: {str(e)}")
                job_dict['employer_company_name'] = None
                job_dict['employer_logo_url'] = None
                job_dict['employer_is_verified'] = None
            
            # Get category information
            try:
                if job_dict.get('category_id'):
                    category = db.get_by_id('job_categories', job_dict['category_id'])
                    if category:
                        if hasattr(category, '_asdict'):
                            category_dict = category._asdict()
                        elif hasattr(category, 'keys'):
                            category_dict = dict(category)
                        else:
                            category_dict = category
                        
                        job_dict['category_name'] = category_dict.get('name')
                    else:
                        job_dict['category_name'] = None
                else:
                    job_dict['category_name'] = None
            except Exception as e:
                logger.warning(f"Could not fetch category data: {str(e)}")
                job_dict['category_name'] = None
            
            # Parse JSON fields
            json_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
            for field in json_fields:
                if job_dict.get(field):
                    try:
                        job_dict[field] = json.loads(job_dict[field])
                    except (json.JSONDecodeError, TypeError):
                        job_dict[field] = []
                else:
                    job_dict[field] = []
            
            # Get job skills
            try:
                skills = db.select('job_skills', '*', 'job_id = ?', [job_id])
                skills_list = []
                if skills:
                    for skill in skills:
                        if hasattr(skill, '_asdict'):
                            skill_dict = skill._asdict()
                        elif hasattr(skill, 'keys'):
                            skill_dict = dict(skill)
                        else:
                            skill_dict = skill
                        skills_list.append(skill_dict)
                job_dict['skills'] = skills_list
            except Exception as e:
                logger.warning(f"Could not fetch skills data: {str(e)}")
                job_dict['skills'] = []
            
            # Get job questions
            try:
                questions = db.select('job_questions', '*', 'job_id = ? ORDER BY order_index', [job_id])
                questions_list = []
                if questions:
                    for question in questions:
                        if hasattr(question, '_asdict'):
                            question_dict = question._asdict()
                        elif hasattr(question, 'keys'):
                            question_dict = dict(question)
                        else:
                            question_dict = question
                        
                        if question_dict.get('options'):
                            try:
                                question_dict['options'] = json.loads(question_dict['options'])
                            except (json.JSONDecodeError, TypeError):
                                question_dict['options'] = []
                        questions_list.append(question_dict)
                job_dict['questions'] = questions_list
            except Exception as e:
                logger.warning(f"Could not fetch questions data: {str(e)}")
                job_dict['questions'] = []
            
            return job_response_schema.dump(job_dict)
            
        except Exception as e:
            logger.error(f"Error retrieving job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def update_job(job_id: int, job_data: Dict, user_id: int, employer_id: int = None, ip_address: str = None) -> Dict:
        """
        Update an existing job.
        
        Args:
            job_id: ID of the job to update
            job_data: Data to update
            user_id: ID of the user updating the job
            employer_id: ID of the employer (for authorization)
            ip_address: IP address for audit logging
            
        Returns:
            Dict containing updated job data
            
        Raises:
            ValueError: If job not found or user not authorized
        """
        try:
            # Validate input data
            validated_data = job_update_schema.load(job_data)
            
            # Get existing job
            existing_job = JobsService.get_job_by_id(job_id, include_inactive=True)
            if not existing_job:
                raise ValueError('Job not found')
            
            # Check authorization (employers can only update their own jobs)
            if employer_id and existing_job['employer_id'] != employer_id:
                raise ValueError('Not authorized to update this job')
            
            # Prepare update data
            now = datetime.now().isoformat()
            validated_data['updated_at'] = now
            validated_data['last_updated_at'] = now
            
            # Set posted_at if status is being changed to active
            if (validated_data.get('status') == 'active' and 
                existing_job.get('status') != 'active'):
                validated_data['posted_at'] = now
            
            # Convert list fields to JSON
            list_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
            for field in list_fields:
                if field in validated_data and validated_data[field] is not None:
                    validated_data[field] = json.dumps(validated_data[field])
            
            # Extract skills and questions data
            skills_data = validated_data.pop('skills', None)
            questions_data = validated_data.pop('questions', None)
            
            # Update job record
            if validated_data:  # Only update if there's data to update
                db.update('jobs', validated_data, 'id = ?', [job_id])
            
            # Update job skills if provided
            if skills_data is not None:
                # Delete existing skills
                db.delete('job_skills', 'job_id = ?', [job_id])
                
                # Insert new skills
                for skill in skills_data:
                    skill['job_id'] = job_id
                    skill['created_at'] = now
                    db.insert('job_skills', skill)
            
            # Update job questions if provided
            if questions_data is not None:
                # Delete existing questions
                db.delete('job_questions', 'job_id = ?', [job_id])
                
                # Insert new questions
                for question in questions_data:
                    question['job_id'] = job_id
                    question['created_at'] = now
                    if question.get('options'):
                        question['options'] = json.dumps(question['options'])
                    db.insert('job_questions', question)
            
            # Log the update
            db.log_audit(user_id, 'UPDATE', 'job', job_id,
                        json.dumps({'action': 'job_updated', 'changes': job_data}),
                        ip_address)
            
            # Return updated job
            return JobsService.get_job_by_id(job_id)
            
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def delete_job(job_id: int, user_id: int, employer_id: int = None, hard_delete: bool = False, ip_address: str = None) -> bool:
        """
        Delete a job (soft delete by default).
        
        Args:
            job_id: ID of the job to delete
            user_id: ID of the user deleting the job
            employer_id: ID of the employer (for authorization)
            hard_delete: Whether to perform hard delete
            ip_address: IP address for audit logging
            
        Returns:
            bool indicating success
            
        Raises:
            ValueError: If job not found or user not authorized
        """
        try:
            # Get existing job
            existing_job = JobsService.get_job_by_id(job_id, include_inactive=True)
            if not existing_job:
                raise ValueError('Job not found')
            
            # Check authorization
            if employer_id and existing_job['employer_id'] != employer_id:
                raise ValueError('Not authorized to delete this job')
            
            if hard_delete:
                # Hard delete - remove completely
                db.delete('jobs', 'id = ?', [job_id])
                action = 'HARD_DELETE'
            else:
                # Soft delete - mark as inactive
                now = datetime.now().isoformat()
                db.update('jobs', 
                         {'is_active': False, 'updated_at': now, 'status': 'closed'}, 
                         'id = ?', [job_id])
                action = 'SOFT_DELETE'
            
            # Log the deletion
            db.log_audit(user_id, action, 'job', job_id,
                        json.dumps({'action': 'job_deleted', 'hard_delete': hard_delete}),
                        ip_address)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_jobs_list(filters: Dict = None, employer_id: int = None) -> Tuple[List[Dict], int]:
        """
        Get a paginated list of jobs with filtering (simplified version).
        
        Args:
            filters: Filter parameters
            employer_id: ID of employer (to filter by employer)
            
        Returns:
            Tuple of (job_list, total_count)
        """
        try:
            # Validate filters
            if filters:
                filters = job_filter_schema.load(filters)
            else:
                filters = job_filter_schema.load({})
            
            # Build basic conditions and parameters
            conditions = ['is_active = 1']
            params = []
            
            # Employer filter
            if employer_id:
                conditions.append('employer_id = ?')
                params.append(employer_id)
            
            # Status filter - default to active
            status_filter = filters.get('status', ['active'])
            if status_filter:
                if isinstance(status_filter, list):
                    placeholders = ','.join(['?' for _ in status_filter])
                    conditions.append(f'status IN ({placeholders})')
                    params.extend(status_filter)
                else:
                    conditions.append('status = ?')
                    params.append(status_filter)
            
            # Basic search filter
            if filters.get('search'):
                conditions.append('(title LIKE ? OR description LIKE ?)')
                search_term = f"%{filters['search']}%"
                params.extend([search_term, search_term])
            
            # Title filter
            if filters.get('title'):
                conditions.append('title LIKE ?')
                params.append(f"%{filters['title']}%")
            
            # Employment type filter
            if filters.get('employment_type'):
                emp_types = filters['employment_type']
                if isinstance(emp_types, list):
                    placeholders = ','.join(['?' for _ in emp_types])
                    conditions.append(f'employment_type IN ({placeholders})')
                    params.extend(emp_types)
                else:
                    conditions.append('employment_type = ?')
                    params.append(emp_types)
            
            # Location filters
            if filters.get('city'):
                conditions.append('city LIKE ?')
                params.append(f"%{filters['city']}%")
            
            if filters.get('country'):
                conditions.append('country LIKE ?')
                params.append(f"%{filters['country']}%")
            
            # Remote filter
            if filters.get('is_remote') is not None:
                conditions.append('is_remote = ?')
                params.append(1 if filters['is_remote'] else 0)
            
            # Salary filters
            if filters.get('salary_min'):
                conditions.append('(salary_max IS NULL OR salary_max >= ?)')
                params.append(float(filters['salary_min']))
            
            if filters.get('salary_max'):
                conditions.append('(salary_min IS NULL OR salary_min <= ?)')
                params.append(float(filters['salary_max']))
            
            # Build WHERE clause
            where_clause = ' AND '.join(conditions)
            
            # Get total count with simplified query
            count_query = f"SELECT COUNT(*) FROM jobs WHERE {where_clause}"
            try:
                count_result = db.execute_query(count_query, params, fetch_one=True)
                if isinstance(count_result, dict):
                    total_count = count_result.get('COUNT(*)', 0) or list(count_result.values())[0]
                else:
                    total_count = count_result[0] if count_result else 0
            except Exception as e:
                logger.error(f"Count query failed: {str(e)}")
                total_count = 0
            
            # Get jobs with basic query (no JOINs initially)
            page = filters.get('page', 1)
            per_page = filters.get('per_page', 20)
            offset = (page - 1) * per_page
            
            # Add sorting
            sort_by = filters.get('sort_by', 'created_at')
            sort_order = filters.get('sort_order', 'desc')
            
            # Map sort fields to actual column names
            sort_mapping = {
                'created_at': 'created_at',
                'posted_at': 'posted_at',
                'title': 'title',
                'salary_min': 'salary_min',
                'salary_max': 'salary_max'
            }
            
            sort_column = sort_mapping.get(sort_by, 'created_at')
            jobs_query = f"""
                SELECT * FROM jobs 
                WHERE {where_clause} 
                ORDER BY {sort_column} {sort_order.upper()} 
                LIMIT {per_page} OFFSET {offset}
            """
            
            jobs = db.execute_query(jobs_query, params)
            
            # Process jobs and add employer/category info individually
            jobs_list = []
            for job in jobs:
                if hasattr(job, '_asdict'):
                    job_dict = job._asdict()
                elif hasattr(job, 'keys'):
                    job_dict = dict(job)
                else:
                    job_dict = job
                
                # Add employer info
                try:
                    employer = db.get_by_id('employers', job_dict['employer_id'])
                    if employer:
                        if hasattr(employer, '_asdict'):
                            employer_dict = employer._asdict()
                        elif hasattr(employer, 'keys'):
                            employer_dict = dict(employer)
                        else:
                            employer_dict = employer
                        
                        job_dict['employer_company_name'] = employer_dict.get('company_name')
                        job_dict['employer_logo_url'] = employer_dict.get('logo_url')
                        job_dict['employer_is_verified'] = employer_dict.get('is_verified')
                except Exception as e:
                    logger.warning(f"Could not fetch employer for job {job_dict.get('id')}: {str(e)}")
                    job_dict['employer_company_name'] = None
                    job_dict['employer_logo_url'] = None
                    job_dict['employer_is_verified'] = None
                
                # Add category info
                try:
                    if job_dict.get('category_id'):
                        category = db.get_by_id('job_categories', job_dict['category_id'])
                        if category:
                            if hasattr(category, '_asdict'):
                                category_dict = category._asdict()
                            elif hasattr(category, 'keys'):
                                category_dict = dict(category)
                            else:
                                category_dict = category
                            
                            job_dict['category_name'] = category_dict.get('name')
                        else:
                            job_dict['category_name'] = None
                    else:
                        job_dict['category_name'] = None
                except Exception as e:
                    logger.warning(f"Could not fetch category for job {job_dict.get('id')}: {str(e)}")
                    job_dict['category_name'] = None
                
                # Parse JSON fields
                json_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
                for field in json_fields:
                    if job_dict.get(field):
                        try:
                            job_dict[field] = json.loads(job_dict[field])
                        except (json.JSONDecodeError, TypeError):
                            job_dict[field] = []
                    else:
                        job_dict[field] = []
                
                jobs_list.append(job_list_response_schema.dump(job_dict))
            
            return jobs_list, total_count
            
        except Exception as e:
            logger.error(f"Error retrieving jobs list: {str(e)}")
            # Return empty results instead of raising exception
            return [], 0
            sort_by = filters.get('sort_by', 'posted_at')
            sort_order = filters.get('sort_order', 'desc')
            
            # Map sort fields to actual column names
            sort_mapping = {
                'created_at': 'j.created_at',
                'posted_at': 'j.posted_at',
                'title': 'j.title',
                'salary_min': 'j.salary_min',
                'salary_max': 'j.salary_max',
                'application_deadline': 'j.application_deadline',
                'views_count': 'j.views_count',
                'applications_count': 'j.applications_count',
                'expires_at': 'j.expires_at'
            }
            
            sort_column = sort_mapping.get(sort_by, 'j.posted_at')
            query += f" ORDER BY {sort_column} {sort_order.upper()}"
            
            # Add pagination
            page = filters.get('page', 1)
            per_page = filters.get('per_page', 20)
            offset = (page - 1) * per_page
            
            query += f" LIMIT {per_page} OFFSET {offset}"
            
            # Execute query
            jobs = db.execute_query(query, params)
            
            # Convert to list of dictionaries and process
            jobs_list = []
            for job in jobs:
                job_dict = dict(job)
                
                # Parse JSON fields for list view (simplified)
                json_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
                for field in json_fields:
                    if job_dict.get(field):
                        try:
                            job_dict[field] = json.loads(job_dict[field])
                        except (json.JSONDecodeError, TypeError):
                            job_dict[field] = []
                    else:
                        job_dict[field] = []
                
                jobs_list.append(job_list_response_schema.dump(job_dict))
            
            return jobs_list, total_count
            
        except Exception as e:
            logger.error(f"Error retrieving jobs list: {str(e)}")
            raise
    
    
    @staticmethod
    def get_jobs_list_filter(filters: Dict = None, employer_id: int = None) -> Tuple[List[Dict], int]:
        """
        Get a paginated list of jobs with filtering (simplified version).
        
        Args:
            filters: Filter parameters
            employer_id: ID of employer (to filter by employer)
            
        Returns:
            Tuple of (job_list, total_count)
        """
        try:
            # Validate filters, but handle salary fields and pincode separately if not in schema
            if filters:
                try:
                    filters = job_filter_schema.load(filters)
                except ValidationError as e:
                    # If salary fields or pincode are causing validation errors, extract them separately
                    special_filters = {}
                    clean_filters = filters.copy()
                    
                    # Extract fields that might not be in schema
                    for field in ['min_salary', 'max_salary', 'pincode']:
                        if field in clean_filters:
                            try:
                                if field in ['min_salary', 'max_salary']:
                                    special_filters[field] = float(clean_filters.pop(field))
                                else:  # pincode
                                    special_filters[field] = int(clean_filters.pop(field))
                            except (ValueError, TypeError):
                                pass
                    
                    # Validate remaining filters
                    filters = job_filter_schema.load(clean_filters)
                    # Add back special filters
                    filters.update(special_filters)
            else:
                filters = job_filter_schema.load({})
            
            # Handle pincode-based location filtering
            location_filter_jobs = None
            if filters.get('pincode'):
                user_pincode = filters['pincode']
                logger.info(f"Applying pincode filter for: {user_pincode}")
                
                # First, get the coordinates for the user's pincode
                user_coords = JobsService.get_coordinates_for_pincode(user_pincode)
                
                if user_coords:
                    user_lat, user_lng = user_coords
                    logger.info(f"User coordinates: {user_lat}, {user_lng}")
                    
                    # Get all jobs with coordinates to calculate distances
                    all_jobs_query = """
                        SELECT id, latitude, longitude, pincode 
                        FROM jobs 
                        WHERE latitude IS NOT NULL 
                        AND longitude IS NOT NULL 
                        AND is_active = 1
                    """
                    all_jobs = db.execute_query(all_jobs_query)
                    
                    # Filter jobs within 15km radius
                    nearby_job_ids = []
                    for job in all_jobs:
                        if job.get('latitude') and job.get('longitude'):
                            distance = JobsService.calculate_distance(
                                user_lat, user_lng, 
                                float(job['latitude']), float(job['longitude'])
                            )
                            logger.debug(f"Job ID {job['id']} at pincode {job.get('pincode')}: distance = {distance:.2f}km")
                            
                            if distance <= 15.0:  # Within 15km radius
                                nearby_job_ids.append(job['id'])
                    
                    location_filter_jobs = nearby_job_ids
                    logger.info(f"Found {len(nearby_job_ids)} jobs within 15km of pincode {user_pincode}")
                else:
                    logger.warning(f"Could not find coordinates for pincode: {user_pincode}")
                    # Return empty result if pincode is invalid
                    location_filter_jobs = []
            
            # Build basic conditions and parameters
            conditions = ['is_active = 1']
            params = []
            
            # Apply location filter if we have nearby jobs from pincode search
            if location_filter_jobs is not None:
                if not location_filter_jobs:
                    # No jobs found within radius, return empty result
                    return [], 0
                else:
                    # Add condition to only include nearby jobs
                    placeholders = ','.join(['?' for _ in location_filter_jobs])
                    conditions.append(f'id IN ({placeholders})')
                    params.extend(location_filter_jobs)
            
            # Employer filter
            if employer_id:
                conditions.append('employer_id = ?')
                params.append(employer_id)
            
            # Category filter
            if filters.get('category_id'):
                conditions.append('category_id = ?')
                params.append(filters['category_id'])
            
            # Employment type filter (supports multiple values)
            if filters.get('employment_type'):
                employment_types = filters['employment_type']
                if isinstance(employment_types, list) and employment_types:
                    placeholders = ','.join(['?' for _ in employment_types])
                    conditions.append(f'employment_type IN ({placeholders})')
                    params.extend(employment_types)
                elif isinstance(employment_types, str):
                    conditions.append('employment_type = ?')
                    params.append(employment_types)
            
            # Experience level filter (supports multiple values)
            if filters.get('experience_level'):
                experience_levels = filters['experience_level']
                if isinstance(experience_levels, list) and experience_levels:
                    placeholders = ','.join(['?' for _ in experience_levels])
                    conditions.append(f'experience_level IN ({placeholders})')
                    params.extend(experience_levels)
                elif isinstance(experience_levels, str):
                    conditions.append('experience_level = ?')
                    params.append(experience_levels)
            
            # Date posted filter (supports multiple values)
            if filters.get('date_posted'):
                date_ranges = filters['date_posted']
                if not isinstance(date_ranges, list):
                    date_ranges = [date_ranges]
                
                # Convert date range labels to actual date conditions
                date_conditions = []
                for date_range in date_ranges:
                    if date_range == 'last_hour':
                        date_conditions.append("created_at >= datetime('now', '-1 hour')")
                    elif date_range == 'last_24_hour':
                        date_conditions.append("created_at >= datetime('now', '-1 day')")
                    elif date_range == 'last_7_days':
                        date_conditions.append("created_at >= datetime('now', '-7 days')")
                    elif date_range == 'last_30_days':
                        date_conditions.append("created_at >= datetime('now', '-30 days')")
                    elif date_range == 'last_90_days':
                        date_conditions.append("created_at >= datetime('now', '-90 days')")
                
                # If we have valid date conditions, combine them with OR
                if date_conditions:
                    if len(date_conditions) == 1:
                        conditions.append(date_conditions[0])
                    else:
                        conditions.append(f"({' OR '.join(date_conditions)})")
            
            # Salary filters
            if filters.get('min_salary') and filters.get('max_salary'):
                min_salary_value = float(filters['min_salary']) if hasattr(filters['min_salary'], '__float__') else filters['min_salary']
                max_salary_value = float(filters['max_salary']) if hasattr(filters['max_salary'], '__float__') else filters['max_salary']
                
                logger.info(f"Applying salary filter: {min_salary_value} <= salary_min <= {max_salary_value}")
                
                conditions.append('(salary_min >= ? AND salary_min <= ?)')
                params.extend([min_salary_value, max_salary_value])
                
            elif filters.get('min_salary'):
                min_salary_value = float(filters['min_salary']) if hasattr(filters['min_salary'], '__float__') else filters['min_salary']
                logger.info(f"Applying min salary filter: salary_min >= {min_salary_value}")
                conditions.append('salary_min >= ?')
                params.append(min_salary_value)
                
            elif filters.get('max_salary'):
                max_salary_value = float(filters['max_salary']) if hasattr(filters['max_salary'], '__float__') else filters['max_salary']
                logger.info(f"Applying max salary filter: salary_min <= {max_salary_value}")
                conditions.append('salary_min <= ?')
                params.append(max_salary_value)
            else:
                logger.info("No salary filters applied")
            
            # Status filter - default to active
            status_filter = filters.get('status', ['active'])
            if status_filter:
                if isinstance(status_filter, list):
                    placeholders = ','.join(['?' for _ in status_filter])
                    conditions.append(f'status IN ({placeholders})')
                    params.extend(status_filter)
                else:
                    conditions.append('status = ?')
                    params.append(status_filter)
            
            # Basic search filter
            if filters.get('search'):
                conditions.append('(title LIKE ? OR company_name LIKE ?)')
                search_term = f"%{filters['search']}%"
                params.extend([search_term, search_term])
            
            # Build WHERE clause
            where_clause = ' AND '.join(conditions)
            
            # Get total count with simplified query
            count_query = f"SELECT COUNT(*) FROM jobs WHERE {where_clause}"
            try:
                count_result = db.execute_query(count_query, params, fetch_one=True)
                if isinstance(count_result, dict):
                    total_count = count_result.get('COUNT(*)', 0) or list(count_result.values())[0]
                else:
                    total_count = count_result[0] if count_result else 0
            except Exception as e:
                logger.error(f"Count query failed: {str(e)}")
                total_count = 0
            
            # Get jobs with basic query
            page = filters.get('page', 1)
            per_page = filters.get('per_page', 20)
            offset = (page - 1) * per_page
            
            # Add sorting
            sort_by = filters.get('sort_by', 'created_at')
            sort_order = filters.get('sort_order', 'desc')
            
            # Map sort fields to actual column names
            sort_mapping = {
                'created_at': 'created_at',
                'posted_at': 'posted_at',
                'title': 'title',
                'salary_min': 'salary_min',
                'salary_max': 'salary_max'
            }
            
            sort_column = sort_mapping.get(sort_by, 'created_at')
            jobs_query = f"""
                SELECT * FROM jobs 
                WHERE {where_clause} 
                ORDER BY {sort_column} {sort_order.upper()} 
                LIMIT {per_page} OFFSET {offset}
            """
            
            jobs = db.execute_query(jobs_query, params)
            
            # Process jobs and add employer/category info individually
            jobs_list = []
            for job in jobs:
                if hasattr(job, '_asdict'):
                    job_dict = job._asdict()
                elif hasattr(job, 'keys'):
                    job_dict = dict(job)
                else:
                    job_dict = job
                
                # Parse JSON fields
                json_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
                for field in json_fields:
                    if job_dict.get(field):
                        try:
                            job_dict[field] = json.loads(job_dict[field])
                        except (json.JSONDecodeError, TypeError):
                            job_dict[field] = []
                    else:
                        job_dict[field] = []
                
                # Add distance if pincode filter was applied
                if filters.get('pincode') and user_coords and job_dict.get('latitude') and job_dict.get('longitude'):
                    distance = JobsService.calculate_distance(
                        user_coords[0], user_coords[1],
                        float(job_dict['latitude']), float(job_dict['longitude'])
                    )
                    job_dict['distance_km'] = round(distance, 2)
                
                try:
                    if job_dict.get('category_id'):
                        category = db.get_by_id('job_categories', job_dict['category_id'])
                        if category:
                            if hasattr(category, '_asdict'):
                                category_dict = category._asdict()
                            elif hasattr(category, 'keys'):
                                category_dict = dict(category)
                            else:
                                category_dict = category
                            
                            job_dict['category_name'] = category_dict.get('name')
                        else:
                            job_dict['category_name'] = None
                    else:
                        job_dict['category_name'] = None
                except Exception as e:
                    logger.warning(f"Could not fetch category for job {job_dict.get('id')}: {str(e)}")
                    job_dict['category_name'] = None
                
                jobs_list.append(job_list_response_schema.dump(job_dict))
            
            return jobs_list, total_count
            
        except Exception as e:
            logger.error(f"Error retrieving jobs list: {str(e)}")
            # Return empty results instead of raising exception
            return [], 0

    @staticmethod
    def get_coordinates_for_pincode(pincode: int) -> Optional[Tuple[float, float]]:
        """
        Get latitude and longitude coordinates for a given pincode.
        First checks if we have a job with this pincode in the database,
        otherwise you can integrate with a geocoding service.
        
        Args:
            pincode: The pincode to get coordinates for
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        try:
            # First, try to find coordinates from existing jobs with this pincode
            query = """
                SELECT latitude, longitude 
                FROM jobs 
                WHERE pincode = ? 
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL 
                LIMIT 1
            """
            result = db.execute_query(query, [pincode], fetch_one=True)
            
            if result:
                return (float(result['latitude']), float(result['longitude']))
            
            # TODO: If no existing job found, you can integrate with a geocoding service
            # For example, Google Maps Geocoding API or any other service
            # For now, returning None if not found in database
            logger.warning(f"No coordinates found for pincode: {pincode}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting coordinates for pincode {pincode}: {str(e)}")
            return None

    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate the great circle distance between two points on earth using Haversine formula.
        
        Args:
            lat1, lng1: Latitude and longitude of first point
            lat2, lng2: Latitude and longitude of second point
            
        Returns:
            Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        print(f"lat1: {lat1}, lng1: {lng1}, lat2: {lat2}, lng2: {lng2}")
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
        
        
    @staticmethod
    def get_job_statistics(job_id: int, employer_id: int = None) -> Dict:
        """
        Get statistics for a specific job.
        
        Args:
            job_id: ID of the job
            employer_id: ID of employer (for authorization)
            
        Returns:
            Dict containing job statistics
        """
        try:
            # Verify job exists and authorization
            job = JobsService.get_job_by_id(job_id, include_inactive=True)
            if not job:
                raise ValueError('Job not found')
            
            if employer_id and job['employer_id'] != employer_id:
                raise ValueError('Not authorized to view statistics for this job')
            
            # Get basic stats from job record
            stats = {
                'total_views': job.get('views_count', 0),
                'total_applications': job.get('applications_count', 0),
                'total_bookmarks': job.get('bookmarks_count', 0)
            }
            
            # Get time-based statistics
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            # Views this week
            views_query = """
                SELECT COUNT(*) FROM job_views 
                WHERE job_id = ? AND viewed_at >= ?
            """
            views_this_week = db.execute_query(views_query, [job_id, week_ago], fetch_one=True)['COUNT(*)']
            stats['views_this_week'] = views_this_week

            # Applications this week (would need applications table)
            # For now, we'll set it to 0 as applications table isn't implemented yet
            stats['applications_this_week'] = 0
            
            # Calculate averages
            job_created = datetime.fromisoformat(job['created_at'])
            days_since_creation = max((datetime.now() - job_created).days, 1)
            
            stats['avg_views_per_day'] = round(stats['total_views'] / days_since_creation, 2)
            stats['avg_applications_per_day'] = round(stats['total_applications'] / days_since_creation, 2)

            # Calculate conversion rate
            if stats['total_views'] > 0:
                stats['conversion_rate'] = round((stats['total_applications'] / stats['total_views']) * 100, 2)
            else:
                stats['conversion_rate'] = 0.0
            
            return job_stats_schema.dump(stats)
            
        except Exception as e:
            logger.error(f"Error retrieving job statistics for job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def bookmark_job(job_id: int, user_id: int, notes: str = None) -> bool:
        """
        Bookmark a job for a user.
        
        Args:
            job_id: ID of the job to bookmark
            user_id: ID of the user bookmarking
            notes: Optional notes about the bookmark
            
        Returns:
            bool indicating success
        """
        try:
            # Verify job exists and is active
            job = JobsService.get_job_by_id(job_id)
            if not job:
                raise ValueError('Job not found or inactive')
            
            # Check if already bookmarked
            existing = db.record_exists('job_bookmarks', 'job_id = ? AND user_id = ?', [job_id, user_id])
            if existing:
                raise ValueError('Job already bookmarked')
            
            # Create bookmark
            bookmark_data = {
                'job_id': job_id,
                'user_id': user_id,
                'notes': notes,
                'created_at': datetime.now().isoformat()
            }
            
            db.insert('job_bookmarks', bookmark_data)
            
            # Update bookmarks count
            db.execute_query(
                'UPDATE jobs SET bookmarks_count = bookmarks_count + 1 WHERE id = ?',
                [job_id]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error bookmarking job {job_id} for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def remove_bookmark(job_id: int, user_id: int) -> bool:
        """
        Remove a job bookmark.
        
        Args:
            job_id: ID of the job
            user_id: ID of the user
            
        Returns:
            bool indicating success
        """
        try:
            # Check if bookmark exists
            existing = db.record_exists('job_bookmarks', 'job_id = ? AND user_id = ?', [job_id, user_id])
            if not existing:
                raise ValueError('Bookmark not found')
            
            # Remove bookmark
            db.delete('job_bookmarks', 'job_id = ? AND user_id = ?', [job_id, user_id])
            
            # Update bookmarks count
            db.execute_query(
                'UPDATE jobs SET bookmarks_count = CASE WHEN bookmarks_count > 0 THEN bookmarks_count - 1 ELSE 0 END WHERE id = ?',
                [job_id]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing bookmark for job {job_id} and user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_user_bookmarks(user_id: int, page: int = 1, per_page: int = 20) -> Tuple[List[Dict], int]:
        """
        Get bookmarked jobs for a user.
        
        Args:
            user_id: ID of the user
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (bookmarked_jobs, total_count)
        """
        try:
            # Get total count
            count_query = """
                SELECT COUNT(*) FROM job_bookmarks jb
                JOIN jobs j ON jb.job_id = j.id
                WHERE jb.user_id = ? AND j.is_active = 1
            """
            total_count = db.execute_query(count_query, [user_id], fetch_one=True)[0]
            
            # Get bookmarked jobs
            offset = (page - 1) * per_page
            query = """
                SELECT j.*, jb.notes as bookmark_notes, jb.created_at as bookmarked_at,
                       e.company_name as employer_company_name,
                       e.logo_url as employer_logo_url,
                       e.is_verified as employer_is_verified,
                       c.name as category_name
                FROM job_bookmarks jb
                JOIN jobs j ON jb.job_id = j.id
                LEFT JOIN employers e ON j.employer_id = e.id
                LEFT JOIN job_categories c ON j.category_id = c.id
                WHERE jb.user_id = ? AND j.is_active = 1
                ORDER BY jb.created_at DESC
                LIMIT ? OFFSET ?
            """
            
            bookmarks = db.execute_query(query, [user_id, per_page, offset])
            
            # Process results
            bookmarks_list = []
            for bookmark in bookmarks:
                bookmark_dict = dict(bookmark)
                
                # Parse JSON fields
                json_fields = ['required_skills', 'preferred_skills', 'languages', 'keywords']
                for field in json_fields:
                    if bookmark_dict.get(field):
                        try:
                            bookmark_dict[field] = json.loads(bookmark_dict[field])
                        except (json.JSONDecodeError, TypeError):
                            bookmark_dict[field] = []
                    else:
                        bookmark_dict[field] = []
                
                bookmarks_list.append(job_list_response_schema.dump(bookmark_dict))
            
            return bookmarks_list, total_count
            
        except Exception as e:
            logger.error(f"Error retrieving bookmarks for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def record_job_view(job_id: int, user_id: int = None, ip_address: str = None, user_agent: str = None, referrer: str = None):
        """
        Record a job view for analytics.
        
        Args:
            job_id: ID of the job viewed
            user_id: ID of the user (None for anonymous)
            ip_address: IP address of the viewer
            user_agent: User agent string
            referrer: Referrer URL
        """
        try:
            # Verify job exists
            if not db.record_exists('jobs', 'id = ? AND is_active = 1', [job_id]):
                return  # Silently ignore views for non-existent jobs
            
            # Record the view
            view_data = {
                'job_id': job_id,
                'user_id': user_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'referrer': referrer,
                'viewed_at': datetime.now().isoformat()
            }
            
            db.insert('job_views', view_data)
            
            # Update view count
            db.execute_query('UPDATE jobs SET views_count = views_count + 1 WHERE id = ?', [job_id])
            
        except Exception as e:
            logger.error(f"Error recording job view for job {job_id}: {str(e)}")
            # Don't raise exception for view recording failures
    
    @staticmethod
    def approve_job(job_id: int, admin_user_id: int, ip_address: str = None) -> bool:
        """
        Approve a job (admin function).
        
        Args:
            job_id: ID of the job to approve
            admin_user_id: ID of the admin approving
            ip_address: IP address for audit logging
            
        Returns:
            bool indicating success
        """
        try:
            # Verify job exists
            job = JobsService.get_job_by_id(job_id, include_inactive=True)
            if not job:
                raise ValueError('Job not found')
            
            # Update job approval status
            now = datetime.now().isoformat()
            update_data = {
                'is_approved': True,
                'approved_by': admin_user_id,
                'approved_at': now,
                'updated_at': now,
                'rejection_reason': None
            }
            
            db.update('jobs', update_data, 'id = ?', [job_id])
            
            # Log the approval
            db.log_audit(admin_user_id, 'UPDATE', 'job', job_id,
                        json.dumps({'action': 'job_approved'}),
                        ip_address)
            
            return True
            
        except Exception as e:
            logger.error(f"Error approving job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def reject_job(job_id: int, admin_user_id: int, reason: str, ip_address: str = None) -> bool:
        """
        Reject a job (admin function).
        
        Args:
            job_id: ID of the job to reject
            admin_user_id: ID of the admin rejecting
            reason: Reason for rejection
            ip_address: IP address for audit logging
            
        Returns:
            bool indicating success
        """
        try:
            # Verify job exists
            job = JobsService.get_job_by_id(job_id, include_inactive=True)
            if not job:
                raise ValueError('Job not found')
            
            # Update job rejection status
            now = datetime.now().isoformat()
            update_data = {
                'is_approved': False,
                'approved_by': admin_user_id,
                'approved_at': now,
                'updated_at': now,
                'rejection_reason': reason,
                'status': 'paused'  # Pause rejected jobs
            }
            
            db.update('jobs', update_data, 'id = ?', [job_id])
            
            # Log the rejection
            db.log_audit(admin_user_id, 'UPDATE', 'job', job_id,
                        json.dumps({'action': 'job_rejected', 'reason': reason}),
                        ip_address)
            
            return True
            
        except Exception as e:
            logger.error(f"Error rejecting job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_job_categories(include_inactive: bool = False) -> List[Dict]:
        """
        Get all job categories.
        
        Args:
            include_inactive: Whether to include inactive categories
            
        Returns:
            List of job categories
        """
        try:
            condition = '1=1'
            params = []
            
            if not include_inactive:
                condition = 'is_active = 1'
            
            categories = db.select('job_categories', '*', condition, params, 'name ASC')
            return [job_category_schema.dump(dict(category)) for category in categories]
            
        except Exception as e:
            logger.error(f"Error retrieving job categories: {str(e)}")
            raise
    
    @staticmethod
    def create_job_category(category_data: Dict, user_id: int, ip_address: str = None) -> Dict:
        """
        Create a new job category (admin function).
        
        Args:
            category_data: Category data
            user_id: ID of the user creating the category
            ip_address: IP address for audit logging
            
        Returns:
            Dict containing created category data
        """
        try:
            # Validate input
            validated_data = job_category_schema.load(category_data)
            
            # Check if category already exists
            existing = db.record_exists('job_categories', 'name = ?', [validated_data['name']])
            if existing:
                raise ValueError('Category with this name already exists')
            
            # Add timestamps
            now = datetime.now().isoformat()
            validated_data.update({
                'created_at': now,
                'updated_at': now,
                'is_active': validated_data.get('is_active', True)
            })
            
            # Create category
            category_id = db.insert('job_categories', validated_data)
            
            # Log the creation
            db.log_audit(user_id, 'CREATE', 'job_category', category_id,
                        json.dumps({'action': 'category_created', 'name': validated_data['name']}),
                        ip_address)
            
            # Return created category
            category = db.get_by_id('job_categories', category_id)
            return job_category_schema.dump(dict(category))
            
        except Exception as e:
            logger.error(f"Error creating job category: {str(e)}")
            raise
    
    @staticmethod
    def create_job_template(employer_id: int, template_data: Dict, user_id: int, ip_address: str = None) -> Dict:
        """
        Create a job template for an employer.
        
        Args:
            employer_id: ID of the employer
            template_data: Template data
            user_id: ID of the user creating the template
            ip_address: IP address for audit logging
            
        Returns:
            Dict containing created template data
        """
        try:
            # Validate input
            validated_data = job_template_schema.load(template_data)
            
            # Verify employer exists
            if not db.record_exists('employers', 'id = ? AND is_active = 1', [employer_id]):
                raise ValueError('Invalid or inactive employer')
            
            # Add required fields
            now = datetime.now().isoformat()
            validated_data.update({
                'employer_id': employer_id,
                'created_at': now,
                'updated_at': now,
                'is_active': True,
                'usage_count': 0
            })
            
            # Convert skill lists to JSON
            skill_fields = ['required_skills', 'preferred_skills']
            for field in skill_fields:
                if field in validated_data and validated_data[field]:
                    validated_data[field] = json.dumps(validated_data[field])
            
            # Create template
            template_id = db.insert('job_templates', validated_data)
            
            # Log the creation
            db.log_audit(user_id, 'CREATE', 'job_template', template_id,
                        json.dumps({'action': 'template_created', 'name': validated_data['template_name']}),
                        ip_address)
            
            # Return created template
            template = db.get_by_id('job_templates', template_id)
            template_dict = dict(template)
            
            # Parse JSON fields
            for field in skill_fields:
                if template_dict.get(field):
                    try:
                        template_dict[field] = json.loads(template_dict[field])
                    except (json.JSONDecodeError, TypeError):
                        template_dict[field] = []
                else:
                    template_dict[field] = []
            
            return job_template_schema.dump(template_dict)
            
        except Exception as e:
            logger.error(f"Error creating job template: {str(e)}")
            raise
    
    @staticmethod
    def get_employer_templates(employer_id: int) -> List[Dict]:
        """
        Get job templates for an employer.
        
        Args:
            employer_id: ID of the employer
            
        Returns:
            List of job templates
        """
        try:
            templates = db.select('job_templates', '*', 
                                'employer_id = ? AND is_active = 1', [employer_id],
                                'template_name ASC')
            
            templates_list = []
            for template in templates:
                template_dict = dict(template)
                
                # Parse JSON fields
                skill_fields = ['required_skills', 'preferred_skills']
                for field in skill_fields:
                    if template_dict.get(field):
                        try:
                            template_dict[field] = json.loads(template_dict[field])
                        except (json.JSONDecodeError, TypeError):
                            template_dict[field] = []
                    else:
                        template_dict[field] = []
                
                templates_list.append(job_template_schema.dump(template_dict))
            
            return templates_list
            
        except Exception as e:
            logger.error(f"Error retrieving templates for employer {employer_id}: {str(e)}")
            raise
    
    @staticmethod
    def expire_jobs():
        """
        Mark expired jobs as expired (background task).
        This should be called by a scheduled task.
        """
        try:
            now = datetime.now().isoformat()
            
            # Find jobs that should be expired
            expired_jobs = db.select('jobs', 'id', 
                                   "expires_at IS NOT NULL AND expires_at <= ? AND status != 'expired'",
                                   [now])
            
            if expired_jobs:
                # Update expired jobs
                job_ids = [str(job['id']) for job in expired_jobs]
                placeholders = ','.join(['?' for _ in job_ids])
                
                db.execute_query(
                    f"UPDATE jobs SET status = 'expired', updated_at = ? WHERE id IN ({placeholders})",
                    [now] + job_ids
                )
                
                logger.info(f"Expired {len(job_ids)} jobs")
            
        except Exception as e:
            logger.error(f"Error expiring jobs: {str(e)}")
            raise