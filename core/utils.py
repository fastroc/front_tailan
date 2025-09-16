"""
Core utility functions used across the Django project.
"""
import re
from datetime import date, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.utils.text import slugify
from django.contrib.auth.models import User


def get_fiscal_year_dates(company, as_of_date=None):
    """
    Get fiscal year start and end dates for a company.
    
    Args:
        company: Company object with fiscal_year_start
        as_of_date: Date to calculate fiscal year for (defaults to today)
        
    Returns:
        dict: {'start': date, 'end': date, 'year': int}
    """
    if not company.fiscal_year_start:
        # Default to calendar year if not set
        today = as_of_date or date.today()
        return {
            'start': date(today.year, 1, 1),
            'end': date(today.year, 12, 31),
            'year': today.year
        }
    
    today = as_of_date or date.today()
    fiscal_start = company.fiscal_year_start
    
    # Calculate which fiscal year we're in
    if today >= date(today.year, fiscal_start.month, fiscal_start.day):
        # We're in the current fiscal year
        fy_start = date(today.year, fiscal_start.month, fiscal_start.day)
        fy_end = date(today.year + 1, fiscal_start.month, fiscal_start.day) - timedelta(days=1)
        fy_year = today.year + 1  # Fiscal year is named by its end year
    else:
        # We're in the previous fiscal year
        fy_start = date(today.year - 1, fiscal_start.month, fiscal_start.day)
        fy_end = date(today.year, fiscal_start.month, fiscal_start.day) - timedelta(days=1)
        fy_year = today.year
    
    return {
        'start': fy_start,
        'end': fy_end,
        'year': fy_year
    }


def is_date_in_current_fiscal_year(company, check_date):
    """
    Check if a given date falls within the current fiscal year.
    
    Args:
        company: Company object
        check_date: Date to check
        
    Returns:
        Boolean
    """
    fiscal_dates = get_fiscal_year_dates(company)
    return fiscal_dates['start'] <= check_date <= fiscal_dates['end']


def get_ytd_date_range(company, as_of_date=None):
    """
    Get Year-to-Date range based on company's fiscal year.
    
    Args:
        company: Company object
        as_of_date: Date to calculate YTD to (defaults to today)
        
    Returns:
        dict: {'start': date, 'end': date}
    """
    fiscal_dates = get_fiscal_year_dates(company, as_of_date)
    end_date = as_of_date or date.today()
    
    return {
        'start': fiscal_dates['start'],
        'end': min(end_date, fiscal_dates['end'])
    }


def format_fiscal_year(company, as_of_date=None):
    """
    Format fiscal year for display (e.g., "FY 2024" or "FY 2023-24").
    
    Args:
        company: Company object
        as_of_date: Date to calculate fiscal year for
        
    Returns:
        String representation of fiscal year
    """
    fiscal_dates = get_fiscal_year_dates(company, as_of_date)
    
    if company.fiscal_year_start and company.fiscal_year_start.month != 1:
        # Non-calendar year (e.g., "FY 2023-24")
        start_year = fiscal_dates['start'].year
        end_year = fiscal_dates['end'].year
        return f"FY {start_year}-{str(end_year)[-2:]}"
    else:
        # Calendar year (e.g., "FY 2024")
        return f"FY {fiscal_dates['year']}"


def send_notification_email(user, subject, message, from_email=None):
    """
    Send notification email to a user.
    
    Args:
        user: User object or email string
        subject: Email subject
        message: Email message
        from_email: Sender email (optional)
    """
    if isinstance(user, User):
        recipient = user.email
    else:
        recipient = user
    
    if not from_email:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    return send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[recipient],
        fail_silently=False,
    )


def generate_unique_slug(model_class, title, slug_field='slug'):
    """
    Generate a unique slug for a model instance.
    
    Args:
        model_class: The model class
        title: The title to create slug from
        slug_field: The field name for the slug
    
    Returns:
        Unique slug string
    """
    slug = slugify(title)
    unique_slug = slug
    counter = 1
    
    while model_class.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1
    
    return unique_slug


def validate_phone_number(phone):
    """
    Validate phone number format.
    
    Args:
        phone: Phone number string
        
    Returns:
        Boolean indicating if phone is valid
    """
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))


def format_currency(amount, currency='USD'):
    """
    Format amount as currency.
    
    Args:
        amount: Numeric amount
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency == 'USD':
        return f"${amount:.2f}"
    elif currency == 'EUR':
        return f"€{amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def truncate_text(text, max_length=100, suffix='...'):
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
