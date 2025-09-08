"""
Reconciliation Orchestrator - Coordinates all reconciliation services.
Follows Resilient Architecture Guide - Orchestrator pattern.
"""
import logging

from .upload_service import UploadService
from .process_service import ProcessService
from ..utils.exceptions import ReconciliationBaseException
from ..utils.feature_flags import check_feature_enabled

logger = logging.getLogger(__name__)


class ReconciliationOrchestrator:
    """
    Main orchestrator for reconciliation operations.
    Coordinates between upload and processing services.
    """
    
    def __init__(self):
        self.upload_service = UploadService()
        self.process_service = ProcessService()
    
    def upload_and_process_file(self, file, user, bank_account_name=None, statement_period=None, auto_process=False):
        """
        Complete workflow: Upload file and optionally process it.
        
        Args:
            file: Django UploadedFile
            user: User uploading the file
            bank_account_name: Optional bank account name
            statement_period: Optional statement period
            auto_process: Whether to automatically process after upload
            
        Returns:
            dict: Result with uploaded_file and processing_stats (if processed)
        """
        result = {
            'uploaded_file': None,
            'processing_stats': None,
            'success': False,
            'error': None
        }
        
        try:
            # Step 1: Upload file
            uploaded_file = self.upload_service.upload_file(
                file=file,
                user=user,
                bank_account_name=bank_account_name,
                statement_period=statement_period
            )
            result['uploaded_file'] = uploaded_file
            
            # Step 2: Process file if requested and processing is enabled
            if auto_process and check_feature_enabled('CSV_PROCESSING_ENABLED'):
                try:
                    processing_stats = self.process_service.process_file(uploaded_file)
                    result['processing_stats'] = processing_stats
                except Exception as process_error:
                    # Upload succeeded but processing failed - this is OK
                    logger.warning(f"Processing failed after successful upload: {process_error}")
                    result['error'] = f"Upload successful but processing failed: {str(process_error)}"
            
            result['success'] = True
            return result
            
        except ReconciliationBaseException as e:
            result['error'] = str(e)
            logger.error(f"Orchestrated operation failed: {e}")
            return result
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error in orchestrator: {e}")
            return result
    
    def get_user_dashboard_data(self, user):
        """
        Get dashboard data for user - files, stats, etc.
        Demonstrates service coordination with error isolation.
        """
        dashboard_data = {
            'files': [],
            'total_files': 0,
            'processed_files': 0,
            'total_transactions': 0,
            'recent_activity': [],
            'service_status': self._get_service_status()
        }
        
        try:
            # Get user files (isolated - fails gracefully)
            files = self.upload_service.get_user_files(user)
            dashboard_data['files'] = files
            dashboard_data['total_files'] = files.count()
            dashboard_data['processed_files'] = files.filter(is_processed=True).count()
            
            # Get transaction count (isolated - fails gracefully)
            try:
                from ..models import BankTransaction
                dashboard_data['total_transactions'] = BankTransaction.objects.filter(
                    uploaded_file__uploaded_by=user
                ).count()
            except Exception as e:
                logger.warning(f"Failed to get transaction count: {e}")
                dashboard_data['total_transactions'] = 0
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            # Return partial data - resilient degradation
        
        return dashboard_data
    
    def _get_service_status(self):
        """Get status of all services - for monitoring"""
        return {
            'upload_enabled': check_feature_enabled('FILE_UPLOAD_ENABLED'),
            'processing_enabled': check_feature_enabled('CSV_PROCESSING_ENABLED'),
            'batch_processing_enabled': check_feature_enabled('BATCH_PROCESSING_ENABLED'),
            'advanced_validation_enabled': check_feature_enabled('ADVANCED_VALIDATION_ENABLED'),
        }
    
    def health_check(self):
        """
        Health check for the entire reconciliation system.
        Returns status of all components.
        """
        health_status = {
            'overall_healthy': True,
            'services': {},
            'timestamp': None
        }
        
        try:
            from django.utils import timezone
            health_status['timestamp'] = timezone.now()
            
            # Check upload service
            health_status['services']['upload'] = {
                'healthy': check_feature_enabled('FILE_UPLOAD_ENABLED'),
                'enabled': check_feature_enabled('FILE_UPLOAD_ENABLED')
            }
            
            # Check processing service
            health_status['services']['processing'] = {
                'healthy': check_feature_enabled('CSV_PROCESSING_ENABLED'),
                'enabled': check_feature_enabled('CSV_PROCESSING_ENABLED')
            }
            
            # Overall health
            health_status['overall_healthy'] = all(
                service['healthy'] for service in health_status['services'].values()
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status['overall_healthy'] = False
            health_status['error'] = str(e)
        
        return health_status
