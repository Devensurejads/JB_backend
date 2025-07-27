# app/utils/date_utils.py

from datetime import datetime, date
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def safe_isoformat(value: Union[datetime, date, str, None]) -> Optional[str]:
    """
    Safely convert a date/datetime value to ISO format string.
    
    Args:
        value: Date, datetime, string, or None
        
    Returns:
        ISO format string or None
    """
    if value is None:
        return None
    
    # If it's already a string, return as is
    if isinstance(value, str):
        return value
    
    # If it has isoformat method (date/datetime), use it
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    
    # Try to convert to string as fallback
    try:
        return str(value)
    except Exception as e:
        logger.warning(f"Could not convert date value to string: {value}, error: {e}")
        return None


def parse_date_string(date_str: str) -> Optional[date]:
    """
    Parse a date string into a date object.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Date object or None if parsing fails
    """
    if not date_str:
        return None
    
    # Common date formats to try
    date_formats = [
        '%Y-%m-%d',  # ISO format
        '%Y/%m/%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M:%S',  # ISO datetime
        '%Y-%m-%dT%H:%M:%S.%f',  # ISO datetime with microseconds
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date string: {date_str}")
    return None


def format_date_for_display(value: Union[datetime, date, str, None], format_str: str = '%Y-%m-%d') -> Optional[str]:
    """
    Format a date value for display.
    
    Args:
        value: Date, datetime, string, or None
        format_str: Format string for output
        
    Returns:
        Formatted date string or None
    """
    if value is None:
        return None
    
    # If it's a string, try to parse it first
    if isinstance(value, str):
        parsed_date = parse_date_string(value)
        if parsed_date:
            return parsed_date.strftime(format_str)
        return value  # Return original string if parsing fails
    
    # If it's a date/datetime object
    if hasattr(value, 'strftime'):
        return value.strftime(format_str)
    
    return str(value)


def validate_date_range(start_date: Union[date, str, None], 
                       end_date: Union[date, str, None]) -> tuple[bool, str]:
    """
    Validate that end_date is after start_date.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        (is_valid, error_message)
    """
    if not start_date or not end_date:
        return True, ""  # If either is None, no validation needed
    
    # Parse dates if they're strings
    if isinstance(start_date, str):
        start_date = parse_date_string(start_date)
    if isinstance(end_date, str):
        end_date = parse_date_string(end_date)
    
    if not start_date or not end_date:
        return False, "Invalid date format"
    
    if end_date < start_date:
        return False, "End date must be after start date"
    
    return True, ""


def age_from_birthdate(birth_date: Union[date, str, None]) -> Optional[int]:
    """
    Calculate age from birth date.
    
    Args:
        birth_date: Birth date
        
    Returns:
        Age in years or None
    """
    if not birth_date:
        return None
    
    # Parse if string
    if isinstance(birth_date, str):
        birth_date = parse_date_string(birth_date)
    
    if not birth_date:
        return None
    
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


def days_between_dates(start_date: Union[date, str, None], 
                      end_date: Union[date, str, None]) -> Optional[int]:
    """
    Calculate days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Number of days or None
    """
    if not start_date or not end_date:
        return None
    
    # Parse dates if they're strings
    if isinstance(start_date, str):
        start_date = parse_date_string(start_date)
    if isinstance(end_date, str):
        end_date = parse_date_string(end_date)
    
    if not start_date or not end_date:
        return None
    
    delta = end_date - start_date
    return delta.days


def is_current_period(start_date: Union[date, str, None], 
                     end_date: Union[date, str, None]) -> bool:
    """
    Check if a period is current (ongoing).
    
    Args:
        start_date: Start date
        end_date: End date (None means current)
        
    Returns:
        True if period is current
    """
    if not start_date:
        return False
    
    # If no end date, assume current
    if not end_date:
        return True
    
    # Parse dates if they're strings
    if isinstance(start_date, str):
        start_date = parse_date_string(start_date)
    if isinstance(end_date, str):
        end_date = parse_date_string(end_date)
    
    if not start_date:
        return False
    
    if not end_date:
        return True
    
    today = date.today()
    return start_date <= today <= end_date