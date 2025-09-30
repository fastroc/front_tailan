"""
Data migration to set general_loans_receivable_account from existing principal_account
"""
from django.db import migrations


def populate_general_loans_receivable_account(apps, schema_editor):
    """Set general_loans_receivable_account to existing principal_account for all configurations"""
    LoanGLConfiguration = apps.get_model('loan_reconciliation_bridge', 'LoanGLConfiguration')
    
    for config in LoanGLConfiguration.objects.all():
        if config.principal_account and not config.general_loans_receivable_account:
            # Use existing principal_account as the main receivable account
            config.general_loans_receivable_account = config.principal_account
            config.save()
            print(f"Set general_loans_receivable_account for {config.company.name}")


def reverse_populate_general_loans_receivable_account(apps, schema_editor):
    """Reverse operation - clear general_loans_receivable_account"""
    LoanGLConfiguration = apps.get_model('loan_reconciliation_bridge', 'LoanGLConfiguration')
    
    for config in LoanGLConfiguration.objects.all():
        config.general_loans_receivable_account = None
        config.save()


class Migration(migrations.Migration):

    dependencies = [
        ('loan_reconciliation_bridge', '0003_loanglconfiguration_default_interest_percentage_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_general_loans_receivable_account,
            reverse_populate_general_loans_receivable_account
        ),
    ]
