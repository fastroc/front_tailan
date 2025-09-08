from django.db import models
from django.contrib.auth import get_user_model
from core.models import TimeStampedModel

User = get_user_model()


class UploadedFile(TimeStampedModel):
    """Track uploaded bank statement files"""
    file_name = models.CharField(max_length=255, verbose_name="File Name")
    file = models.FileField(
        upload_to='reconciliation/uploads/%Y/%m/%d/',
        verbose_name="Uploaded File"
    )
    file_size = models.IntegerField(verbose_name="File Size (bytes)")
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_files',
        verbose_name="Uploaded By"
    )
    
    # Bank account information
    bank_account_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Bank Account Name"
    )
    statement_period = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Statement Period"
    )
    
    # Processing status
    is_processed = models.BooleanField(
        default=False,
        verbose_name="Processed"
    )
    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Processed At"
    )
    
    class Meta:
        verbose_name = "Uploaded File"
        verbose_name_plural = "Uploaded Files"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} - {self.bank_account_name}"


class BankTransaction(TimeStampedModel):
    """Bank Statement Table - Stores individual bank transactions"""
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Source File"
    )
    row_number = models.IntegerField(verbose_name="Row Number")
    
    # CSV Bank Statement Columns
    date = models.DateField(verbose_name="Transaction Date")
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Amount"
    )
    payee = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Payee"
    )
    description = models.TextField(verbose_name="Description")
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Reference"
    )
    
    # Enhancement Columns for User Input
    who = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Who (Contact Name)"
    )
    what = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="What (Account Code)"
    )
    why = models.TextField(
        blank=True,
        null=True,
        verbose_name="Why (Reason)"
    )
    
    class Meta:
        verbose_name = "Bank Transaction"
        verbose_name_plural = "Bank Transactions"
        ordering = ['-date', 'row_number']
        
    def __str__(self):
        return f"{self.date} - ${self.amount} - {self.description[:50]}"


class ProcessingLog(TimeStampedModel):
    """Track file processing attempts"""
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='processing_logs',
        verbose_name="Uploaded File"
    )
    success = models.BooleanField(verbose_name="Success")
    error_message = models.TextField(blank=True, null=True)
    transactions_extracted = models.IntegerField(default=0)
    transactions_imported = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Processing Log"
        verbose_name_plural = "Processing Logs"
        ordering = ['-created_at']
        
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.uploaded_file.file_name} - {status}"
