"""
Feature flags for graceful degradation.
Follows Resilient Architecture Guide - Circuit Breaker pattern.
"""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Central feature flag management"""
    
    # Default feature states
    DEFAULT_FLAGS = {
        'FILE_UPLOAD_ENABLED': True,
        'CSV_PROCESSING_ENABLED': True,
        'BATCH_PROCESSING_ENABLED': True,
        'ADVANCED_VALIDATION_ENABLED': True,
        'EMAIL_NOTIFICATIONS_ENABLED': False,
    }
    
    @classmethod
    def is_enabled(cls, feature_name):
        """Check if a feature is enabled"""
        try:
            # Check Django settings first
            if hasattr(settings, 'RECONCILIATION_FEATURES'):
                feature_flags = getattr(settings, 'RECONCILIATION_FEATURES', {})
                if feature_name in feature_flags:
                    return feature_flags[feature_name]
            
            # Fall back to defaults
            return cls.DEFAULT_FLAGS.get(feature_name, False)
            
        except Exception as e:
            logger.error(f"Error checking feature flag {feature_name}: {e}")
            # Fail closed - disable feature if check fails
            return False
    
    @classmethod
    def get_all_flags(cls):
        """Get all feature flags status"""
        flags = {}
        for feature_name in cls.DEFAULT_FLAGS:
            flags[feature_name] = cls.is_enabled(feature_name)
        return flags


# Convenience functions
def check_feature_enabled(feature_name):
    """Quick check if feature is enabled"""
    return FeatureFlags.is_enabled(feature_name)


def require_feature(feature_name):
    """Decorator to require feature to be enabled"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_feature_enabled(feature_name):
                from .exceptions import ServiceUnavailableError
                raise ServiceUnavailableError(
                    f"Feature '{feature_name}' is currently disabled",
                    error_code="FEATURE_DISABLED",
                    context={'feature': feature_name}
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
