"""
Process Service - Handles CSV file processing.
Follows Resilient Architecture Guide - Service Layer pattern.
"""
import logging
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction

from ..models import BankTransaction, ProcessingLog
from ..utils.exceptions import FileProcessingError, CSVParsingError, DataValidationError
from ..utils.feature_flags import require_feature

logger = logging.getLogger(__name__)


class ProcessService:
    """Service for processing uploaded CSV files"""
    
    @require_feature('CSV_PROCESSING_ENABLED')
    def process_file(self, uploaded_file):
        """
        Process uploaded CSV file and extract transactions.
        
        Args:
            uploaded_file: UploadedFile instance
            
        Returns:
            dict: Processing statistics
            
        Raises:
            FileProcessingError: If processing fails
            CSVParsingError: If CSV parsing fails
        """
        if uploaded_file.is_processed:
            raise FileProcessingError(
                "File has already been processed",
                error_code="ALREADY_PROCESSED",
                context={'file_id': uploaded_file.id}
            )
        
        processing_log = None
        try:
            # Create processing log
            processing_log = ProcessingLog.objects.create(
                uploaded_file=uploaded_file,
                success=False,
                transactions_extracted=0,
                transactions_imported=0
            )
            
            # Process the CSV file
            stats = self._process_csv_content(uploaded_file, processing_log)
            
            # Update file status
            with transaction.atomic():
                uploaded_file.is_processed = True
                uploaded_file.processed_at = datetime.now()
                uploaded_file.save()
                
                processing_log.success = True
                processing_log.transactions_extracted = stats['extracted']
                processing_log.transactions_imported = stats['imported']
                processing_log.save()
            
            logger.info(f"File processed successfully: {uploaded_file.file_name}")
            return stats
            
        except Exception as e:
            # Update processing log with error
            if processing_log:
                processing_log.error_message = str(e)
                processing_log.save()
            
            logger.error(f"File processing failed: {str(e)}")
            raise FileProcessingError(
                f"Failed to process file '{uploaded_file.file_name}': {str(e)}",
                error_code="PROCESSING_FAILED",
                context={'file_id': uploaded_file.id}
            )
    
    def _process_csv_content(self, uploaded_file, processing_log):
        """Process CSV file content and extract transactions"""
        try:
            # Read CSV content
            file_content = uploaded_file.file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_content))
            
            transactions_created = 0
            row_number = 0
            
            # Process each row
            for row_number, row in enumerate(csv_reader, 1):
                try:
                    transaction_data = self._parse_csv_row(row, row_number)
                    if transaction_data:
                        # Create transaction with atomic operation
                        with transaction.atomic():
                            BankTransaction.objects.create(
                                uploaded_file=uploaded_file,
                                **transaction_data
                            )
                        transactions_created += 1
                        
                except Exception as row_error:
                    # Log individual row errors but continue processing
                    logger.warning(f"Failed to process row {row_number}: {row_error}")
                    continue
            
            return {
                'extracted': row_number,
                'imported': transactions_created
            }
            
        except Exception as e:
            raise CSVParsingError(
                f"Failed to parse CSV content: {str(e)}",
                error_code="CSV_PARSING_FAILED",
                context={'file_id': uploaded_file.id}
            )
    
    def _parse_csv_row(self, row, row_number):
        """Parse a single CSV row into transaction data"""
        try:
            # Parse date (required)
            date_str = row.get('Date', '').strip()
            if not date_str:
                raise DataValidationError("Date field is required")
            transaction_date = self._parse_date(date_str)
            
            # Parse amount (required)
            amount_str = row.get('Amount', '').strip().replace(',', '').replace('$', '')
            if not amount_str:
                raise DataValidationError("Amount field is required")
            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                raise DataValidationError(f"Invalid amount format: {amount_str}")
            
            # Get description (required)
            description = row.get('Description', '').strip()
            if not description:
                raise DataValidationError("Description field is required")
            
            return {
                'row_number': row_number,
                'date': transaction_date,
                'amount': amount,
                'payee': row.get('Payee', '').strip()[:255] or None,
                'description': description,
                'reference': row.get('Reference', '').strip()[:100] or None
            }
            
        except (DataValidationError, ValueError) as e:
            # Skip invalid rows but log them
            logger.warning(f"Skipping invalid row {row_number}: {e}")
            return None
    
    def _parse_date(self, date_str):
        """Parse date from various formats"""
        date_formats = [
            '%Y-%m-%d',      # 2025-01-15
            '%d/%m/%Y',      # 15/01/2025
            '%m/%d/%Y',      # 01/15/2025
            '%d-%m-%Y',      # 15-01-2025
            '%d %b %Y',      # 15 Jan 2025
            '%d %B %Y',      # 15 January 2025
            '%Y/%m/%d',      # 2025/01/15
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise DataValidationError(f"Unable to parse date: {date_str}")
    
    def get_processing_stats(self, uploaded_file):
        """Get processing statistics for a file"""
        try:
            log = ProcessingLog.objects.filter(uploaded_file=uploaded_file).last()
            if log:
                return {
                    'success': log.success,
                    'extracted': log.transactions_extracted,
                    'imported': log.transactions_imported,
                    'error_message': log.error_message
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get processing stats: {str(e)}")
            return None
