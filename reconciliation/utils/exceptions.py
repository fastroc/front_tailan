"""
Custom exceptions for reconciliation module.
Follows Resilient Architecture Guide - Error Isolation pattern.
"""


class ReconciliationBaseException(Exception):
    """Base exception for all reconciliation errors"""
    def __init__(self, message, error_code=None, context=None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)


class FileUploadError(ReconciliationBaseException):
    """Errors related to file upload operations"""
    pass


class FileProcessingError(ReconciliationBaseException):
    """Errors related to file processing operations"""
    pass


class CSVParsingError(ReconciliationBaseException):
    """Errors related to CSV parsing"""
    pass


class DataValidationError(ReconciliationBaseException):
    """Errors related to data validation"""
    pass


class ServiceUnavailableError(ReconciliationBaseException):
    """Service temporarily unavailable"""
    pass


class CircuitBreakerOpenError(ReconciliationBaseException):
    """Circuit breaker is open - service calls blocked"""
    pass
