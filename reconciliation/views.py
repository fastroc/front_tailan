from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime

from coa.models import Account
from bank_accounts.models import BankTransaction, UploadedFile
from company.models import Company
from .models import ReconciliationSession, TransactionMatch


@login_required
def dashboard(request):
    """Main reconciliation dashboard showing all accounts and their status from database"""
    company_id = request.session.get('active_company_id')
    
    # Debug: If no company in session, try to get the first company
    if not company_id:
        first_company = Company.objects.first()
        if first_company:
            company_id = first_company.id
            request.session['active_company_id'] = company_id
            messages.info(request, f"Auto-selected company: {first_company.name}")
        else:
            messages.error(request, "No companies found. Please create a company first.")
            # Create a minimal context to prevent template errors
            context = {
                'company': None,
                'accounts': [],
                'total_accounts': 0,
                'total_uploaded_files': 0,
                'total_transactions': 0,
                'total_reconciled': 0,
                'total_unreconciled': 0,
                'total_balance': 0,
                'overall_percentage': 0,
                'recent_activity': [],
                'current_date': datetime.now(),
                'page_title': 'Bank Reconciliation Dashboard - No Companies'
            }
            return render(request, 'reconciliation/dashboard.html', context)
        
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Company not found. Selecting first available company.")
        first_company = Company.objects.first()
        if first_company:
            company = first_company
            request.session['active_company_id'] = first_company.id
        else:
            # Create a minimal context to prevent template errors
            context = {
                'company': None,
                'accounts': [],
                'total_accounts': 0,
                'total_uploaded_files': 0,
                'total_transactions': 0,
                'total_reconciled': 0,
                'total_unreconciled': 0,
                'total_balance': 0,
                'overall_percentage': 0,
                'recent_activity': [],
                'current_date': datetime.now(),
                'page_title': 'Bank Reconciliation Dashboard - No Companies'
            }
            return render(request, 'reconciliation/dashboard.html', context)
    
    # Get all bank accounts for this company from database
    # Use same filtering logic as bank_accounts module
    from django.db.models import Q
    bank_accounts = Account.objects.filter(
        company=company,
        account_type='CURRENT_ASSET'
    ).filter(
        Q(name__icontains='bank') | 
        Q(name__icontains='transactions') | 
        Q(name__icontains='cash') |
        Q(name__icontains='checking') |
        Q(name__icontains='savings')
    ).distinct().order_by('name')
    
    # Prepare real data for each account
    accounts_data = []
    total_uploaded_files = 0
    total_transactions = 0
    total_reconciled = 0
    
    for account in bank_accounts:
        # Get uploaded files for this account
        uploaded_files = UploadedFile.objects.filter(account=account).order_by('-uploaded_at')
        
        # Get transactions for this account
        transactions = BankTransaction.objects.filter(coa_account=account)
        
        # Count reconciled transactions
        reconciled_transactions = transactions.filter(
            id__in=TransactionMatch.objects.filter(
                is_reconciled=True,
                bank_transaction__coa_account=account
            ).values_list('bank_transaction_id', flat=True)
        )
        
        # Get latest reconciliation session
        latest_session = ReconciliationSession.objects.filter(account=account).order_by('-created_at').first()
        
        # Calculate reconciliation progress
        transaction_count = transactions.count()
        reconciled_count = reconciled_transactions.count()
        reconciliation_percentage = 0
        if transaction_count > 0:
            reconciliation_percentage = round((reconciled_count / transaction_count) * 100, 1)
        
        # Calculate account balance
        account_balance = transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Determine status and action
        if transaction_count == 0:
            status = 'empty'
            action = 'upload'
            status_class = 'secondary'
            action_text = 'Upload Transactions'
        elif reconciled_count == 0:
            status = 'ready'
            action = 'reconcile'
            status_class = 'warning'
            action_text = 'Start Reconciliation'
        elif reconciled_count < transaction_count:
            status = 'in_progress' 
            action = 'continue'
            status_class = 'info'
            action_text = 'Continue Reconciliation'
        else:
            status = 'completed'
            action = 'view'
            status_class = 'success'
            action_text = 'View Reconciliation'
        
        # Generate account identifier for URL
        account_identifier = account.name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        if 'anz' in account_identifier:
            account_identifier = 'anz-business'
        elif 'cba' in account_identifier or 'commonwealth' in account_identifier:
            account_identifier = 'cba-savings'
        elif 'westpac' in account_identifier:
            account_identifier = 'westpac-credit'
        elif 'nab' in account_identifier:
            account_identifier = 'nab-term'
        
        account_data = {
            'account': account,
            'account_identifier': account_identifier,
            'account_number': f"***{str(account.id)[-4:]}",  # Mock account number from ID
            'balance': account_balance,
            'uploaded_files': uploaded_files,
            'file_count': uploaded_files.count(),
            'transaction_count': transaction_count,
            'reconciled_count': reconciled_count,
            'unreconciled_count': transaction_count - reconciled_count,
            'reconciliation_percentage': reconciliation_percentage,
            'latest_session': latest_session,
            'status': status,
            'action': action,
            'status_class': status_class,
            'action_text': action_text,
            'recent_files': uploaded_files[:3],  # Show only recent 3 files
            'last_reconciled': latest_session.created_at if latest_session else None
        }
        
        accounts_data.append(account_data)
        
        # Update totals
        total_uploaded_files += uploaded_files.count()
        total_transactions += transaction_count
        total_reconciled += reconciled_count
    
    # Calculate overall statistics
    overall_percentage = 0
    if total_transactions > 0:
        overall_percentage = round((total_reconciled / total_transactions) * 100, 1)
    
    # Recent activity (last 10 reconciliation sessions across all accounts)
    recent_activity = ReconciliationSession.objects.filter(
        account__company=company
    ).order_by('-created_at')[:10]
    
    # Total balance calculation
    total_balance = sum(acc['balance'] for acc in accounts_data)
    
    context = {
        'company': company,
        'accounts': accounts_data,
        'accounts_data': accounts_data,  # Add this for template compatibility
        'total_accounts': bank_accounts.count(),
        'total_uploaded_files': total_uploaded_files,
        'total_transactions': total_transactions,
        'total_reconciled': total_reconciled,
        'total_unreconciled': total_transactions - total_reconciled,
        'total_balance': total_balance,
        'overall_percentage': overall_percentage,
        'recent_activity': recent_activity,
        'current_date': datetime.now(),
        'page_title': 'Bank Reconciliation Dashboard'
    }
    
    return render(request, 'reconciliation/dashboard.html', context)


