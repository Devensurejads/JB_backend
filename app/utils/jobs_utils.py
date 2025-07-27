# app/utils/jobs_utils.py

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from app.utils.db_abstraction import db

logger = logging.getLogger(__name__)


class JobsUtils:
    """Utility functions for job management."""
    
    @staticmethod
    def calculate_profile_completion(job_data: Dict) -> float:
        """
        Calculate job posting completion percentage.
        
        Args:
            job_data: Dictionary containing job data
            
        Returns:
            Float representing completion percentage (0-100)
        """
        required_fields = [
            'title', 'description', 'employment_type', 'location'
        ]
        
        optional_fields = [
            'short_description', 'requirements', 'responsibilities', 'benefits',
            'experience_level', 'education_level', 'salary_min', 'salary_max',
            'contact_email', 'contact_phone', 'company_overview',
            'required_skills', 'preferred_skills'
        ]
        
        total_fields = len(required_fields) + len(optional_fields)
        completed_fields = 0
        
        # Check required fields (worth more)
        for field in required_fields:
            if job_data.get(field):
                completed_fields += 2  # Required fields worth double
        
        # Check optional fields
        for field in optional_fields:
            if job_data.get(field):
                if isinstance(job_data[field], list) and len(job_data[field]) > 0:
                    completed_fields += 1
                elif isinstance(job_data[field], str) and job_data[field].strip():
                    completed_fields += 1
                elif job_data[field] is not None:
                    completed_fields += 1
        
        # Calculate percentage (required fields count double)
        max_score = len(required_fields) * 2 + len(optional_fields)
        completion_percentage = (completed_fields / max_score) * 100
        
        return round(min(completion_percentage, 100.0), 2)
    
    @staticmethod
    def generate_job_slug(title: str, job_id: int) -> str:
        """
        Generate a URL-friendly slug for a job.
        
        Args:
            title: Job title
            job_id: Job ID
            
        Returns:
            URL-friendly slug
        """
        import re
        
        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        
        # Add job ID to ensure uniqueness
        return f"{slug}-{job_id}"
    
    @staticmethod
    def extract_keywords_from_text(text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from job description for SEO.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of keywords
        """
        import re
        from collections import Counter
        
        # Common stop words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'our', 'their'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out stop words and short words
        filtered_words = [word for word in words if word not in stop_words and len(word) >= 3]
        
        # Count word frequency
        word_counts = Counter(filtered_words)
        
        # Return most common words
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    @staticmethod
    def validate_salary_range(salary_min: float, salary_max: float, currency: str = 'USD') -> bool:
        """
        Validate salary range for reasonableness.
        
        Args:
            salary_min: Minimum salary
            salary_max: Maximum salary
            currency: Currency code
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation
        if salary_min < 0 or salary_max < 0:
            return False
        
        if salary_max < salary_min:
            return False
        
        # Currency-specific validation (basic ranges)
        currency_limits = {
            'USD': {'min': 1000, 'max': 10000000},
            'EUR': {'min': 1000, 'max': 8000000},
            'GBP': {'min': 1000, 'max': 7000000},
            'INR': {'min': 100000, 'max': 500000000},
        }
        
        limits = currency_limits.get(currency, currency_limits['USD'])
        
        if salary_min < limits['min'] or salary_max > limits['max']:
            return False
        
        return True
    
    @staticmethod
    def get_job_match_score(job_data: Dict, candidate_profile: Dict) -> float:
        """
        Calculate match score between a job and candidate profile.
        
        Args:
            job_data: Job information
            candidate_profile: Candidate profile information
            
        Returns:
            Match score as a percentage (0-100)
        """
        score = 0.0
        max_score = 0.0
        
        # Skills matching (40% weight)
        job_skills = job_data.get('required_skills', []) + job_data.get('preferred_skills', [])
        candidate_skills = candidate_profile.get('skills', [])
        
        if job_skills:
            skill_matches = len(set(job_skills) & set(candidate_skills))
            skill_score = (skill_matches / len(job_skills)) * 40
            score += skill_score
        max_score += 40
        
        # Experience level matching (25% weight)
        job_exp_level = job_data.get('experience_level')
        candidate_exp = candidate_profile.get('experience_years', 0)
        
        exp_level_mapping = {
            'entry': (0, 2),
            'junior': (1, 4),
            'mid': (3, 7),
            'senior': (6, 12),
            'executive': (10, 50)
        }
        
        if job_exp_level and job_exp_level in exp_level_mapping:
            min_exp, max_exp = exp_level_mapping[job_exp_level]
            if min_exp <= candidate_exp <= max_exp:
                score += 25
            elif candidate_exp >= min_exp:
                # Partial credit for higher experience
                score += 15
        max_score += 25
        
        # Location matching (15% weight)
        job_location = job_data.get('city', '').lower()
        candidate_location = candidate_profile.get('city', '').lower()
        job_remote = job_data.get('is_remote', False)
        candidate_remote_pref = candidate_profile.get('remote_work_preference', 'hybrid')
        
        if job_remote or candidate_remote_pref in ['remote', 'hybrid']:
            score += 15
        elif job_location and candidate_location and job_location == candidate_location:
            score += 15
        elif job_location and candidate_location:
            # Partial credit for same country/state
            score += 5
        max_score += 15
        
        # Employment type matching (10% weight)
        job_type = job_data.get('employment_type')
        candidate_pref_type = candidate_profile.get('preferred_job_type')
        
        if job_type and candidate_pref_type and job_type == candidate_pref_type:
            score += 10
        max_score += 10
        
        # Salary matching (10% weight)
        job_salary_min = job_data.get('salary_min')
        job_salary_max = job_data.get('salary_max')
        candidate_salary_min = candidate_profile.get('preferred_salary_min')
        candidate_salary_max = candidate_profile.get('preferred_salary_max')
        
        if job_salary_min and candidate_salary_min:
            if job_salary_min >= candidate_salary_min:
                score += 10
            elif job_salary_max and job_salary_max >= candidate_salary_min:
                score += 5
        max_score += 10
        
        # Calculate final percentage
        if max_score > 0:
            return round((score / max_score) * 100, 2)
        else:
            return 0.0
    
    @staticmethod
    def get_trending_skills(days: int = 30, limit: int = 20) -> List[Dict]:
        """
        Get trending skills from recent job postings.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of skills to return
            
        Returns:
            List of trending skills with counts
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get skills from recent job postings
            query = """
                SELECT js.skill_name, COUNT(*) as frequency
                FROM job_skills js
                JOIN jobs j ON js.job_id = j.id
                WHERE j.created_at >= ? AND j.is_active = 1 AND j.status = 'active'
                GROUP BY js.skill_name
                ORDER BY frequency DESC
                LIMIT ?
            """
            
            skills = db.execute_query(query, [cutoff_date, limit])
            
            return [{'skill': skill['skill_name'], 'count': skill['frequency']} for skill in skills]
            
        except Exception as e:
            logger.error(f"Error getting trending skills: {str(e)}")
            return []
    
    @staticmethod
    def get_salary_insights(location: str = None, employment_type: str = None, 
                          experience_level: str = None) -> Dict:
        """
        Get salary insights for job market analysis.
        
        Args:
            location: Location filter
            employment_type: Employment type filter
            experience_level: Experience level filter
            
        Returns:
            Dictionary containing salary insights
        """
        try:
            conditions = ['j.is_active = 1', 'j.status = ?', 'j.salary_min IS NOT NULL']
            params = ['active']
            
            if location:
                conditions.append('j.city LIKE ?')
                params.append(f'%{location}%')
            
            if employment_type:
                conditions.append('j.employment_type = ?')
                params.append(employment_type)
            
            if experience_level:
                conditions.append('j.experience_level = ?')
                params.append(experience_level)
            
            where_clause = ' AND '.join(conditions)
            
            # Get salary statistics
            query = f"""
                SELECT 
                    AVG(j.salary_min) as avg_min_salary,
                    AVG(j.salary_max) as avg_max_salary,
                    MIN(j.salary_min) as min_salary,
                    MAX(j.salary_max) as max_salary,
                    COUNT(*) as job_count
                FROM jobs j
                WHERE {where_clause}
            """
            
            result = db.execute_query(query, params, fetch_one=True)
            
            if result and result['job_count'] > 0:
                return {
                    'average_min_salary': round(result['avg_min_salary'], 2) if result['avg_min_salary'] else 0,
                    'average_max_salary': round(result['avg_max_salary'], 2) if result['avg_max_salary'] else 0,
                    'min_salary': result['min_salary'] or 0,
                    'max_salary': result['max_salary'] or 0,
                    'job_count': result['job_count']
                }
            else:
                return {
                    'average_min_salary': 0,
                    'average_max_salary': 0,
                    'min_salary': 0,
                    'max_salary': 0,
                    'job_count': 0
                }
            
        except Exception as e:
            logger.error(f"Error getting salary insights: {str(e)}")
            return {
                'average_min_salary': 0,
                'average_max_salary': 0,
                'min_salary': 0,
                'max_salary': 0,
                'job_count': 0
            }
    
    @staticmethod
    def cleanup_expired_jobs():
        """
        Clean up expired jobs and update job statistics.
        This should be run as a background task.
        """
        try:
            from app.services.jobs_service import JobsService
            
            # Mark expired jobs
            JobsService.expire_jobs()
            
            # Reset monthly job counts at the beginning of each month
            current_month = datetime.now().strftime('%Y-%m-01')
            last_reset_key = 'last_monthly_reset'
            
            # Check if we need to reset monthly counts
            last_reset = db.select('system_settings', 'value', 'key = ?', [last_reset_key])
            
            if not last_reset:
                # First time, create the setting
                db.insert('system_settings', {
                    'key': last_reset_key,
                    'value': current_month,
                    'description': 'Last time monthly job counts were reset',
                    'category': 'jobs'
                })
            else:
                last_reset_date = list(last_reset)[0]['value']
                if last_reset_date != current_month:
                    # Reset monthly counts for all employers
                    db.execute_query('UPDATE employers SET jobs_posted_this_month = 0')
                    
                    # Update the last reset date
                    db.update('system_settings', {'value': current_month}, 'key = ?', [last_reset_key])
                    
                    logger.info("Monthly job counts reset for all employers")
            
            logger.info("Job cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during job cleanup: {str(e)}")
            raise
    
    @staticmethod
    def send_job_alert_notifications():
        """
        Send job alert notifications to users.
        This should be run as a background task.
        """
        try:
            # Get all active job alerts
            alerts = db.select('job_alerts', '*', 'is_active = 1')
            
            for alert in alerts:
                alert_dict = dict(alert)
                user_id = alert_dict['user_id']
                
                # Parse JSON fields
                keywords = json.loads(alert_dict.get('keywords', '[]')) if alert_dict.get('keywords') else []
                employment_types = json.loads(alert_dict.get('employment_type', '[]')) if alert_dict.get('employment_type') else []
                experience_levels = json.loads(alert_dict.get('experience_level', '[]')) if alert_dict.get('experience_level') else []
                remote_types = json.loads(alert_dict.get('remote_type', '[]')) if alert_dict.get('remote_type') else []
                
                # Build search filters
                filters = {}
                
                if keywords:
                    filters['search'] = ' '.join(keywords)
                
                if alert_dict.get('location'):
                    filters['city'] = alert_dict['location']
                
                if employment_types:
                    filters['employment_type'] = employment_types
                
                if experience_levels:
                    filters['experience_level'] = experience_levels
                
                if remote_types:
                    filters['remote_type'] = remote_types
                
                if alert_dict.get('salary_min'):
                    filters['salary_min'] = alert_dict['salary_min']
                
                # Only get jobs posted since last alert
                last_sent = alert_dict.get('last_sent_at')
                if last_sent:
                    filters['posted_after'] = datetime.fromisoformat(last_sent).date()
                
                filters['per_page'] = 50  # Limit results
                
                # Get matching jobs
                from app.services.jobs_service import JobsService
                matching_jobs, total_count = JobsService.get_jobs_list(filters)
                
                if matching_jobs:
                    # Here you would send the notification (email, SMS, etc.)
                    # For now, we'll just log it
                    logger.info(f"Job alert for user {user_id}: {total_count} new jobs found")
                    
                    # Update last_sent_at
                    now = datetime.now().isoformat()
                    db.update('job_alerts', {'last_sent_at': now}, 'id = ?', [alert_dict['id']])
            
            logger.info("Job alert notifications processed successfully")
            
        except Exception as e:
            logger.error(f"Error sending job alert notifications: {str(e)}")
            raise
    
    @staticmethod
    def generate_job_report(employer_id: int = None, start_date: str = None, end_date: str = None) -> Dict:
        """
        Generate a comprehensive job posting report.
        
        Args:
            employer_id: Optional employer ID to filter by
            start_date: Start date for the report (ISO format)
            end_date: End date for the report (ISO format)
            
        Returns:
            Dictionary containing report data
        """
        try:
            conditions = ['j.is_active = 1']
            params = []
            
            if employer_id:
                conditions.append('j.employer_id = ?')
                params.append(employer_id)
            
            if start_date:
                conditions.append('j.created_at >= ?')
                params.append(start_date)
            
            if end_date:
                conditions.append('j.created_at <= ?')
                params.append(end_date)
            
            where_clause = ' AND '.join(conditions)
            
            # Overall statistics
            stats_query = f"""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(CASE WHEN j.status = 'active' THEN 1 END) as active_jobs,
                    COUNT(CASE WHEN j.status = 'draft' THEN 1 END) as draft_jobs,
                    COUNT(CASE WHEN j.status = 'paused' THEN 1 END) as paused_jobs,
                    COUNT(CASE WHEN j.status = 'closed' THEN 1 END) as closed_jobs,
                    COUNT(CASE WHEN j.status = 'expired' THEN 1 END) as expired_jobs,
                    SUM(j.views_count) as total_views,
                    SUM(j.applications_count) as total_applications,
                    AVG(j.views_count) as avg_views_per_job,
                    AVG(j.applications_count) as avg_applications_per_job
                FROM jobs j
                WHERE {where_clause}
            """
            
            stats = dict(db.execute_query(stats_query, params, fetch_one=True))
            
            # Employment type breakdown
            employment_type_query = f"""
                SELECT 
                    j.employment_type,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM jobs j2 WHERE {where_clause}), 2) as percentage
                FROM jobs j
                WHERE {where_clause}
                GROUP BY j.employment_type
                ORDER BY count DESC
            """
            
            employment_types = [dict(row) for row in db.execute_query(employment_type_query, params + params)]
            
            # Experience level breakdown
            experience_level_query = f"""
                SELECT 
                    j.experience_level,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM jobs j2 WHERE {where_clause}), 2) as percentage
                FROM jobs j
                WHERE {where_clause} AND j.experience_level IS NOT NULL
                GROUP BY j.experience_level
                ORDER BY count DESC
            """
            
            experience_levels = [dict(row) for row in db.execute_query(experience_level_query, params + params)]
            
            # Location breakdown
            location_query = f"""
                SELECT 
                    j.city,
                    j.country,
                    COUNT(*) as count
                FROM jobs j
                WHERE {where_clause} AND j.city IS NOT NULL
                GROUP BY j.city, j.country
                ORDER BY count DESC
                LIMIT 10
            """
            
            locations = [dict(row) for row in db.execute_query(location_query, params)]
            
            # Remote work breakdown
            remote_query = f"""
                SELECT 
                    CASE 
                        WHEN j.is_remote = 1 THEN j.remote_type
                        ELSE 'onsite'
                    END as work_type,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM jobs j2 WHERE {where_clause}), 2) as percentage
                FROM jobs j
                WHERE {where_clause}
                GROUP BY work_type
                ORDER BY count DESC
            """
            
            remote_breakdown = [dict(row) for row in db.execute_query(remote_query, params + params)]
            
            # Salary insights (if salary data is available)
            salary_query = f"""
                SELECT 
                    j.salary_currency,
                    COUNT(*) as jobs_with_salary,
                    AVG(j.salary_min) as avg_min_salary,
                    AVG(j.salary_max) as avg_max_salary,
                    MIN(j.salary_min) as min_salary,
                    MAX(j.salary_max) as max_salary
                FROM jobs j
                WHERE {where_clause} AND j.salary_min IS NOT NULL
                GROUP BY j.salary_currency
                ORDER BY jobs_with_salary DESC
            """
            
            salary_data = [dict(row) for row in db.execute_query(salary_query, params)]
            
            # Top skills (from job_skills table)
            skills_query = f"""
                SELECT 
                    js.skill_name,
                    COUNT(*) as frequency,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT j.id) FROM jobs j WHERE {where_clause}), 2) as percentage
                FROM job_skills js
                JOIN jobs j ON js.job_id = j.id
                WHERE {where_clause}
                GROUP BY js.skill_name
                ORDER BY frequency DESC
                LIMIT 20
            """
            
            top_skills = [dict(row) for row in db.execute_query(skills_query, params)]
            
            # Jobs by category
            category_query = f"""
                SELECT 
                    c.name as category_name,
                    COUNT(j.id) as job_count,
                    ROUND(COUNT(j.id) * 100.0 / (SELECT COUNT(*) FROM jobs j2 WHERE {where_clause}), 2) as percentage
                FROM job_categories c
                LEFT JOIN jobs j ON c.id = j.category_id AND {where_clause}
                WHERE c.is_active = 1
                GROUP BY c.id, c.name
                HAVING job_count > 0
                ORDER BY job_count DESC
            """
            
            categories = [dict(row) for row in db.execute_query(category_query, params + params)]
            
            # Performance metrics over time (last 30 days)
            if not start_date:
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            else:
                thirty_days_ago = start_date
            
            daily_stats_query = f"""
                SELECT 
                    DATE(j.created_at) as date,
                    COUNT(*) as jobs_posted,
                    SUM(j.views_count) as total_views,
                    SUM(j.applications_count) as total_applications
                FROM jobs j
                WHERE j.created_at >= ? AND {where_clause}
                GROUP BY DATE(j.created_at)
                ORDER BY date DESC
                LIMIT 30
            """
            
            daily_stats = [dict(row) for row in db.execute_query(daily_stats_query, [thirty_days_ago] + params)]
            
            return {
                'report_period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'employer_id': employer_id
                },
                'overall_statistics': stats,
                'employment_type_breakdown': employment_types,
                'experience_level_breakdown': experience_levels,
                'top_locations': locations,
                'remote_work_breakdown': remote_breakdown,
                'salary_insights': salary_data,
                'top_skills': top_skills,
                'category_breakdown': categories,
                'daily_performance': daily_stats,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating job report: {str(e)}")
            raise
    
    @staticmethod
    def validate_job_data_integrity():
        """
        Validate job data integrity and fix common issues.
        This should be run as a maintenance task.
        """
        try:
            issues_found = []
            
            # Check for jobs with missing required data
            missing_data_query = """
                SELECT id, title FROM jobs 
                WHERE is_active = 1 AND (
                    title IS NULL OR title = '' OR
                    description IS NULL OR description = '' OR
                    employment_type IS NULL OR employment_type = ''
                )
            """
            
            missing_data_jobs = db.execute_query(missing_data_query)
            if missing_data_jobs:
                issues_found.append({
                    'type': 'missing_required_data',
                    'count': len(missing_data_jobs),
                    'jobs': [dict(job) for job in missing_data_jobs]
                })
            
            # Check for jobs with invalid salary ranges
            invalid_salary_query = """
                SELECT id, title, salary_min, salary_max FROM jobs 
                WHERE is_active = 1 AND salary_min IS NOT NULL AND salary_max IS NOT NULL
                AND salary_max < salary_min
            """
            
            invalid_salary_jobs = db.execute_query(invalid_salary_query)
            if invalid_salary_jobs:
                issues_found.append({
                    'type': 'invalid_salary_range',
                    'count': len(invalid_salary_jobs),
                    'jobs': [dict(job) for job in invalid_salary_jobs]
                })
            
            # Check for jobs with past application deadlines that are still active
            past_deadline_query = """
                SELECT id, title, application_deadline FROM jobs 
                WHERE is_active = 1 AND status = 'active'
                AND application_deadline IS NOT NULL 
                AND application_deadline < DATE('now')
            """
            
            past_deadline_jobs = db.execute_query(past_deadline_query)
            if past_deadline_jobs:
                # Auto-fix: pause these jobs
                job_ids = [str(job['id']) for job in past_deadline_jobs]
                placeholders = ','.join(['?' for _ in job_ids])
                
                db.execute_query(
                    f"UPDATE jobs SET status = 'paused' WHERE id IN ({placeholders})",
                    job_ids
                )
                
                issues_found.append({
                    'type': 'past_application_deadline',
                    'count': len(past_deadline_jobs),
                    'action': 'auto_paused',
                    'jobs': [dict(job) for job in past_deadline_jobs]
                })
            
            # Check for orphaned job skills
            orphaned_skills_query = """
                SELECT js.id, js.job_id, js.skill_name FROM job_skills js
                LEFT JOIN jobs j ON js.job_id = j.id
                WHERE j.id IS NULL
            """
            
            orphaned_skills = db.execute_query(orphaned_skills_query)
            if orphaned_skills:
                # Auto-fix: remove orphaned skills
                skill_ids = [str(skill['id']) for skill in orphaned_skills]
                placeholders = ','.join(['?' for _ in skill_ids])
                
                db.execute_query(
                    f"DELETE FROM job_skills WHERE id IN ({placeholders})",
                    skill_ids
                )
                
                issues_found.append({
                    'type': 'orphaned_job_skills',
                    'count': len(orphaned_skills),
                    'action': 'auto_removed'
                })
            
            # Check for orphaned job questions
            orphaned_questions_query = """
                SELECT jq.id, jq.job_id FROM job_questions jq
                LEFT JOIN jobs j ON jq.job_id = j.id
                WHERE j.id IS NULL
            """
            
            orphaned_questions = db.execute_query(orphaned_questions_query)
            if orphaned_questions:
                # Auto-fix: remove orphaned questions
                question_ids = [str(q['id']) for q in orphaned_questions]
                placeholders = ','.join(['?' for _ in question_ids])
                
                db.execute_query(
                    f"DELETE FROM job_questions WHERE id IN ({placeholders})",
                    question_ids
                )
                
                issues_found.append({
                    'type': 'orphaned_job_questions',
                    'count': len(orphaned_questions),
                    'action': 'auto_removed'
                })
            
            # Log results
            if issues_found:
                logger.warning(f"Job data integrity check found {len(issues_found)} types of issues")
                for issue in issues_found:
                    logger.warning(f"Issue: {issue['type']}, Count: {issue['count']}")
            else:
                logger.info("Job data integrity check passed - no issues found")
            
            return {
                'check_completed_at': datetime.now().isoformat(),
                'issues_found': issues_found,
                'total_issue_types': len(issues_found)
            }
            
        except Exception as e:
            logger.error(f"Error during job data integrity check: {str(e)}")
            raise