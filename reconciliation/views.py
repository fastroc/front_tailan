from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from datetime import datetime

from coa.models import Account
from bank_accounts.models import BankTransaction, UploadedFile
from company.models import Company
from .models import ReconciliationSession, TransactionMatch


# @login_required  # Temporarily disabled for testing
def dashboard(request):
    """Main reconciliation dashboard showing all accounts and their status from database"""
    company_id = request.session.get("active_company_id")

    # Debug: If no company in session, try to get the first company
    if not company_id:
        first_company = Company.objects.first()
        if first_company:
            company_id = first_company.id
            request.session["active_company_id"] = company_id
            messages.info(request, f"Auto-selected company: {first_company.name}")
        else:
            messages.error(
                request, "No companies found. Please create a company first."
            )
            # Create a minimal context to prevent template errors
            context = {
                "company": None,
                "accounts": [],
                "total_accounts": 0,
                "total_uploaded_files": 0,
                "total_transactions": 0,
                "total_reconciled": 0,
                "total_unreconciled": 0,
                "total_balance": 0,
                "overall_percentage": 0,
                "recent_activity": [],
                "current_date": datetime.now(),
                "page_title": "Bank Reconciliation Dashboard - No Companies",
            }
            return render(request, "reconciliation/dashboard.html", context)

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Company not found. Selecting first available company.")
        first_company = Company.objects.first()
        if first_company:
            company = first_company
            request.session["active_company_id"] = first_company.id
        else:
            # Create a minimal context to prevent template errors
            context = {
                "company": None,
                "accounts": [],
                "total_accounts": 0,
                "total_uploaded_files": 0,
                "total_transactions": 0,
                "total_reconciled": 0,
                "total_unreconciled": 0,
                "total_balance": 0,
                "overall_percentage": 0,
                "recent_activity": [],
                "current_date": datetime.now(),
                "page_title": "Bank Reconciliation Dashboard - No Companies",
            }
            return render(request, "reconciliation/dashboard.html", context)

    # Get all bank accounts for this company from database
    # Show only accounts marked as bank accounts
    bank_accounts = Account.objects.filter(
        company=company, is_bank_account=True, is_active=True
    ).order_by("name")

    # Prepare real data for each account
    accounts_data = []
    total_uploaded_files = 0
    total_transactions = 0
    total_reconciled = 0

    for account in bank_accounts:
        # Get uploaded files for this account
        uploaded_files = UploadedFile.objects.filter(account=account).order_by(
            "-uploaded_at"
        )

        # Get transactions for this account
        transactions = BankTransaction.objects.filter(coa_account=account)

        # Count reconciled transactions
        reconciled_transactions = transactions.filter(
            id__in=TransactionMatch.objects.filter(
                is_reconciled=True, bank_transaction__coa_account=account
            ).values_list("bank_transaction_id", flat=True)
        )

        # Get latest reconciliation session
        latest_session = (
            ReconciliationSession.objects.filter(account=account)
            .order_by("-created_at")
            .first()
        )

        # Calculate reconciliation progress
        transaction_count = transactions.count()
        reconciled_count = reconciled_transactions.count()
        reconciliation_percentage = 0
        if transaction_count > 0:
            reconciliation_percentage = round(
                (reconciled_count / transaction_count) * 100, 1
            )

        # Calculate account balance
        account_balance = transactions.aggregate(total=Sum("amount"))["total"] or 0

        # Determine status and action
        if transaction_count == 0:
            status = "empty"
            action = "upload"
            status_class = "secondary"
            action_text = "Upload Transactions"
        elif reconciled_count == 0:
            status = "ready"
            action = "reconcile"
            status_class = "warning"
            action_text = "Start Reconciliation"
        elif reconciled_count < transaction_count:
            status = "in_progress"
            action = "continue"
            status_class = "info"
            action_text = "Continue Reconciliation"
        else:
            status = "completed"
            action = "view"
            status_class = "success"
            action_text = "View Reconciliation"

        # Generate account identifier for URL
        account_identifier = (
            account.name.lower().replace(" ", "-").replace("(", "").replace(")", "")
        )
        if "anz" in account_identifier:
            account_identifier = "anz-business"
        elif "cba" in account_identifier or "commonwealth" in account_identifier:
            account_identifier = "cba-savings"
        elif "westpac" in account_identifier:
            account_identifier = "westpac-credit"
        elif "nab" in account_identifier:
            account_identifier = "nab-term"

        account_data = {
            "account": account,
            "account_identifier": account_identifier,
            "account_number": f"***{str(account.id)[-4:]}",  # Mock account number from ID
            "balance": account_balance,
            "uploaded_files": uploaded_files,
            "file_count": uploaded_files.count(),
            "transaction_count": transaction_count,
            "reconciled_count": reconciled_count,
            "unreconciled_count": transaction_count - reconciled_count,
            "reconciliation_percentage": reconciliation_percentage,
            "latest_session": latest_session,
            "status": status,
            "action": action,
            "status_class": status_class,
            "action_text": action_text,
            "recent_files": uploaded_files[:3],  # Show only recent 3 files
            "last_reconciled": latest_session.created_at if latest_session else None,
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
    ).order_by("-created_at")[:10]

    # Total balance calculation
    total_balance = sum(acc["balance"] for acc in accounts_data)

    context = {
        "company": company,
        "accounts": accounts_data,
        "accounts_data": accounts_data,  # Add this for template compatibility
        "total_accounts": bank_accounts.count(),
        "total_uploaded_files": total_uploaded_files,
        "total_transactions": total_transactions,
        "total_reconciled": total_reconciled,
        "total_unreconciled": total_transactions - total_reconciled,
        "total_balance": total_balance,
        "overall_percentage": overall_percentage,
        "recent_activity": recent_activity,
        "current_date": datetime.now(),
        "page_title": "Bank Reconciliation Dashboard",
    }

    return render(request, "reconciliation/dashboard.html", context)


