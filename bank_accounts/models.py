from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import hashlib
import json
import uuid


class UploadedFile(models.Model):
    """Track CSV file uploads for bank accounts"""
    account = models.ForeignKey('coa.Account', on_delete=models.CASCADE, related_name='uploaded_files')
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='uploaded_files', null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    stored_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_hash = models.CharField(max_length=64)  # SHA256 hash
    
    # Upload metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Processing results
    total_rows = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.imported_count} transactions"


class BankStatementDocument(models.Model):
    """
    IMMUTABLE storage of original bank statement files
    This data NEVER gets modified after upload - preserves legal document integrity
    """
    # Unique identifier
    document_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # File metadata
    original_filename = models.CharField(max_length=255, help_text="Original filename as uploaded")
    file_format = models.CharField(max_length=10, choices=[('xlsx', 'Excel'), ('csv', 'CSV')])
    file_size_bytes = models.IntegerField()
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    
    # Company context
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='bank_statement_documents')
    
    # Document integrity verification
    file_hash = models.CharField(max_length=64, help_text="SHA256 hash for integrity verification")
    verification_checksum = models.CharField(max_length=128, blank=True)
    
    # Raw document data (100% original - NEVER modify)
    raw_header_data = models.JSONField(help_text="Exactly as in original file - header rows")
    raw_transaction_data = models.JSONField(help_text="Every cell, every character preserved")
    original_encoding = models.CharField(max_length=20, default='utf-8')
    
    # Document status
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-upload_timestamp']
        indexes = [
            models.Index(fields=['company', 'upload_timestamp']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['document_id']),
        ]
    
    def save(self, *args, **kwargs):
        # Generate verification checksum on save
        if not self.verification_checksum:
            combined_data = json.dumps({
                'header': self.raw_header_data,
                'transactions': self.raw_transaction_data,
                'filename': self.original_filename
            }, sort_keys=True)
            self.verification_checksum = hashlib.sha256(combined_data.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    def verify_integrity(self):
        """Verify document hasn't been tampered with"""
        combined_data = json.dumps({
            'header': self.raw_header_data,
            'transactions': self.raw_transaction_data,
            'filename': self.original_filename
        }, sort_keys=True)
        current_checksum = hashlib.sha256(combined_data.encode()).hexdigest()
        return current_checksum == self.verification_checksum
    
    def __str__(self):
        return f"Document: {self.original_filename} ({self.upload_timestamp.strftime('%Y-%m-%d')})"


class BankStatementProcessing(models.Model):
    """
    Processing metadata and system translations - separate from original document
    This is where we do translations and categorizations WITHOUT modifying originals
    """
    # Link to immutable source
    source_document = models.OneToOneField(BankStatementDocument, on_delete=models.CASCADE, related_name='processing')
    
    # Processing metadata
    processing_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    processing_timestamp = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Language detection and confidence
    detected_language = models.CharField(max_length=10, choices=[
        ('mn', 'Mongolian'),
        ('en', 'English'),
        ('mixed', 'Mixed Languages')
    ])
    language_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000, 
                                            help_text="Confidence level 0.0000-1.0000")
    
    # Translated/categorized fields (for system use only)
    system_account_holder = models.CharField(max_length=200, blank=True)
    system_account_number = models.CharField(max_length=50, blank=True)
    system_account_type = models.CharField(max_length=50, blank=True, help_text="English translation for backend")
    system_currency = models.CharField(max_length=10, default='MNT')
    system_date_range_start = models.DateField(null=True, blank=True)
    system_date_range_end = models.DateField(null=True, blank=True)
    
    # Processing statistics
    total_transactions = models.IntegerField(default=0)
    successfully_processed = models.IntegerField(default=0)
    failed_translations = models.IntegerField(default=0)
    processing_complete = models.BooleanField(default=False)
    
    # Translation confidence tracking
    translation_details = models.JSONField(blank=True, null=True, help_text="Detailed translation confidence scores")
    
    # Account linking
    suggested_coa_account = models.ForeignKey('coa.Account', null=True, blank=True, on_delete=models.SET_NULL)
    auto_link_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)
    user_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-processing_timestamp']
        indexes = [
            models.Index(fields=['source_document', 'processing_complete']),
            models.Index(fields=['processing_id']),
        ]
    
    def __str__(self):
        return f"Processing: {self.source_document.original_filename} ({self.get_detected_language_display()})"


