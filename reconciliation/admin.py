from django.contrib import admin
from .models import UploadedFile, BankTransaction, ProcessingLog

# Simple admin registration for Bank Statement table
admin.site.register(UploadedFile)
admin.site.register(BankTransaction)  # This is the Bank Statement table
admin.site.register(ProcessingLog)
