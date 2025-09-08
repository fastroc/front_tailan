"""
Custom validators for Django models and forms.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """
    Validate phone number format.
    Accepts formats like: +1234567890, 123-456-7890, (123) 456-7890
    """
    pattern = r'^\+?[\d\s\-\(\)]{10,20}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Enter a valid phone number.'),
            code='invalid_phone'
        )


def validate_no_special_characters(value):
    """
    Validate that value contains only letters, numbers, and spaces.
    """
    pattern = r'^[a-zA-Z0-9\s]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Only letters, numbers, and spaces are allowed.'),
            code='invalid_characters'
        )


def validate_file_size(value, max_size_mb=5):
    """
    Validate uploaded file size.
    
    Args:
        value: File field value
        max_size_mb: Maximum size in megabytes
    """
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _('File size cannot exceed %(max_size)s MB.') % {'max_size': max_size_mb},
            code='file_too_large'
        )


def validate_image_file_extension(value):
    """
    Validate that uploaded file is an image.
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    file_extension = value.name.lower().split('.')[-1]
    
    if f'.{file_extension}' not in allowed_extensions:
        raise ValidationError(
            _('Only image files are allowed.'),
            code='invalid_image_extension'
        )


def validate_positive_number(value):
    """
    Validate that number is positive.
    """
    if value <= 0:
        raise ValidationError(
            _('Value must be positive.'),
            code='negative_value'
        )


def validate_social_media_url(value):
    """
    Validate social media URL format.
    """
    social_patterns = [
        r'^https?://(www\.)?(facebook|twitter|instagram|linkedin)\.com/.+$',
        r'^https?://(www\.)?youtube\.com/.+$',
        r'^https?://(www\.)?tiktok\.com/.+$',
    ]
    
    if not any(re.match(pattern, value, re.IGNORECASE) for pattern in social_patterns):
        raise ValidationError(
            _('Enter a valid social media URL.'),
            code='invalid_social_url'
        )
