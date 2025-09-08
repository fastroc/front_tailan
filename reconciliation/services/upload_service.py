"""
Upload Service - Handles file upload operations.
Follows Resilient Architecture Guide - Service Layer pattern.
"""
import logging
from django.db import transaction

from ..models import UploadedFile
from ..utils.exceptions import FileUploadError
from ..utils.feature_flags import require_feature

logger = logging.getLogger(__name__)


class UploadService:
    """Service for handling file uploads"""
    
    @require_feature('FILE_UPLOAD_ENABLED')
    def upload_file(self, file, user, bank_account_name=None, statement_period=None):
        """
        Upload a file with validation and error handling.
        
        Args:
            file: Django UploadedFile object
            user: User uploading the file
            bank_account_name: Optional bank account name
            statement_period: Optional statement period
            
        Returns:
            UploadedFile instance
            
        Raises:
            FileUploadError: If upload fails
            ServiceUnavailableError: If service is disabled
        """
        try:
            # Validate file
            self._validate_file(file)
            
            # Create database record with transaction safety
            with transaction.atomic():
                uploaded_file = UploadedFile.objects.create(
                    file=file,
                    file_name=file.name,
                    file_size=file.size,
                    uploaded_by=user,
                    bank_account_name=bank_account_name,
                    statement_period=statement_period
                )
                
                logger.info(f"File uploaded successfully: {file.name} by user {user.id}")
                return uploaded_file
                
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise FileUploadError(
                f"Failed to upload file '{file.name}': {str(e)}",
                error_code="UPLOAD_FAILED",
                context={
                    'file_name': file.name,
                    'file_size': file.size,
                    'user_id': user.id
                }
            )
    
    def _validate_file(self, file):
        """Validate uploaded file"""
        # File extension validation
        if not file.name.lower().endswith('.csv'):
            raise FileUploadError(
                "Only CSV files are allowed",
                error_code="INVALID_FILE_TYPE",
                context={'file_name': file.name}
            )
        
        # File size validation
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            raise FileUploadError(
                f"File size ({file.size} bytes) exceeds maximum allowed size ({max_size} bytes)",
                error_code="FILE_TOO_LARGE",
                context={'file_size': file.size, 'max_size': max_size}
            )
        
        # File content validation (basic)
        if file.size == 0:
            raise FileUploadError(
                "Empty files are not allowed",
                error_code="EMPTY_FILE",
                context={'file_name': file.name}
            )
    
    def get_user_files(self, user, limit=None):
        """Get all files uploaded by user"""
        try:
            queryset = UploadedFile.objects.filter(uploaded_by=user).order_by('-created_at')
            if limit:
                queryset = queryset[:limit]
            return queryset
        except Exception as e:
            logger.error(f"Failed to get user files: {str(e)}")
            raise FileUploadError(
                "Failed to retrieve user files",
                error_code="QUERY_FAILED",
                context={'user_id': user.id}
            )
    
    def get_file_by_id(self, file_id, user):
        """Get specific file by ID for user"""
        try:
            return UploadedFile.objects.get(id=file_id, uploaded_by=user)
        except UploadedFile.DoesNotExist:
            raise FileUploadError(
                f"File with ID {file_id} not found or access denied",
                error_code="FILE_NOT_FOUND",
                context={'file_id': file_id, 'user_id': user.id}
            )