class BankTransactionRecord(models.Model):
    """
    Individual transaction with original + system versions
    Maintains both immutable original data and translated system data
    """
    # Link to processing session
    processing = models.ForeignKey(BankStatementProcessing, on_delete=models.CASCADE, related_name='transaction_records')
    row_number = models.IntegerField(help_text="Position in original file (1-based)")
    
    # ORIGINAL data (never modified - legal document preservation)
    original_date_text = models.CharField(max_length=50, help_text="Exactly as in file")
    original_amount_text = models.CharField(max_length=50, help_text="With all original formatting")
    original_description = models.TextField(help_text="Cyrillic/mixed language as-is")
    original_payee = models.CharField(max_length=200, blank=True, help_text="Original payee field")
    original_reference = models.CharField(max_length=100, blank=True)
    original_memo = models.TextField(blank=True, help_text="Any memo/notes field")
    
    # SYSTEM data (for processing only - derived from original)
    system_date = models.DateField(null=True, blank=True, help_text="Parsed for system use")
    system_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    system_description_english = models.TextField(blank=True, help_text="For searching/matching")
    system_payee_english = models.CharField(max_length=200, blank=True)
    system_category = models.CharField(max_length=50, blank=True, help_text="Auto-categorized transaction type")
    
    # Translation confidence scores
    date_parse_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)
    amount_parse_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)
    description_translation_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)
    overall_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)
    
    # Translation details for user verification
    translation_notes = models.JSONField(blank=True, null=True, help_text="Detailed translation process info")
    
    # Manual reconciliation status
    is_reconciled = models.BooleanField(default=False)
    reconciled_with_coa = models.ForeignKey('coa.Account', null=True, blank=True, on_delete=models.SET_NULL)
    reconciliation_notes = models.TextField(blank=True)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reconciled_transactions')
    reconciliation_date = models.DateTimeField(null=True, blank=True)
    
    # User verification of translations
    user_verified_translation = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_translations')
    verification_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['processing', 'row_number']
        indexes = [
            models.Index(fields=['processing', 'row_number']),
            models.Index(fields=['system_date', 'system_amount']),
            models.Index(fields=['is_reconciled']),
            models.Index(fields=['user_verified_translation']),
        ]
        unique_together = [['processing', 'row_number']]  # Ensure one record per file row
    
    def __str__(self):
        return f"Row {self.row_number}: {self.original_description[:50]}..."
    
    def get_confidence_level(self):
        """Return human-readable confidence level"""
        if self.overall_confidence >= 0.9:
            return "High"
        elif self.overall_confidence >= 0.7:
            return "Medium"
        elif self.overall_confidence >= 0.5:
            return "Low"
        else:
            return "Very Low"
    
    def needs_verification(self):
        """Check if this transaction needs user verification"""
        return (
            not self.user_verified_translation or 
            self.overall_confidence < 0.8 or
            self.failed_translations > 0
        )


class BankTransaction(models.Model):
    """Bank transactions linked to COA accounts"""
    coa_account = models.ForeignKey('coa.Account', on_delete=models.CASCADE, related_name='bank_transactions')
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='bank_transactions', null=True, blank=True, help_text="Company this transaction belongs to")
    # uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    
    date = models.DateField()
    transaction_datetime = models.DateTimeField(null=True, blank=True, help_text="Full transaction date and time if available")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)
    related_account = models.CharField(max_length=20, blank=True, help_text="Харьцсан данс - Related account number from column H")
    
    # Smart processing fields (new fields for AI functionality)
    customer_name = models.CharField(max_length=200, blank=True, help_text="Customer name extracted from description")
    loan_number = models.CharField(max_length=50, blank=True, null=True, help_text="Loan number if detected")
    transaction_type = models.CharField(max_length=20, choices=[
        ('auto', 'Auto-Detected'),
        ('disbursement', 'Loan Disbursement'),
        ('payment', 'Loan Payment'),
        ('other', 'Other')
    ], default='auto', help_text="Type of transaction")
    processing_method = models.CharField(max_length=20, choices=[
        ('manual', 'Manual Entry'),
        ('import', 'File Import'),
        ('smart_ai', 'Smart AI Processing')
    ], default='manual', help_text="How this transaction was processed")
    confidence_score = models.IntegerField(default=0, help_text="AI confidence score (0-100)")
    notes = models.TextField(blank=True, help_text="Additional notes or comments")
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_transactions')
    suggestion_feedback = models.CharField(max_length=20, choices=[
        ('good', 'Good Match'),
        ('poor', 'Poor Match'),
        ('corrected', 'User Corrected')
    ], blank=True, null=True, help_text="User feedback on AI suggestion quality")
    
    # Link to new transaction record system (optional for backward compatibility)
    source_transaction_record = models.ForeignKey(BankTransactionRecord, on_delete=models.SET_NULL, null=True, blank=True, 
                                                help_text="Link to original document transaction")
    
    # Duplicate detection
    transaction_hash = models.CharField(max_length=64, db_index=True, default='pending')  # For duplicate detection
    
    # Tracking (keep old fields for now)
    uploaded_file = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date', '-id']
        # unique_together = ['coa_account', 'transaction_hash']  # Add later after data cleanup
    
    def save(self, *args, **kwargs):
        # Generate transaction hash for duplicate detection (only if not already set properly)
        if not self.transaction_hash or self.transaction_hash == 'pending':
            # Use consistent format: date, amount, reference, description
            hash_string = f"{self.date}{self.amount}{self.reference}{self.description}"
            self.transaction_hash = hashlib.sha256(hash_string.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    def regenerate_hash(self):
        """Regenerate the transaction hash - use this to fix inconsistent hashes
        
        Note: This uses only the DATE (not full datetime) because the model only stores dates.
        New uploads use the full datetime during import for more precise duplicate detection.
        """
        hash_string = f"{self.date}{self.amount}{self.reference}{self.description}"
        self.transaction_hash = hashlib.sha256(hash_string.encode()).hexdigest()
        return self.transaction_hash
    
    def __str__(self):
        return f"{self.date}: {self.description} - ${self.amount}"