# @login_required  # Temporarily disabled for testing
def account_reconciliation(request, account_id):
    """Enhanced reconciliation process page for a specific account"""

    # First, try to find the account to determine its company
    try:
        if isinstance(account_id, str) and account_id.isdigit():
            account_id = int(account_id)

        # Find the account regardless of company to get its company
        target_account = Account.objects.filter(
            id=account_id, account_type="CURRENT_ASSET"
        ).first()

        if target_account and target_account.company:
            # Set the session to use the account's company
            company_id = target_account.company.id
            request.session["active_company_id"] = company_id
            company = target_account.company
            # Try to add message, but don't fail if messages middleware not available
            try:
                messages.info(
                    request,
                    f"Auto-selected company: {company.name} for account {target_account.name}",
                )
            except:
                pass  # Silent fail for testing without messages middleware
        else:
            # Fallback to session company or first company
            company_id = request.session.get("active_company_id")
            if not company_id:
                first_company = Company.objects.first()
                if first_company:
                    company_id = first_company.id
                    request.session["active_company_id"] = company_id
                    company = first_company
                else:
                    messages.error(request, "Please select a company first.")
                    return redirect("reconciliation:dashboard")
            else:
                try:
                    company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    try:
                        messages.error(request, "Company not found.")
                    except:
                        pass  # Silent fail for testing
                    return redirect("reconciliation:dashboard")

    except Exception as e:
        try:
            messages.error(request, f"Error finding account: {e}")
        except:
            pass  # Silent fail for testing
        return redirect("reconciliation:dashboard")

    # Get the actual account from database
    try:
        if isinstance(account_id, (int, str)) and str(account_id).isdigit():
            account_id = int(account_id)
            # Show only accounts marked as bank accounts
            account = get_object_or_404(
                Account.objects.filter(company=company, is_bank_account=True),
                id=account_id,
            )
        else:
            # Map existing bank accounts only
            bank_accounts = Account.objects.filter(
                company=company, is_bank_account=True
            )

            # Map common identifiers
            account_map = {}
            for acc in bank_accounts:
                name_lower = acc.name.lower()
                if "khan" in name_lower:
                    account_map["khanbank"] = acc
                elif "golomt" in name_lower:
                    account_map["golomtbank"] = acc
                elif "golomt" in name_lower:
                    account_map["golomt-bank"] = acc

            account = account_map.get(str(account_id).lower())
            if not account:
                # Fallback to first bank account
                account = bank_accounts.first()

            if not account:
                messages.error(request, "Bank account not found.")
                return redirect("reconciliation:dashboard")

    except Exception as e:
        messages.error(request, f"Error finding account: {str(e)}")
        return redirect("reconciliation:dashboard")

    # Import reconciliation service
    from .reconciliation_service import ReconciliationService

    # Get or create reconciliation session
    # Handle case where user is not authenticated (for testing)
    user = request.user if request.user.is_authenticated else None
    reconciliation_session = ReconciliationService.get_or_create_session(account, user)

    # Get unmatched transactions for this account
    unmatched_transactions = ReconciliationService.get_unmatched_transactions(account)

    # Convert to list to ensure template can iterate
    transactions_list = list(unmatched_transactions)

    # Get matched transactions for editing (ordered by transaction date - oldest first)
    matched_transactions = (
        TransactionMatch.objects.filter(
            bank_transaction__coa_account=account, is_reconciled=True
        )
        .select_related("bank_transaction", "gl_account", "reconciliation_session")
        .order_by("bank_transaction__date")
    )

    # Get reconciliation progress
    progress = ReconciliationService.get_reconciliation_progress(account)

    # Get Chart of Accounts for dropdown
    coa_accounts = (
        Account.objects.filter(company=company)
        .exclude(account_type="Bank")
        .order_by("code", "name")
    )

    # Group COA by account type for better UX
    coa_groups = {}
    for acc in coa_accounts:
        account_type = (
            acc.get_account_type_display()
            if hasattr(acc, "get_account_type_display")
            else acc.account_type
        )
        if account_type not in coa_groups:
            coa_groups[account_type] = []
        coa_groups[account_type].append(acc)

    # Sample contacts for autocomplete (can be enhanced later)
    sample_contacts = [
        "TechCorp Consulting",
        "Office Landlord",
        "Telstra Business",
        "ATO",
        "Staff Payroll",
        "Equipment Supplier",
        "Marketing Agency",
        "Legal Services",
        "Insurance Company",
        "Bank Fees",
        "Interest Payment",
        "Loan Repayment",
    ]

    # Tax rates
    tax_rates = [
        {"id": "gst_10", "name": "GST 10%"},
        {"id": "gst_free", "name": "GST Free"},
        {"id": "input_taxed", "name": "Input Taxed"},
        {"id": "no_gst", "name": "No GST"},
    ]

    context = {
        "company": company,
        "account": account,
        "account_id": account_id,
        "account_name": account.name,
        "reconciliation_session": reconciliation_session,
        "transactions": transactions_list,  # Use the list instead of queryset
        "matched_transactions": matched_transactions,  # Add matched transactions
        "progress": progress,
        "coa_groups": coa_groups,
        "contacts": sample_contacts,
        "tax_rates": tax_rates,
        "total_transactions": progress["total_transactions"],
        "matched_count": progress["matched_transactions"],
        "unmatched_transactions": progress["unmatched_transactions"],
        "reconciliation_percentage": progress["percentage"],
        "statement_balance": progress.get("statement_balance", 0.00),
        "reconciled_balance": progress.get("reconciled_balance", 0.00),
        "balance_difference": progress.get("difference", 0.00),
        "title": f"Bank Reconciliation - {account.name}",
    }

    return render(request, "reconciliation/reconciliation_process.html", context)

    # Sample transactions data for demo - 20+ realistic Australian business transactions
    sample_transactions = [
        {
            "id": 1,
            "date": "2024-09-08",
            "description": "Professional Services - Web Development",
            "reference": "INV-2024-001",
            "memo": "Monthly web development services",
            "amount": 1250.00,
        },
        {
            "id": 2,
            "date": "2024-09-07",
            "description": "Office Supplies - Officeworks",
            "reference": "EFTPOS-789",
            "memo": "Stationery and equipment",
            "amount": -89.50,
        },
        {
            "id": 3,
            "date": "2024-09-06",
            "description": "Bank Transfer - Client Payment",
            "reference": "TXN-456123",
            "memo": "Payment from Acme Corp",
            "amount": 2850.00,
        },
        {
            "id": 4,
            "date": "2024-09-05",
            "description": "Telstra Business Plan",
            "reference": "DD-TEL-001",
            "memo": "Monthly internet and phone",
            "amount": -145.90,
        },
        {
            "id": 5,
            "date": "2024-09-04",
            "description": "Fuel - BP Service Station",
            "reference": "CARD-4521",
            "memo": "Vehicle fuel expenses",
            "amount": -95.40,
        },
        {
            "id": 6,
            "date": "2024-09-03",
            "description": "Software License - Microsoft",
            "reference": "SUB-MS-365",
            "memo": "Office 365 Business Premium",
            "amount": -28.50,
        },
        {
            "id": 7,
            "date": "2024-09-02",
            "description": "Consulting Revenue - TechCorp",
            "reference": "INV-2024-002",
            "memo": "IT consulting project milestone",
            "amount": 3200.00,
        },
        {
            "id": 8,
            "date": "2024-09-01",
            "description": "Coffee Meeting - Expense",
            "reference": "CARD-8901",
            "memo": "Client meeting at Starbucks",
            "amount": -45.80,
        },
        {
            "id": 9,
            "date": "2024-08-31",
            "description": "Equipment Purchase - Harvey Norman",
            "reference": "INV-HN-7890",
            "memo": "New laptop and accessories",
            "amount": -1899.00,
        },
        {
            "id": 10,
            "date": "2024-08-30",
            "description": "Bank Interest Earned",
            "reference": "INT-AUG-2024",
            "memo": "Monthly interest on savings",
            "amount": 12.35,
        },
        {
            "id": 11,
            "date": "2024-08-29",
            "description": "Professional Services - Legal Advice",
            "reference": "INV-LAW-456",
            "memo": "Contract review and advice",
            "amount": -520.00,
        },
        {
            "id": 12,
            "date": "2024-08-28",
            "description": "Client Payment - Global Systems",
            "reference": "TXN-GS-789",
            "memo": "Web design project completion",
            "amount": 4500.00,
        },
        {
            "id": 13,
            "date": "2024-08-27",
            "description": "Marketing - Google Ads",
            "reference": "ADS-GOOGLE-08",
            "memo": "Monthly advertising spend",
            "amount": -750.00,
        },
        {
            "id": 14,
            "date": "2024-08-26",
            "description": "Insurance Premium - Business",
            "reference": "POL-BUS-2024",
            "memo": "Professional indemnity insurance",
            "amount": -285.60,
        },
        {
            "id": 15,
            "date": "2024-08-25",
            "description": "Travel - Domestic Flight",
            "reference": "JETSTAR-JQ456",
            "memo": "Business trip to Melbourne",
            "amount": -320.00,
        },
        {
            "id": 16,
            "date": "2024-08-24",
            "description": "Recurring Income - Subscription",
            "reference": "SUB-MONTHLY-16",
            "memo": "Monthly software subscription revenue",
            "amount": 899.00,
        },
        {
            "id": 17,
            "date": "2024-08-23",
            "description": "Office Rent - Monthly",
            "reference": "RENT-AUG-2024",
            "memo": "Shared office space rental",
            "amount": -650.00,
        },
        {
            "id": 18,
            "date": "2024-08-22",
            "description": "Accounting Software - Xero",
            "reference": "SUB-XERO-AUG",
            "memo": "Monthly accounting software",
            "amount": -62.00,
        },
        {
            "id": 19,
            "date": "2024-08-21",
            "description": "Bank Fees - Transaction Charges",
            "reference": "FEE-TXN-AUG",
            "memo": "Monthly account maintenance",
            "amount": -15.00,
        },
        {
            "id": 20,
            "date": "2024-08-20",
            "description": "Training Course - Online",
            "reference": "COURSE-TECH-2024",
            "memo": "Professional development course",
            "amount": -395.00,
        },
        {
            "id": 21,
            "date": "2024-08-19",
            "description": "Client Refund - Digital Agency",
            "reference": "REF-DA-001",
            "memo": "Partial refund for project changes",
            "amount": -180.00,
        },
        {
            "id": 22,
            "date": "2024-08-18",
            "description": "Equipment Lease - Printer",
            "reference": "LEASE-CANON-08",
            "memo": "Monthly printer lease payment",
            "amount": -89.00,
        },
        {
            "id": 23,
            "date": "2024-08-17",
            "description": "Web Hosting - Annual Payment",
            "reference": "HOST-ANNUAL-2024",
            "memo": "Web hosting and domain renewal",
            "amount": -450.00,
        },
        {
            "id": 24,
            "date": "2024-08-16",
            "description": "Freelancer Payment - Design Work",
            "reference": "PAY-FREELANCE-16",
            "memo": "Logo design and branding",
            "amount": -980.00,
        },
        {
            "id": 25,
            "date": "2024-08-15",
            "description": "Large Project Payment - Enterprise Client",
            "reference": "INV-ENT-2024-003",
            "memo": "Enterprise system development - Phase 1",
            "amount": 15750.00,
        },
    ]

    # Sample contacts - expanded list
    sample_contacts = [
        {"id": 1, "name": "Acme Corporation"},
        {"id": 2, "name": "Tech Solutions Ltd"},
        {"id": 3, "name": "Global Systems Inc"},
        {"id": 4, "name": "Digital Agency Pro"},
        {"id": 5, "name": "Officeworks"},
        {"id": 6, "name": "TechCorp Consulting"},
        {"id": 7, "name": "Harvey Norman"},
        {"id": 8, "name": "Telstra Business"},
        {"id": 9, "name": "Microsoft Australia"},
        {"id": 10, "name": "Google Australia"},
        {"id": 11, "name": "Starbucks Coffee"},
        {"id": 12, "name": "BP Australia"},
        {"id": 13, "name": "Jetstar Airways"},
        {"id": 14, "name": "Xero Australia"},
        {"id": 15, "name": "Legal Partners Pty Ltd"},
        {"id": 16, "name": "Business Insurance Co"},
        {"id": 17, "name": "Office Space Solutions"},
        {"id": 18, "name": "Canon Australia"},
        {"id": 19, "name": "Web Host Pro"},
        {"id": 20, "name": "Creative Freelancers"},
    ]

    # Sample Chart of Accounts grouped - expanded for diverse transactions
    sample_coa_groups = {
        "Revenue": [
            {"code": "4100", "name": "Professional Services Income"},
            {"code": "4200", "name": "Consulting Revenue"},
            {"code": "4300", "name": "Web Development Income"},
            {"code": "4400", "name": "Software Subscription Revenue"},
            {"code": "4900", "name": "Other Income"},
        ],
        "Expenses": [
            {"code": "6100", "name": "Office Supplies"},
            {"code": "6200", "name": "Professional Fees"},
            {"code": "6300", "name": "General Expenses"},
            {"code": "6400", "name": "Telecommunications"},
            {"code": "6500", "name": "Motor Vehicle Expenses"},
            {"code": "6600", "name": "Software & Licenses"},
            {"code": "6700", "name": "Travel & Accommodation"},
            {"code": "6800", "name": "Advertising & Marketing"},
            {"code": "6810", "name": "Insurance"},
            {"code": "6820", "name": "Rent & Utilities"},
            {"code": "6830", "name": "Training & Development"},
            {"code": "6840", "name": "Equipment Lease"},
            {"code": "6850", "name": "Web Hosting & Domain"},
            {"code": "6860", "name": "Contractor Payments"},
            {"code": "6900", "name": "Bank Fees"},
        ],
        "Assets": [
            {"code": "1100", "name": "Bank Account - ANZ"},
            {"code": "1110", "name": "Bank Account - CBA"},
            {"code": "1120", "name": "Bank Account - Westpac"},
            {"code": "1200", "name": "Accounts Receivable"},
            {"code": "1600", "name": "Office Equipment"},
            {"code": "1650", "name": "Computer Equipment"},
        ],
        "Liabilities": [
            {"code": "2100", "name": "Accounts Payable"},
            {"code": "2200", "name": "Credit Card - Westpac"},
            {"code": "2300", "name": "Accrued Expenses"},
        ],
    }

    # Sample tax rates
    sample_tax_rates = [
        {"id": 1, "name": "GST 10%"},
        {"id": 2, "name": "GST Free"},
        {"id": 3, "name": "Input Taxed"},
    ]

    context = {
        "company": company,
        "account": account,
        "account_id": account_id,
        "account_name": account.name,
        "reconciliation_session": reconciliation_session,
        "transactions": unmatched_transactions,
        "progress": progress,
        "coa_groups": coa_groups,
        "contacts": sample_contacts,
        "tax_rates": tax_rates,
        "total_transactions": progress["total_transactions"],
        "matched_transactions": progress["matched_transactions"],
        "unmatched_transactions": progress["unmatched_transactions"],
        "reconciliation_percentage": progress["percentage"],
        "statement_balance": progress.get("statement_balance", 0.00),
        "system_balance": progress.get("system_balance", 0.00),
        "title": f"Bank Reconciliation - {account.name}",
    }

    return render(request, "reconciliation/reconciliation_process.html", context)