@login_required
def account_reconciliation(request, account_id):
    """Enhanced reconciliation process page for a specific account"""
    company_id = request.session.get('active_company_id')
    if not company_id:
        # Auto-select first company
        first_company = Company.objects.first()
        if first_company:
            company_id = first_company.id
            request.session['active_company_id'] = company_id
        else:
            messages.error(request, "Please select a company first.")
            return redirect('reconciliation:dashboard')
        
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Company not found.")
        return redirect('reconciliation:dashboard')
    
    # Get the actual account from database
    try:
        if isinstance(account_id, str) and account_id.isdigit():
            account_id = int(account_id)
            # Use same filtering logic as dashboard
            from django.db.models import Q
            account = get_object_or_404(
                Account.objects.filter(
                    company=company,
                    account_type='CURRENT_ASSET'
                ).filter(
                    Q(name__icontains='bank') | 
                    Q(name__icontains='transactions') | 
                    Q(name__icontains='cash') |
                    Q(name__icontains='checking') |
                    Q(name__icontains='savings')
                ), 
                id=account_id
            )
        else:
            # Handle string account identifiers by finding the account
            bank_accounts = Account.objects.filter(
                company=company,
                account_type='CURRENT_ASSET'
            ).filter(
                Q(name__icontains='bank') | 
                Q(name__icontains='transactions') | 
                Q(name__icontains='cash') |
                Q(name__icontains='checking') |
                Q(name__icontains='savings')
            ).distinct()
            
            # Map common identifiers
            account_map = {}
            for acc in bank_accounts:
                name_lower = acc.name.lower()
                if 'khan' in name_lower:
                    account_map['khanbank'] = acc
                elif 'golomt' in name_lower:
                    account_map['golomtbank'] = acc
                elif 'golomt' in name_lower:
                    account_map['golomt-bank'] = acc
                    
            account = account_map.get(str(account_id).lower())
            if not account:
                # Fallback to first bank account
                account = bank_accounts.first()
                
            if not account:
                messages.error(request, "Bank account not found.")
                return redirect('reconciliation:dashboard')
                
    except Exception as e:
        messages.error(request, f"Error finding account: {str(e)}")
        return redirect('reconciliation:dashboard')
    
    # Import reconciliation service
    from .reconciliation_service import ReconciliationService
    
    # Get or create reconciliation session
    reconciliation_session = ReconciliationService.get_or_create_session(account, request.user)
    
    # Get unmatched transactions for this account  
    unmatched_transactions = ReconciliationService.get_unmatched_transactions(account)
    
    # Convert to list to ensure template can iterate
    transactions_list = list(unmatched_transactions)
    
    # Get matched transactions for editing (ordered by transaction date - oldest first)
    matched_transactions = TransactionMatch.objects.filter(
        bank_transaction__coa_account=account,
        is_reconciled=True
    ).select_related(
        'bank_transaction', 'gl_account', 'reconciliation_session'
    ).order_by('bank_transaction__date')
    
    # Get reconciliation progress
    progress = ReconciliationService.get_reconciliation_progress(account)
    
    # Get Chart of Accounts for dropdown
    coa_accounts = Account.objects.filter(company=company).exclude(account_type='Bank').order_by('code', 'name')
    
    # Group COA by account type for better UX
    coa_groups = {}
    for acc in coa_accounts:
        account_type = acc.get_account_type_display() if hasattr(acc, 'get_account_type_display') else acc.account_type
        if account_type not in coa_groups:
            coa_groups[account_type] = []
        coa_groups[account_type].append(acc)
    
    # Sample contacts for autocomplete (can be enhanced later)
    sample_contacts = [
        'TechCorp Consulting', 'Office Landlord', 'Telstra Business', 'ATO', 
        'Staff Payroll', 'Equipment Supplier', 'Marketing Agency', 'Legal Services',
        'Insurance Company', 'Bank Fees', 'Interest Payment', 'Loan Repayment'
    ]
    
    # Tax rates
    tax_rates = [
        {'id': 'gst_10', 'name': 'GST 10%'},
        {'id': 'gst_free', 'name': 'GST Free'},
        {'id': 'input_taxed', 'name': 'Input Taxed'},
        {'id': 'no_gst', 'name': 'No GST'}
    ]
    
    context = {
        'company': company,
        'account': account,
        'account_id': account_id,
        'account_name': account.name,
        'reconciliation_session': reconciliation_session,
        'transactions': transactions_list,  # Use the list instead of queryset
        'matched_transactions': matched_transactions,  # Add matched transactions
        'progress': progress,
        'coa_groups': coa_groups,
        'contacts': sample_contacts,
        'tax_rates': tax_rates,
        'total_transactions': progress['total_transactions'],
        'matched_count': progress['matched_transactions'],
        'unmatched_transactions': progress['unmatched_transactions'],
        'reconciliation_percentage': progress['percentage'],
        'statement_balance': progress.get('statement_balance', 0.00),
        'reconciled_balance': progress.get('reconciled_balance', 0.00),
        'balance_difference': progress.get('difference', 0.00),
        'title': f'Bank Reconciliation - {account.name}'
    }
    
    return render(request, 'reconciliation/reconciliation_process.html', context)
    
    # Sample transactions data for demo - 20+ realistic Australian business transactions
    sample_transactions = [
        {
            'id': 1,
            'date': '2024-09-08',
            'description': 'Professional Services - Web Development',
            'reference': 'INV-2024-001',
            'memo': 'Monthly web development services',
            'amount': 1250.00
        },
        {
            'id': 2, 
            'date': '2024-09-07',
            'description': 'Office Supplies - Officeworks',
            'reference': 'EFTPOS-789',
            'memo': 'Stationery and equipment',
            'amount': -89.50
        },
        {
            'id': 3,
            'date': '2024-09-06', 
            'description': 'Bank Transfer - Client Payment',
            'reference': 'TXN-456123',
            'memo': 'Payment from Acme Corp',
            'amount': 2850.00
        },
        {
            'id': 4,
            'date': '2024-09-05',
            'description': 'Telstra Business Plan',
            'reference': 'DD-TEL-001',
            'memo': 'Monthly internet and phone',
            'amount': -145.90
        },
        {
            'id': 5,
            'date': '2024-09-04',
            'description': 'Fuel - BP Service Station',
            'reference': 'CARD-4521',
            'memo': 'Vehicle fuel expenses',
            'amount': -95.40
        },
        {
            'id': 6,
            'date': '2024-09-03',
            'description': 'Software License - Microsoft',
            'reference': 'SUB-MS-365',
            'memo': 'Office 365 Business Premium',
            'amount': -28.50
        },
        {
            'id': 7,
            'date': '2024-09-02',
            'description': 'Consulting Revenue - TechCorp',
            'reference': 'INV-2024-002',
            'memo': 'IT consulting project milestone',
            'amount': 3200.00
        },
        {
            'id': 8,
            'date': '2024-09-01',
            'description': 'Coffee Meeting - Expense',
            'reference': 'CARD-8901',
            'memo': 'Client meeting at Starbucks',
            'amount': -45.80
        },
        {
            'id': 9,
            'date': '2024-08-31',
            'description': 'Equipment Purchase - Harvey Norman',
            'reference': 'INV-HN-7890',
            'memo': 'New laptop and accessories',
            'amount': -1899.00
        },
        {
            'id': 10,
            'date': '2024-08-30',
            'description': 'Bank Interest Earned',
            'reference': 'INT-AUG-2024',
            'memo': 'Monthly interest on savings',
            'amount': 12.35
        },
        {
            'id': 11,
            'date': '2024-08-29',
            'description': 'Professional Services - Legal Advice',
            'reference': 'INV-LAW-456',
            'memo': 'Contract review and advice',
            'amount': -520.00
        },
        {
            'id': 12,
            'date': '2024-08-28',
            'description': 'Client Payment - Global Systems',
            'reference': 'TXN-GS-789',
            'memo': 'Web design project completion',
            'amount': 4500.00
        },
        {
            'id': 13,
            'date': '2024-08-27',
            'description': 'Marketing - Google Ads',
            'reference': 'ADS-GOOGLE-08',
            'memo': 'Monthly advertising spend',
            'amount': -750.00
        },
        {
            'id': 14,
            'date': '2024-08-26',
            'description': 'Insurance Premium - Business',
            'reference': 'POL-BUS-2024',
            'memo': 'Professional indemnity insurance',
            'amount': -285.60
        },
        {
            'id': 15,
            'date': '2024-08-25',
            'description': 'Travel - Domestic Flight',
            'reference': 'JETSTAR-JQ456',
            'memo': 'Business trip to Melbourne',
            'amount': -320.00
        },
        {
            'id': 16,
            'date': '2024-08-24',
            'description': 'Recurring Income - Subscription',
            'reference': 'SUB-MONTHLY-16',
            'memo': 'Monthly software subscription revenue',
            'amount': 899.00
        },
        {
            'id': 17,
            'date': '2024-08-23',
            'description': 'Office Rent - Monthly',
            'reference': 'RENT-AUG-2024',
            'memo': 'Shared office space rental',
            'amount': -650.00
        },
        {
            'id': 18,
            'date': '2024-08-22',
            'description': 'Accounting Software - Xero',
            'reference': 'SUB-XERO-AUG',
            'memo': 'Monthly accounting software',
            'amount': -62.00
        },
        {
            'id': 19,
            'date': '2024-08-21',
            'description': 'Bank Fees - Transaction Charges',
            'reference': 'FEE-TXN-AUG',
            'memo': 'Monthly account maintenance',
            'amount': -15.00
        },
        {
            'id': 20,
            'date': '2024-08-20',
            'description': 'Training Course - Online',
            'reference': 'COURSE-TECH-2024',
            'memo': 'Professional development course',
            'amount': -395.00
        },
        {
            'id': 21,
            'date': '2024-08-19',
            'description': 'Client Refund - Digital Agency',
            'reference': 'REF-DA-001',
            'memo': 'Partial refund for project changes',
            'amount': -180.00
        },
        {
            'id': 22,
            'date': '2024-08-18',
            'description': 'Equipment Lease - Printer',
            'reference': 'LEASE-CANON-08',
            'memo': 'Monthly printer lease payment',
            'amount': -89.00
        },
        {
            'id': 23,
            'date': '2024-08-17',
            'description': 'Web Hosting - Annual Payment',
            'reference': 'HOST-ANNUAL-2024',
            'memo': 'Web hosting and domain renewal',
            'amount': -450.00
        },
        {
            'id': 24,
            'date': '2024-08-16',
            'description': 'Freelancer Payment - Design Work',
            'reference': 'PAY-FREELANCE-16',
            'memo': 'Logo design and branding',
            'amount': -980.00
        },
        {
            'id': 25,
            'date': '2024-08-15',
            'description': 'Large Project Payment - Enterprise Client',
            'reference': 'INV-ENT-2024-003',
            'memo': 'Enterprise system development - Phase 1',
            'amount': 15750.00
        }
    ]
    
    # Sample contacts - expanded list
    sample_contacts = [
        {'id': 1, 'name': 'Acme Corporation'},
        {'id': 2, 'name': 'Tech Solutions Ltd'}, 
        {'id': 3, 'name': 'Global Systems Inc'},
        {'id': 4, 'name': 'Digital Agency Pro'},
        {'id': 5, 'name': 'Officeworks'},
        {'id': 6, 'name': 'TechCorp Consulting'},
        {'id': 7, 'name': 'Harvey Norman'},
        {'id': 8, 'name': 'Telstra Business'},
        {'id': 9, 'name': 'Microsoft Australia'},
        {'id': 10, 'name': 'Google Australia'},
        {'id': 11, 'name': 'Starbucks Coffee'},
        {'id': 12, 'name': 'BP Australia'},
        {'id': 13, 'name': 'Jetstar Airways'},
        {'id': 14, 'name': 'Xero Australia'},
        {'id': 15, 'name': 'Legal Partners Pty Ltd'},
        {'id': 16, 'name': 'Business Insurance Co'},
        {'id': 17, 'name': 'Office Space Solutions'},
        {'id': 18, 'name': 'Canon Australia'},
        {'id': 19, 'name': 'Web Host Pro'},
        {'id': 20, 'name': 'Creative Freelancers'}
    ]
    
    # Sample Chart of Accounts grouped - expanded for diverse transactions
    sample_coa_groups = {
        'Revenue': [
            {'code': '4100', 'name': 'Professional Services Income'},
            {'code': '4200', 'name': 'Consulting Revenue'},
            {'code': '4300', 'name': 'Web Development Income'},
            {'code': '4400', 'name': 'Software Subscription Revenue'},
            {'code': '4900', 'name': 'Other Income'}
        ],
        'Expenses': [
            {'code': '6100', 'name': 'Office Supplies'},
            {'code': '6200', 'name': 'Professional Fees'},
            {'code': '6300', 'name': 'General Expenses'},
            {'code': '6400', 'name': 'Telecommunications'},
            {'code': '6500', 'name': 'Motor Vehicle Expenses'},
            {'code': '6600', 'name': 'Software & Licenses'},
            {'code': '6700', 'name': 'Travel & Accommodation'},
            {'code': '6800', 'name': 'Advertising & Marketing'},
            {'code': '6810', 'name': 'Insurance'},
            {'code': '6820', 'name': 'Rent & Utilities'},
            {'code': '6830', 'name': 'Training & Development'},
            {'code': '6840', 'name': 'Equipment Lease'},
            {'code': '6850', 'name': 'Web Hosting & Domain'},
            {'code': '6860', 'name': 'Contractor Payments'},
            {'code': '6900', 'name': 'Bank Fees'}
        ],
        'Assets': [
            {'code': '1100', 'name': 'Bank Account - ANZ'},
            {'code': '1110', 'name': 'Bank Account - CBA'},
            {'code': '1120', 'name': 'Bank Account - Westpac'},
            {'code': '1200', 'name': 'Accounts Receivable'},
            {'code': '1600', 'name': 'Office Equipment'},
            {'code': '1650', 'name': 'Computer Equipment'}
        ],
        'Liabilities': [
            {'code': '2100', 'name': 'Accounts Payable'},
            {'code': '2200', 'name': 'Credit Card - Westpac'},
            {'code': '2300', 'name': 'Accrued Expenses'}
        ]
    }
    
    # Sample tax rates
    sample_tax_rates = [
        {'id': 1, 'name': 'GST 10%'},
        {'id': 2, 'name': 'GST Free'}, 
        {'id': 3, 'name': 'Input Taxed'}
    ]
    
    context = {
        'company': company,
        'account': account,
        'account_id': account_id,
        'account_name': account.name,
        'reconciliation_session': reconciliation_session,
        'transactions': unmatched_transactions,
        'progress': progress,
        'coa_groups': coa_groups,
        'contacts': sample_contacts,
        'tax_rates': tax_rates,
        'total_transactions': progress['total_transactions'],
        'matched_transactions': progress['matched_transactions'],
        'unmatched_transactions': progress['unmatched_transactions'],
        'reconciliation_percentage': progress['percentage'],
        'statement_balance': progress.get('statement_balance', 0.00),
        'system_balance': progress.get('system_balance', 0.00),
        'title': f'Bank Reconciliation - {account.name}'
    }
    
    return render(request, 'reconciliation/reconciliation_process.html', context)
