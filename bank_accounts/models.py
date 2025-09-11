from django.db import models
from django.contrib.auth.models import User
import hashlib


class UploadedFile(models.Model):
    """Track CSV file uploads for bank accounts"""
    account = models.ForeignKey('coa.Account', on_delete=models.CASCADE, related_name='uploaded_files')
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


class BankTransaction(models.Model):
    """Bank transactions linked to COA accounts"""
    coa_account = models.ForeignKey('coa.Account', on_delete=models.CASCADE, related_name='bank_transactions')
    # uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)
    
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
        # Generate transaction hash for duplicate detection
        if not self.transaction_hash or self.transaction_hash == 'pending':
            hash_string = f"{self.date}{self.amount}{self.reference}{self.description}"
            self.transaction_hash = hashlib.sha256(hash_string.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.date}: {self.description} - ${self.amount}"
