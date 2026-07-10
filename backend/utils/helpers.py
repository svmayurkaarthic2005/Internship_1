"""
Helper utilities
"""
from datetime import datetime, date
from typing import Any, Dict
import uuid


def generate_application_number() -> str:
    """
    Generate unique application number
    Format: APP-YYYY-NNNNNN
    """
    year = datetime.now().year
    unique_part = str(uuid.uuid4().int)[:6]
    return f"APP-{year}-{unique_part.zfill(6)}"


def calculate_days_between(start_date: date, end_date: date = None) -> int:
    """
    Calculate days between two dates
    If end_date is None, use today
    """
    if end_date is None:
        end_date = date.today()
    return (end_date - start_date).days


def is_overdue(submission_date: date, threshold_days: int = 30) -> bool:
    """
    Check if an application is overdue based on submission date
    """
    days_elapsed = calculate_days_between(submission_date)
    return days_elapsed > threshold_days


def format_area(area_sqm: float, unit: str = "sqm") -> str:
    """
    Format area with proper unit
    """
    if unit == "sqm":
        return f"{area_sqm:.2f} sq.m"
    elif unit == "acres":
        acres = area_sqm / 4046.86
        return f"{acres:.2f} acres"
    return f"{area_sqm:.2f}"


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from dictionary
    """
    return {k: v for k, v in data.items() if v is not None}