# @login_required  # Temporarily disabled for testing
def account_reconciliation_simple(request, account_id):
    """Simple, minimal reconciliation interface with core functionality only"""

    # Get company (reuse existing logic)
    company_id = request.session.get("active_company_id")
    if not company_id:
        first_company = Company.objects.first()
        if first_company:
            company_id = first_company.id
            request.session["active_company_id"] = company_id
            company = first_company
        else:
            messages.error(request, "Please select a company first.")
            return redirect("reconciliation:dashboard")
    else:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            messages.error(request, "Company not found.")
            return redirect("reconciliation:dashboard")

    # Get the account
    try:
        account = get_object_or_404(
            Account.objects.filter(company=company, is_bank_account=True), id=account_id
        )
    except Account.DoesNotExist:
        messages.error(request, "Bank account not found.")
        return redirect("reconciliation:dashboard")

    # Import reconciliation service
    from .reconciliation_service import ReconciliationService

    # 🚀 PERFORMANCE OPTIMIZATION #3: Add pagination (load 100 transactions at a time)
    # Get page number from request (default to 1)
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    
    # Get optional file_id for filtering transactions from specific upload
    file_id = request.GET.get('file_id', None)
    filtered_by_file = None
    uploaded_filename = None
    if file_id:
        try:
            filtered_by_file = UploadedFile.objects.get(id=int(file_id), account=account)
            uploaded_filename = filtered_by_file.stored_filename  # Get the stored filename for filtering
        except (UploadedFile.DoesNotExist, ValueError):
            messages.warning(request, "Upload file not found. Showing all transactions.")
            file_id = None
    
    transactions_per_page = 100
    offset = (page - 1) * transactions_per_page
    
    # Get unmatched transactions with limit for pagination and optional file filter
    all_unmatched = ReconciliationService.get_unmatched_transactions(account, uploaded_file_id=uploaded_filename)
    total_transactions = all_unmatched.count()
    
    # Apply pagination
    unmatched_transactions = all_unmatched[offset:offset + transactions_per_page]
    
    # Calculate pagination info
    total_pages = (total_transactions + transactions_per_page - 1) // transactions_per_page
    has_next = page < total_pages
    has_previous = page > 1

    # 🚀 PERFORMANCE OPTIMIZATION #1: Initialize services once (not per transaction)
    from reconciliation.smart_suggestion_service import SmartSuggestionService
    smart_service = SmartSuggestionService()
    
    # 🚀 PERFORMANCE OPTIMIZATION #2: Pre-fetch COA accounts from loan-bridge configuration
    # Get configured accounts from loan-bridge setup (http://localhost:8000/loan-bridge/setup/)
    from loan_reconciliation_bridge.models import LoanGLConfiguration
    
    coa_cache = {}
    try:
        loan_config = LoanGLConfiguration.objects.filter(company=company, is_active=True).first()
        if loan_config:
            # Use configured accounts from loan-bridge setup
            coa_cache['121000'] = loan_config.general_loan_disbursements_account
            coa_cache['122000'] = loan_config.general_loans_receivable_account
        else:
            # Fallback to hardcoded codes if no configuration exists
            coa_cache['121000'] = Account.objects.filter(company=company, code='121000').first()
            coa_cache['122000'] = Account.objects.filter(company=company, code='122000').first()
    except Exception as e:
        print(f"⚠️ Error loading loan-bridge configuration: {e}")
        # Fallback to hardcoded codes
        coa_cache['121000'] = Account.objects.filter(company=company, code='121000').first()
        coa_cache['122000'] = Account.objects.filter(company=company, code='122000').first()
    
    # Additional fallback lookups if accounts still not found
    if not coa_cache.get('121000'):
        coa_cache['121000'] = Account.objects.filter(
            company=company,
            name__icontains="disbursement"
        ).filter(
            Q(name__icontains="loan") | Q(code__startswith="121")
        ).first()
    
    if not coa_cache.get('122000'):
        coa_cache['122000'] = Account.objects.filter(
            company=company,
            name__icontains="receivable"
        ).filter(
            Q(name__icontains="loan") | Q(code__startswith="122")
        ).first()
    
    # Disbursement keywords for quick lookup
    disbursement_keywords = [
        'зээл олгов', 'олгосон', 'зээл олго', 'disburs', 'диsburse',
        'loan disburs', 'олгосон зээл', 'eb-', 'зээл-'
    ]

    # Convert to list and add smart suggestions for each transaction
    transactions_list = []
    for txn in unmatched_transactions:
        # Get smart suggestions for this transaction (using cached service)
        suggestions = []
        try:
            suggestions = smart_service.get_suggestions(
                bank_description=txn.description or "", amount=float(txn.amount)
            )
            
            # Enhance suggestions with COA account recommendations
            for suggestion in suggestions:
                # Determine if this is a loan payment or loan disbursement
                description_lower = (txn.description or "").lower()
                amount = float(txn.amount)
                
                # Check for loan disbursement patterns (negative amounts, disbursement keywords)
                is_disbursement = (
                    amount < 0 and 
                    any(keyword in description_lower for keyword in disbursement_keywords)
                )
                
                # Use pre-fetched accounts from cache (use different variable name to avoid overwriting 'account')
                if is_disbursement and coa_cache['121000']:
                    coa_account = coa_cache['121000']
                    suggestion["suggested_coa"] = {
                        "account_id": coa_account.id,
                        "account_code": coa_account.code,
                        "account_name": coa_account.name,
                        "account_display": f"{coa_account.code} - {coa_account.name}"
                    }
                    suggestion["coa_reason"] = "🚀 Auto-match for loan disbursement (Configured at /loan-bridge/setup/)"
                elif not is_disbursement and coa_cache['122000']:
                    coa_account = coa_cache['122000']
                    suggestion["suggested_coa"] = {
                        "account_id": coa_account.id,
                        "account_code": coa_account.code,
                        "account_name": coa_account.name,
                        "account_display": f"{coa_account.code} - {coa_account.name}"
                    }
                    suggestion["coa_reason"] = "🔥 Main engine for loan payments (Configured at /loan-bridge/setup/)"
                else:
                    suggestion["suggested_coa"] = None
                    suggestion["coa_reason"] = ""
                
        except Exception as e:
            print(f"Error getting suggestions for transaction {txn.id}: {e}")
            suggestions = []

        # 🎯 NEW: Add Bank Rules suggestions (modular - safe if disabled)
        try:
            from bank_rules import get_rules_enabled, get_rule_suggestions
            
            if get_rules_enabled():
                trans_dict = {
                    'id': txn.id,
                    'description': txn.description or '',
                    'amount': float(txn.amount),
                    'correspondent_account': txn.related_account or '',
                    'transaction_date': txn.date,
                    'reference_number': txn.reference or '',
                    'debit_credit': 'debit' if float(txn.amount) < 0 else 'credit',
                }
                
                # DEBUG: Print transaction details for matching
                if 'Интернэт' in (txn.description or ''):
                    print(f"\n🔍 DEBUG - Transaction for matching:")
                    print(f"  ID: {txn.id}")
                    print(f"  Description: {repr(txn.description)}")
                    print(f"  Amount: {txn.amount} (type: {type(txn.amount)})")
                    print(f"  Amount (float): {float(txn.amount)}")
                    print(f"  Debit/Credit: {trans_dict['debit_credit']}")
                    print(f"  Trans dict: {trans_dict}")
                
                rule_suggestions = get_rule_suggestions(trans_dict, company)
                
                # DEBUG: Print suggestions result
                if 'Интернэт' in (txn.description or ''):
                    print(f"  Rule suggestions count: {len(rule_suggestions)}")
                    if rule_suggestions:
                        print(f"  Suggestions: {rule_suggestions}")
                    else:
                        print(f"  No rules matched!")
                
                # Merge rule suggestions with smart suggestions (rules appear first)
                suggestions = rule_suggestions + suggestions
        except ImportError:
            # bank_rules app not installed - continue normally
            pass
        except Exception as e:
            # Rule engine error - log and continue
            print(f"⚠️ Bank rules error for transaction {txn.id}: {e}")
            import traceback
            traceback.print_exc()
        
        # 🧠 NEW: Add AI Pattern Learning suggestions (modular - safe if disabled)
        try:
            from smart_learning.services import PatternMatcher, ConfidenceCalculator
            
            # DEBUG: Log AI pattern attempt
            if 'Интернэт' in (txn.description or ''):
                print(f"\n🔍 DEBUG: Attempting AI pattern matching for transaction {txn.id}")
                print(f"  Description: '{txn.description}'")
                print(f"  Amount: {txn.amount}")
                print(f"  Company: {company}")
            
            # Initialize pattern matcher for this company
            pattern_matcher = PatternMatcher(company=company)
            confidence_calc = ConfidenceCalculator()
            
            # DEBUG: Log pattern matcher initialization
            if 'Интернэт' in (txn.description or ''):
                print(f"  ✅ PatternMatcher initialized successfully")
            
            # Get AI pattern suggestions
            ai_suggestions = pattern_matcher.get_smart_suggestions(
                transaction_description=txn.description or '',
                amount=abs(float(txn.amount)),
                trans_type='debit' if float(txn.amount) < 0 else 'credit'
            )
            
            # DEBUG: Log AI suggestions result
            if 'Интернэт' in (txn.description or ''):
                print(f"  🧠 AI suggestions returned: {len(ai_suggestions)} suggestions")
                if ai_suggestions:
                    for i, s in enumerate(ai_suggestions):
                        print(f"    {i+1}: {s}")
                else:
                    print(f"    (No AI suggestions found)")
            
            # Convert AI suggestions to the same format as rule suggestions
            for ai_sug in ai_suggestions:
                suggestion = {
                    'source': 'ai_pattern',  # Mark as AI-generated
                    'pattern_id': ai_sug['pattern_id'],
                    'pattern_name': ai_sug['pattern_name'],
                    'confidence': ai_sug['confidence'],
                    'confidence_label': confidence_calc.get_confidence_label(ai_sug['confidence']),
                    'suggested_who_text': ai_sug['who'],
                    'customer_name': ai_sug['who'],  # Add for template compatibility
                    'match_percentage': round(ai_sug['confidence'], 1),  # Add for template compatibility
                    'suggested_coa': {
                        'account_id': ai_sug['what'].id,
                        'account_code': ai_sug['what'].code,
                        'account_name': ai_sug['what'].name,
                        'account_display': f"{ai_sug['what'].code} - {ai_sug['what'].name}"
                    },
                    'coa_reason': f"🧠 AI Pattern: {ai_sug['accuracy_history']:.0f}% accurate ({ai_sug['times_used']} uses)",
                    'auto_apply': ai_sug.get('auto_apply', False),
                }
                suggestions.append(suggestion)
                
                # DEBUG: Log suggestion conversion
                if 'Интернэт' in (txn.description or ''):
                    print(f"  ✅ Converted AI suggestion: {suggestion}")
                    print(f"    source: {suggestion['source']}")
                    print(f"    pattern_id: {suggestion['pattern_id']}")
                    print(f"    confidence: {suggestion['confidence']}")
                    print(f"    suggested_who_text: {suggestion['suggested_who_text']}")
                    print(f"    suggested_coa: {suggestion['suggested_coa']}")
            
            # DEBUG: Print AI suggestions
            if ai_suggestions and ('Интернэт' in (txn.description or '') or 'bank fee' in (txn.description or '').lower()):
                print(f"\n🧠 AI Pattern suggestions for '{txn.description}':")
                print(f"  Count: {len(ai_suggestions)}")
                for s in ai_suggestions[:3]:
                    print(f"  - {s['who']} / {s['what'].name} ({s['confidence']:.1f}% confidence)")
        
        except ImportError as ie:
            # smart_learning app not installed - continue normally
            if 'Интернэт' in (txn.description or ''):
                print(f"  ❌ ImportError in AI pattern matching: {ie}")
            pass
        except Exception as e:
            # AI engine error - log and continue
            if 'Интернэт' in (txn.description or ''):
                print(f"  ⚠️ AI pattern matching error for transaction {txn.id}: {e}")
                import traceback
                traceback.print_exc()
            else:
                print(f"⚠️ AI pattern matching error for transaction {txn.id}: {e}")
                import traceback
                traceback.print_exc()
        
        # 🛡️ Filter out any None values that may have slipped through
        suggestions = [s for s in suggestions if s is not None and isinstance(s, dict)]
        
        # 🎯 Sort all suggestions by confidence (highest first)
        # Rule suggestions default to 80% confidence if not specified
        # AI pattern suggestions have calculated confidence
        suggestions.sort(key=lambda x: x.get('confidence', 80), reverse=True)

        # DEBUG: Log final suggestions for Интернэт transactions
        if 'Интернэт' in (txn.description or ''):
            print(f"\n🔍 FINAL SUGGESTIONS for transaction {txn.id}:")
            print(f"  Total suggestions: {len(suggestions)}")
            for i, sug in enumerate(suggestions):
                print(f"    {i+1}: source={sug.get('source', 'unknown')}, confidence={sug.get('confidence', 0)}")
                print(f"       who={sug.get('suggested_who_text', 'unknown')}, coa={sug.get('suggested_coa', {}).get('account_display', 'unknown')}")

        # Create enhanced transaction dict
        enhanced_txn = {
            "id": txn.id,
            "date": txn.date,
            "amount": txn.amount,
            "description": txn.description,
            "reference": txn.reference,
            "related_account": txn.related_account,
            "transaction_hash": txn.transaction_hash,
            "coa_account": txn.coa_account,
            "smart_suggestions": suggestions[:5],  # Limit to top 5 suggestions
        }
        
        # DEBUG: Log the final enhanced transaction for Интернэт
        if 'Интернэт' in (txn.description or ''):
            print(f"  📦 Enhanced transaction {txn.id} smart_suggestions count: {len(enhanced_txn['smart_suggestions'])}")
        
        transactions_list.append(enhanced_txn)

    # Get reconciliation progress (across ALL pages, not just current page)
    progress = ReconciliationService.get_reconciliation_progress(account)
    
    # 🚀 FIX: Use the CORRECT remaining count from progress (not pagination count)
    # progress['unmatched_transactions'] = total_transactions - matched_transactions (CORRECT)
    # total_transactions = count at page load (STALE after reconciliation)
    progress['total_unmatched_all_pages'] = progress['unmatched_transactions']  # Use backend count
    progress['unmatched_current_page'] = len(transactions_list)  # Current page only
    progress['showing_from'] = offset + 1
    progress['showing_to'] = min(offset + transactions_per_page, total_transactions)

    # Get Chart of Accounts for dropdown - exclude only cash/bank accounts, include loans receivable
    coa_accounts = (
        Account.objects.filter(company=company)
        .exclude(account_type="Bank")  # Only exclude Bank accounts
        .exclude(
            # Exclude specific cash accounts but keep loans receivable
            code__in=["1001"]  # Exclude Cash account specifically
        )
        .order_by("code", "name")
    )

    # Group COA by account type for better UX
    coa_groups = {}
    for acc in coa_accounts:
        account_type = (
            acc.get_account_type_display()
            if hasattr(acc, "get_account_type_display")
            else acc.account_type
        )
        if account_type not in coa_groups:
            coa_groups[account_type] = []
        coa_groups[account_type].append(acc)

    # Get loan customers for WHO dropdown with proper data structure
    try:
        from loans_core.models import LoanApplication
        from loans_customers.models import Customer

        # Get customers from approved loan applications
        loan_applications = (
            LoanApplication.objects.filter(status="approved")  # Fixed: lowercase status
            .select_related("customer", "company")
            .order_by("customer__first_name", "customer__last_name")
        )

        # Filter by current company first
        company_applications = loan_applications.filter(company=company)

        # If no customers in current company, show all approved customers but mark their company
        if not company_applications.exists():
            loan_applications = loan_applications
        else:
            loan_applications = company_applications

        # Extract loan customers with all required fields for template
        loan_customers = []
        seen_customers = set()
        for app in loan_applications:
            customer_key = f"{app.customer.first_name}_{app.customer.last_name}_{app.customer.email}"
            if customer_key not in seen_customers:
                # Create customer display text
                customer_name = (
                    f"{app.customer.first_name} {app.customer.last_name}".strip()
                )
                if not customer_name:
                    customer_name = app.customer.email or f"Customer #{app.customer.id}"

                # Get vehicle information from collateral if available
                vehicle_plates = []
                vehicle_info = {}
                try:
                    from loans_collateral.models import Collateral

                    # Get collateral items for this loan application
                    collateral_items = Collateral.objects.filter(loan_application=app)
                    for collateral in collateral_items:
                        if collateral.vehicle_license_plate:
                            vehicle_plates.append(collateral.vehicle_license_plate)
                            vehicle_info[collateral.vehicle_license_plate] = {
                                "make": getattr(collateral, "vehicle_make", ""),
                                "model": getattr(collateral, "vehicle_model", ""),
                                "year": getattr(collateral, "vehicle_year", ""),
                            }
                except ImportError:
                    # Fallback: try the original method
                    if (
                        hasattr(app.customer, "vehicles")
                        and app.customer.vehicles.exists()
                    ):
                        for vehicle in app.customer.vehicles.all():
                            if vehicle.license_plate:
                                vehicle_plates.append(vehicle.license_plate)
                                vehicle_info[vehicle.license_plate] = {
                                    "make": getattr(vehicle, "make", ""),
                                    "model": getattr(vehicle, "model", ""),
                                    "year": getattr(vehicle, "year", ""),
                                }

                # Create detailed display for dropdown
                display_detail = f"Loan #{app.application_id}"
                if app.customer.phone_primary:
                    display_detail += f" | Phone: {app.customer.phone_primary}"
                if app.customer.national_id:
                    display_detail += f" | ID: {app.customer.national_id}"
                if vehicle_plates:
                    display_detail += f" | Plates: {', '.join(vehicle_plates)}"

                # Get loan number if the application has been converted to an active loan
                loan_number = app.application_id  # Default to application_id
                try:
                    if hasattr(app, 'loan') and app.loan:
                        loan_number = app.loan.loan_number
                except Exception:
                    pass  # If no loan exists yet, use application_id

                # Create loan customer data structure matching template expectations
                loan_customer_data = {
                    "loan_id": app.id,
                    "loan_number": loan_number,  # Use loan_number from Loan model, or application_id as fallback
                    "application_id": app.application_id,  # Keep application_id separately
                    "customer_name": customer_name,
                    "customer_id": app.customer.id,
                    "loan_amount": (
                        float(app.approved_amount or app.requested_amount)
                        if (app.approved_amount or app.requested_amount)
                        else 0
                    ),
                    "loan_type": (
                        getattr(app.loan_product, "name", "")
                        if app.loan_product
                        else ""
                    ),
                    "display_text": customer_name,
                    "display_detail": display_detail,
                    "phone": app.customer.phone_primary or "",
                    "national_id": app.customer.national_id or "",
                    "vehicle_plates": vehicle_plates,
                    "vehicle_info": vehicle_info,
                    "company": app.company,
                    "is_same_company": app.company.id == company.id,
                }
                loan_customers.append(loan_customer_data)
                seen_customers.add(customer_key)

    except ImportError:
        # Fallback if loans module not available
        loan_customers = []

    # Simple context - only essential data
    context = {
        "company": company,
        "account": account,
        "account_id": account_id,
        "account_name": account.name,
        "transactions": transactions_list,
        "progress": progress,
        "coa_groups": coa_groups,
        "loan_customers": loan_customers,
        "title": f"Bank Reconciliation - {account.name} (Simple)",
        # File filtering info
        "file_id": file_id,
        "filtered_by_file": filtered_by_file,
        # Pagination data
        "current_page": page,
        "total_pages": total_pages,
        "total_transactions": total_transactions,
        "has_next": has_next,
        "has_previous": has_previous,
        "next_page": page + 1 if has_next else None,
        "previous_page": page - 1 if has_previous else None,
        "showing_from": offset + 1,
        "showing_to": min(offset + transactions_per_page, total_transactions),
        "page_range": range(1, min(total_pages + 1, 11)),  # Show first 10 pages
    }

    return render(request, "reconciliation/reconciliation_simple_minimal.html", context)
