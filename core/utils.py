"""
Core utility functions used across the Django project.
"""
import re
from django.core.mail import send_mail
from django.conf import settings
from django.utils.text import slugify
from django.contrib.auth.models import User


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
