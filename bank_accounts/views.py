from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models
from django.utils import timezone
from coa.models import Account
from company.models import Company
from .models import (
    BankTransaction,
    UploadedFile,
    BankStatementDocument,
    BankStatementProcessing,
    BankTransactionRecord,
)
from .translation_service import MongolianTranslationService
from .file_processor import BankStatementProcessor
import csv
import io
import os
import re
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Bank accounts landing page with overview"""
    # For now, show empty state if no company - don't redirect
    company_id = request.session.get("active_company_id")  # Use correct session key
    if not company_id:
        # Show empty state instead of redirecting - use empty queryset
        return render(
            request,
            "bank_accounts/landing.html",
            {
                "accounts": Account.objects.none(),  # Empty queryset instead of list
                "company": None,
                "total_balance": 0,
                "no_company": True,
            },
        )

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        # Show empty state instead of redirecting - use empty queryset
        return render(
            request,
            "bank_accounts/landing.html",
            {
                "accounts": Account.objects.none(),  # Empty queryset instead of list
                "company": None,
                "total_balance": 0,
                "no_company": True,
            },
        )

    # Show only CURRENT_ASSET accounts that are specifically designated as bank accounts
    # Not ALL current asset accounts - only the ones manually marked as bank accounts
    accounts = Account.objects.filter(
        company=company,
        account_type="CURRENT_ASSET",
        is_bank_account=True,  # Only show accounts specifically marked as bank accounts
    ).order_by("code")

    # Add upload information for each account
    accounts_with_uploads = []
    total_transactions = 0
    total_upload_files = 0

    for account in accounts:
        # Get recent uploads for this account
        recent_uploads = UploadedFile.objects.filter(account=account).order_by(
            "-uploaded_at"
        )[:3]

        # Get transaction count
        transaction_count = BankTransaction.objects.filter(coa_account=account).count()
        total_transactions += transaction_count

        # Get last upload info
        last_upload = recent_uploads.first() if recent_uploads.exists() else None

        # Total uploads count
        total_uploads = UploadedFile.objects.filter(account=account).count()
        total_upload_files += total_uploads

        accounts_with_uploads.append(
            {
                "account": account,
                "recent_uploads": recent_uploads,
                "transaction_count": transaction_count,
                "last_upload": last_upload,
                "total_uploads": total_uploads,
            }
        )

    # Calculate total balance
    total_balance = sum(account.current_balance or 0 for account in accounts)

    return render(
        request,
        "bank_accounts/landing.html",
        {
            "accounts_data": accounts_with_uploads,
            "accounts": accounts,  # Keep for compatibility
            "company": company,
            "total_balance": total_balance,
            "total_transactions": total_transactions,
            "total_upload_files": total_upload_files,
        },
    )


@login_required
def add_account(request):
    """Create new bank account (COA account with type=Bank)"""
    company_id = request.session.get("active_company_id")  # Use correct session key
    if not company_id:
        messages.error(request, "Please select a company first to add bank accounts.")
        return redirect(
            "bank_accounts:dashboard"
        )  # Redirect back to bank accounts instead of dashboard

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first to add bank accounts.")
        return redirect(
            "bank_accounts:dashboard"
        )  # Redirect back to bank accounts instead of dashboard

    if request.method == "POST":
        try:
            name = request.POST.get("name", "").strip()
            code = request.POST.get("code", "").strip()

            # Validate name
            if not name:
                messages.error(request, "Account name is required.")
                return render(
                    request, "bank_accounts/add_account.html", {"company": company}
                )

            # Validate and suggest code if provided
            if code:
                # Check if code already exists
                existing_account = Account.objects.filter(
                    company=company, code=code
                ).first()

                if existing_account:
                    # Generate suggestion
                    suggested_code = _generate_bank_code_suggestion(code, company)
                    messages.warning(
                        request,
                        f'⚠️ Account code "{code}" is already used by "{existing_account.name}". '
                        f'Try "{suggested_code}" instead.',
                    )
                    return render(
                        request,
                        "bank_accounts/add_account.html",
                        {
                            "company": company,
                            "form_data": {
                                "name": name,
                                "code": code,
                                "suggested_code": suggested_code,
                            },
                        },
                    )

            # Create the account
            account = Account.objects.create(
                company=company,
                name=name,
                account_type="CURRENT_ASSET",  # Use proper account type instead of 'Bank'
                code=code if code else _generate_auto_bank_code(company),
                is_bank_account=True,  # Mark this as a bank account
                created_by=request.user,
                updated_by=request.user,
                ytd_balance=0.00,
                current_balance=0.00,
            )

            messages.success(
                request, f"Bank account '{account.name}' created successfully!"
            )
            return redirect("bank_accounts:dashboard")

        except Exception as e:
            messages.error(request, f"Error creating bank account: {str(e)}")
            return render(
                request,
                "bank_accounts/add_account.html",
                {
                    "company": company,
                    "form_data": {
                        "name": request.POST.get("name", ""),
                        "code": request.POST.get("code", ""),
                    },
                },
            )

    return render(request, "bank_accounts/add_account.html", {"company": company})


def _generate_bank_code_suggestion(attempted_code, company):
    """Generate a suggested alternative code for bank accounts."""
    try:
        base_num = int(attempted_code)
        for i in range(1, 10):
            suggested_code = str(base_num + i)
            if not Account.objects.filter(
                company=company, code=suggested_code
            ).exists():
                return suggested_code
    except ValueError:
        for suffix in ["A", "B", "C", "1", "2"]:
            suggested_code = f"{attempted_code}{suffix}"[:10]
            if not Account.objects.filter(
                company=company, code=suggested_code
            ).exists():
                return suggested_code

    return f"{attempted_code[:8]}01"


def _generate_auto_bank_code(company):
    """Auto-generate a bank account code."""
    # Find the next available code in 10xx series
    for code_num in range(1001, 1100):
        code = str(code_num)
        if not Account.objects.filter(company=company, code=code).exists():
            return code

    # Fallback to 11xx series
    for code_num in range(1101, 1200):
        code = str(code_num)
        if not Account.objects.filter(company=company, code=code).exists():
            return code

    return "1999"  # Last resort


@login_required
def convert_account(request):
    """Convert existing CURRENT_ASSET account to bank account"""
    company_id = request.session.get("active_company_id")
    if not company_id:
        messages.error(request, "Please select a company first to convert accounts.")
        return redirect("bank_accounts:dashboard")

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first to convert accounts.")
        return redirect("bank_accounts:dashboard")

    if request.method == "POST":
        account_id = request.POST.get("account_id")
        try:
            account = Account.objects.get(
                id=account_id,
                company=company,
                account_type="CURRENT_ASSET",
                is_bank_account=False,  # Must not already be a bank account
            )

            # Convert to bank account
            account.is_bank_account = True
            account.updated_by = request.user
            account.save()

            messages.success(
                request, f"Successfully converted '{account.name}' to a bank account!"
            )
            return redirect("bank_accounts:dashboard")

        except Account.DoesNotExist:
            messages.error(request, "Account not found or cannot be converted.")
        except Exception as e:
            messages.error(request, f"Error converting account: {str(e)}")

    # Get CURRENT_ASSET accounts that are not already bank accounts
    available_accounts = Account.objects.filter(
        company=company,
        account_type="CURRENT_ASSET",
        is_bank_account=False,  # Not already a bank account
        is_active=True,
    ).order_by("code")

    context = {"company": company, "available_accounts": available_accounts}

    return render(request, "bank_accounts/convert_account.html", context)


@login_required
def bank_statement(request, account_id):
    """Display bank statement lines similar to Xero format"""
    company_id = request.session.get("active_company_id")
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    # Get account
    account = get_object_or_404(
        Account,
        id=account_id,
        company=company,
        account_type="CURRENT_ASSET",
        is_bank_account=True,  # Only allow bank accounts
    )

    # Get all transactions for this account, ordered by date (newest first)
    transactions = BankTransaction.objects.filter(coa_account=account).order_by(
        "-date", "-id"
    )

    # Calculate running balance (like Xero)
    # Start with opening balance from conversion system
    opening_balance = Decimal("0")
    try:
        from conversion.models import ConversionBalance

        conversion_balance = (
            ConversionBalance.objects.filter(company=company, account=account)
            .order_by("-as_at_date")
            .first()
        )

        if conversion_balance:
            # For bank accounts, typically credit balances are positive
            opening_balance = (
                conversion_balance.credit_amount - conversion_balance.debit_amount
            )
    except ImportError:
        pass

    # Prepare transactions with running balance
    transaction_list = []

    # Process transactions in chronological order to calculate running balance correctly
    transactions_chronological = list(transactions.order_by("date", "id"))
    running_balance = opening_balance

    for bank_transaction in transactions_chronological:
        running_balance += bank_transaction.amount

        # Determine transaction type
        if bank_transaction.amount > 0:
            trans_type = "Credit"
            spent = None
            received = abs(bank_transaction.amount)
        else:
            trans_type = "Debit"
            spent = abs(bank_transaction.amount)
            received = None

        transaction_list.append(
            {
                "transaction": bank_transaction,
                "type": trans_type,
                "spent": spent,
                "received": received,
                "balance": running_balance,
                "status": "Imported",  # Could be enhanced with actual reconciliation status
                "reconciled": False,  # Could be enhanced with actual reconciliation data
            }
        )

    # Reverse to show newest first (like Xero)
    transaction_list.reverse()

    # Get upload information
    uploads = UploadedFile.objects.filter(account=account).order_by("-uploaded_at")

    # Calculate summary stats
    total_debits = sum(abs(t.amount) for t in transactions if t.amount < 0)
    total_credits = sum(t.amount for t in transactions if t.amount > 0)
    current_balance = running_balance

    context = {
        "account": account,
        "company": company,
        "transactions": transaction_list,
        "opening_balance": opening_balance,
        "current_balance": current_balance,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "transaction_count": transactions.count(),
        "uploads": uploads,
        "page_title": f"Bank Statement - {account.name}",
    }

    return render(request, "bank_accounts/bank_statement.html", context)


@login_required
def upload_transactions(request, account_id):
    """Upload bank transactions for a specific account"""
    company_id = request.session.get("active_company_id")  # Use correct session key
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    # Get account - only allow accounts specifically marked as bank accounts
    account = get_object_or_404(
        Account,
        id=account_id,
        company=company,
        account_type="CURRENT_ASSET",
        is_bank_account=True,  # Only allow bank accounts
    )

    if request.method == "POST" and request.FILES.get("statement_file"):
        uploaded_file = request.FILES["statement_file"]

        # Validate file type - support both CSV and Excel
        file_name = uploaded_file.name.lower()
        if not (
            file_name.endswith(".csv")
            or file_name.endswith(".xlsx")
            or file_name.endswith(".xls")
        ):
            messages.error(
                request, "Please upload a CSV (.csv) or Excel (.xlsx, .xls) file."
            )
            return render(
                request,
                "bank_accounts/upload.html",
                {"account": account, "company": company},
            )

        try:
            # Create file hash for duplicate detection
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            uploaded_file.seek(0)

            # Check if this exact file has been uploaded before
            if UploadedFile.objects.filter(
                account=account, file_hash=file_hash
            ).exists():
                messages.warning(
                    request,
                    "This exact file has already been uploaded to this account.",
                )
                return render(
                    request,
                    "bank_accounts/upload.html",
                    {"account": account, "company": company},
                )

            # Store file
            file_dir = f"bank_statements/{company.id}/{account.id}"
            os.makedirs(os.path.join("media", file_dir), exist_ok=True)
            stored_filename = (
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
            )
            file_path = f"{file_dir}/{stored_filename}"

            # Save file to media directory
            full_path = os.path.join("media", file_path)
            os.makedirs(
                os.path.dirname(full_path), exist_ok=True
            )  # Ensure directory exists
            with open(full_path, "wb") as f:
                f.write(file_content)

            # Create UploadedFile record
            uploaded_file_record = UploadedFile.objects.create(
                account=account,
                company=company,
                original_filename=uploaded_file.name,
                stored_filename=stored_filename,
                file_size=len(file_content),
                file_hash=file_hash,
                uploaded_by=request.user,
                total_rows=0,
                imported_count=0,
                duplicate_count=0,
                error_count=0,
            )

            # Initialize processing variables
            transactions_created = 0
            duplicates_skipped = 0
            errors = []
            total_rows = 0

            # Process file based on type
            if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
                # Process Excel file
                import openpyxl

                # Save file temporarily
                full_path = os.path.join("media", file_path)
                with open(full_path, "wb") as f:
                    f.write(file_content)

                # Read Excel file
                workbook = openpyxl.load_workbook(full_path)
                worksheet = workbook.active

                # Convert Excel to CSV-like structure for processing
                all_rows = []
                for row in worksheet.iter_rows(values_only=True):
                    if any(cell for cell in row):  # Skip empty rows
                        all_rows.append(
                            [str(cell) if cell is not None else "" for cell in row]
                        )

                # Try to find the actual data table in the Excel file
                # Look for rows that might contain column headers
                data_start_row = 0
                headers = []

                # First, let's log the structure for debugging
                logger.info(f"Excel file has {len(all_rows)} rows")
                for i, row in enumerate(all_rows[:10]):  # Show first 10 rows
                    logger.info(f"Row {i+1}: {row}")

                # Look for transaction table headers - more comprehensive search
                for i, row in enumerate(all_rows):
                    if not row or not any(cell for cell in row):
                        continue

                    row_text = " ".join(
                        str(cell).lower() if cell else "" for cell in row
                    )

                    # Check for typical bank statement column patterns
                    date_indicators = ["огноо", "date", "дата", "он сар өдөр"]
                    amount_indicators = ["дүн", "amount", "мөнгөн дүн", "тоо"]
                    description_indicators = [
                        "тайлбар",
                        "description",
                        "гүйлгээ",
                        "утга",
                    ]

                    # Count how many indicators we find
                    indicator_count = 0
                    if any(indicator in row_text for indicator in date_indicators):
                        indicator_count += 1
                    if any(indicator in row_text for indicator in amount_indicators):
                        indicator_count += 1
                    if any(
                        indicator in row_text for indicator in description_indicators
                    ):
                        indicator_count += 1

                    # If we find at least 2 indicators, this might be our header row
                    if indicator_count >= 2:
                        headers = row
                        data_start_row = i + 1
                        logger.info(f"Found headers at row {i+1}: {headers}")
                        break

                # If no clear headers found, try to find a row with multiple short text entries
                # (typical of column headers vs long descriptive text)
                if not headers:
                    for i, row in enumerate(all_rows):
                        if not row or not any(cell for cell in row):
                            continue

                        # Skip rows that are clearly metadata (have very long text entries)
                        long_text_count = sum(
                            1 for cell in row if cell and len(str(cell).strip()) > 30
                        )
                        total_cells = sum(
                            1 for cell in row if cell and str(cell).strip()
                        )

                        if total_cells >= 3 and long_text_count <= total_cells // 2:
                            # This row has multiple short entries, likely headers
                            headers = row
                            data_start_row = i + 1
                            logger.info(
                                f"Found potential headers by length analysis at row {i+1}: {headers}"
                            )
                            break

                # Last resort: look for the first row that has dates in recognizable format
                if not headers:
                    for i, row in enumerate(all_rows):
                        if not row:
                            continue

                        # Check if this row contains date-like values
                        date_like_count = 0
                        for cell in row:
                            if cell and isinstance(cell, str):
                                cell_str = str(cell).strip()
                                # Look for date patterns
                                if re.match(
                                    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", cell_str
                                ) or re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", cell_str):
                                    date_like_count += 1

                        # If we find dates, the previous row might be headers
                        if date_like_count > 0 and i > 0:
                            headers = all_rows[i - 1]
                            data_start_row = i
                            logger.info(
                                f"Found headers by date detection at row {i}: {headers}"
                            )
                            break
                        elif date_like_count > 0 and i == 0:
                            # First row has dates, assume no headers
                            headers = [f"Column_{j}" for j in range(len(row))]
                            data_start_row = i
                            logger.info(
                                f"No headers found, using generated headers: {headers}"
                            )
                            break

                # If no clear headers found, try to use the first non-empty row as headers
                if not headers and all_rows:
                    # Skip metadata rows (rows that contain mostly text like company info)
                    for i, row in enumerate(all_rows):
                        # Skip rows that look like metadata
                        if (
                            len([cell for cell in row if cell and len(str(cell)) > 20])
                            > len(row) // 2
                        ):
                            continue  # This row has too much text, likely metadata

                        # Use this as header row
                        headers = row
                        data_start_row = i + 1
                        break

                if headers and data_start_row < len(all_rows):
                    data_rows = all_rows[data_start_row:]

                    # Create CSV-like data structure
                    csv_data = []
                    for row in data_rows:
                        if not any(
                            cell.strip() for cell in row if cell
                        ):  # Skip empty rows
                            continue

                        row_dict = {}
                        for i, header in enumerate(headers):
                            if header:  # Only map non-empty headers
                                row_dict[str(header)] = row[i] if i < len(row) else ""

                        # Only include rows that have some data
                        if any(v for v in row_dict.values() if v and str(v).strip()):
                            csv_data.append(row_dict)
                else:
                    csv_data = []
                    errors.append(
                        "Could not identify data table structure in Excel file"
                    )

                # Debug: log file structure for troubleshooting
                logger.info(
                    f"Excel file analysis - Total rows: {len(all_rows)}, Headers found: {headers}, Data start row: {data_start_row}"
                )
                if len(all_rows) > 0:
                    logger.info(f"First few rows: {all_rows[:5]}")

            else:
                # Process CSV file - detect delimiter (comma or semicolon)
                decoded_file = file_content.decode("utf-8")

                # Try to detect delimiter by checking the first line
                first_line = decoded_file.split("\n")[0] if decoded_file else ""
                delimiter = (
                    ";"
                    if ";" in first_line
                    and first_line.count(";") > first_line.count(",")
                    else ","
                )

                csv_data = list(
                    csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
                )

            with transaction.atomic():
                # Initialize translation service for header mapping
                translation_service = MongolianTranslationService()

                # Special handling for Mongolian bank statement format
                # where the first few rows are metadata, not transaction data
                if not csv_data:
                    errors.append(
                        "No transaction data found in file. File appears to contain only metadata."
                    )
                elif len(csv_data) > 0:
                    # Check if the first row looks like metadata instead of transaction data
                    first_row = csv_data[0] if csv_data else {}
                    first_row_values = list(first_row.values())

                    # If first row contains metadata patterns, skip it
                    metadata_indicators = [
                        "хэвлэсэн огноо",
                        "депозит дансны",
                        "хэрэглэгч",
                        "интервал",
                        "дансны дугаар",
                    ]
                    is_metadata_row = any(
                        any(
                            indicator in str(value).lower()
                            for indicator in metadata_indicators
                        )
                        for value in first_row_values
                        if value
                    )

                    if is_metadata_row:
                        logger.info(
                            "Detected metadata in first row, looking for actual transaction data..."
                        )
                        # Try to find where the actual transaction data starts
                        transaction_data_start = -1

                        for idx, row_data in enumerate(csv_data):
                            row_values = list(row_data.values())
                            # Look for rows that contain date-like values
                            date_found = False
                            amount_found = False

                            for value in row_values:
                                if value and str(value).strip():
                                    val_str = str(value).strip()
                                    # Check for date patterns
                                    if re.match(
                                        r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", val_str
                                    ) or re.match(
                                        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", val_str
                                    ):
                                        date_found = True
                                    # Check for amount patterns (numbers, possibly negative)
                                    if re.match(
                                        r"^[+-]?\d+\.?\d*$", val_str.replace(",", "")
                                    ):
                                        amount_found = True

                            if date_found and amount_found:
                                transaction_data_start = idx
                                logger.info(
                                    f"Found transaction data starting at row {idx + 1}"
                                )
                                break

                        # If we found transaction data, use only that part
                        if transaction_data_start >= 0:
                            csv_data = csv_data[transaction_data_start:]
                            logger.info(
                                f"Using {len(csv_data)} rows of transaction data"
                            )
                        else:
                            errors.append(
                                "Could not find transaction data in file. File appears to contain only metadata."
                            )

                for row_num, row in enumerate(
                    csv_data, start=2
                ):  # Start at 2 because of header
                    total_rows += 1
                    try:
                        # Create case-insensitive column lookup
                        row_lower = {k.lower(): v for k, v in row.items()}

                        # Skip summary/total rows (common in bank statements)
                        skip_row = False
                        for key, value in row_lower.items():
                            if value and isinstance(value, str):
                                value_lower = str(value).lower().strip()
                                # Check for Mongolian and English summary indicators
                                summary_indicators = [
                                    "нийт дүн:",
                                    "нийт дүн",
                                    "total:",
                                    "total amount:",
                                    "үлдэгдэл:",
                                    "balance:",
                                    "эцсийн үлдэгдэл:",
                                    "closing balance:",
                                    "summary",
                                    "subtotal",
                                    "grand total",
                                    "нийт",
                                    "дүнгийн нийлбэр",
                                    "эцсийн",
                                    "эхний үлдэгдэл",
                                ]
                                if any(
                                    indicator in value_lower
                                    for indicator in summary_indicators
                                ):
                                    skip_row = True
                                    logger.info(
                                        f"Skipping summary row {row_num}: {value}"
                                    )
                                    break

                        if skip_row:
                            continue

                        # Try to map Mongolian headers to English using translation service
                        date_value = None
                        amount_value = None
                        description_value = ""
                        reference_value = ""
                        related_account_value = ""

                        # Search for date column (try multiple approaches)
                        for key, value in row_lower.items():
                            # Direct English match
                            if key in ["date", "огноо", "огноо:", "дата"]:
                                date_value = value
                                break
                            # Translation match
                            translated_result = (
                                translation_service.translate_column_header(key)
                            )
                            if (
                                translated_result
                                and "date"
                                in translated_result.get("english", "").lower()
                            ):
                                date_value = value
                                break

                        # Search for amount column (handle both single amount and separate debit/credit)
                        amount_value = None
                        debit_value = None
                        credit_value = None

                        # First, try to find separate debit and credit columns
                        for key, value in row_lower.items():
                            # Direct matches for debit
                            if key in [
                                "debit",
                                "дебит",
                                "дебит гүйлгээ",
                                "дебит гүйлгээ:",
                                "зарлага",
                            ]:
                                if value is not None and str(value).strip() not in [
                                    "",
                                    "None",
                                ]:
                                    debit_value = value
                            # Direct matches for credit
                            elif key in [
                                "credit",
                                "кредит",
                                "кредит гүйлгээ",
                                "кредит гүйлгээ:",
                                "орлого",
                            ]:
                                if value is not None and str(value).strip() not in [
                                    "",
                                    "None",
                                ]:
                                    credit_value = value
                            # Translation matches
                            else:
                                translated_result = (
                                    translation_service.translate_column_header(key)
                                )
                                if translated_result:
                                    english_type = translated_result.get(
                                        "english", ""
                                    ).lower()
                                    column_type = translated_result.get(
                                        "column_type", ""
                                    )
                                    if (
                                        column_type == "debit"
                                        or "debit" in english_type
                                    ):
                                        if value is not None and str(
                                            value
                                        ).strip() not in ["", "None"]:
                                            debit_value = value
                                    elif (
                                        column_type == "credit"
                                        or "credit" in english_type
                                    ):
                                        if value is not None and str(
                                            value
                                        ).strip() not in ["", "None"]:
                                            credit_value = value

                        # If no separate debit/credit found, look for single amount column
                        if debit_value is None and credit_value is None:
                            for key, value in row_lower.items():
                                # Direct matches
                                if key in [
                                    "amount",
                                    "дүн",
                                    "дүн:",
                                    "тоо",
                                    "мөнгөн дүн",
                                ]:
                                    amount_value = value
                                    break
                                # Translation match
                                translated_result = (
                                    translation_service.translate_column_header(key)
                                )
                                if (
                                    translated_result
                                    and "amount"
                                    in translated_result.get("english", "").lower()
                                ):
                                    amount_value = value
                                    break

                        # Search for description
                        for key, value in row_lower.items():
                            if key in [
                                "description",
                                "тайлбар",
                                "тайлбар:",
                                "гүйлгээ",
                                "гүйлгээний утга",
                            ]:
                                description_value = value
                                break
                            translated_result = (
                                translation_service.translate_column_header(key)
                            )
                            if translated_result and (
                                "description"
                                in translated_result.get("english", "").lower()
                                or "transaction"
                                in translated_result.get("english", "").lower()
                            ):
                                description_value = value
                                break

                        # Search for reference
                        for key, value in row_lower.items():
                            if key in [
                                "reference",
                                "лавлагаа",
                                "лавлагаа:",
                                "код",
                                "дугаар",
                            ]:
                                reference_value = value
                                break
                            translated_result = (
                                translation_service.translate_column_header(key)
                            )
                            if translated_result and (
                                "reference"
                                in translated_result.get("english", "").lower()
                                or "code"
                                in translated_result.get("english", "").lower()
                            ):
                                reference_value = value
                                break

                        # Search for related account (Column H - Харьцсан данс)
                        for key, value in row_lower.items():
                            if key in [
                                "related_account",
                                "харьцсан данс",
                                "харьцсан данс:",
                                "related account",
                            ]:
                                related_account_value = value
                                break
                            translated_result = (
                                translation_service.translate_column_header(key)
                            )
                            if translated_result and (
                                "related"
                                in translated_result.get("english", "").lower()
                                or "account"
                                in translated_result.get("english", "").lower()
                            ):
                                related_account_value = value
                                break

                        # Check if we found required fields
                        if not date_value:
                            # Try to find any date-like value in the row
                            for value in row.values():
                                if (
                                    value
                                    and isinstance(value, str)
                                    and ("/" in value or "-" in value)
                                ):
                                    try:
                                        # Try to parse as date
                                        datetime.strptime(value.strip(), "%Y/%m/%d")
                                        date_value = value
                                        break
                                    except ValueError:
                                        try:
                                            datetime.strptime(value.strip(), "%Y-%m-%d")
                                            date_value = value
                                            break
                                        except ValueError:
                                            continue

                            if not date_value:
                                errors.append(
                                    f"Row {row_num}: Could not find date column. Available columns: {list(row.keys())}"
                                )
                                continue

                        # Validate that we have either debit/credit or amount
                        if (
                            debit_value is None
                            and credit_value is None
                            and amount_value is None
                        ):
                            # Try to find any numeric value in the row as fallback
                            for value in row.values():
                                if (
                                    value
                                    and str(value)
                                    .replace(",", "")
                                    .replace("-", "")
                                    .replace(".", "")
                                    .isdigit()
                                ):
                                    amount_value = value
                                    break

                            if amount_value is None:
                                errors.append(
                                    f"Row {row_num}: Could not find amount, debit, or credit columns. Available columns: {list(row.keys())}"
                                )
                                continue

                        # Parse date with more flexible formats
                        transaction_date = None
                        transaction_datetime = None

                        # Handle different types of date values
                        if date_value is not None:
                            # Skip rows where the date field contains summary text
                            date_str_check = str(date_value).strip().lower()
                            summary_patterns = [
                                "нийт",
                                "total",
                                "үлдэгдэл",
                                "balance",
                                "summary",
                                "дүн:",
                                "amount:",
                            ]
                            if any(
                                pattern in date_str_check
                                for pattern in summary_patterns
                            ):
                                logger.info(
                                    f"Skipping row {row_num} - date field contains summary text: {date_value}"
                                )
                                continue

                            # Skip if date field is empty or just whitespace
                            if not date_str_check or date_str_check.isspace():
                                logger.info(
                                    f"Skipping row {row_num} - empty date field"
                                )
                                continue

                            # If it's already a datetime object (from Excel)
                            if hasattr(date_value, "date"):
                                transaction_datetime = date_value  # Keep full datetime
                                transaction_date = (
                                    date_value.date()
                                )  # For database storage
                            elif hasattr(
                                date_value, "strftime"
                            ):  # datetime-like object
                                transaction_datetime = date_value  # Keep full datetime
                                transaction_date = (
                                    date_value.date()
                                    if hasattr(date_value, "date")
                                    else date_value
                                )
                            else:
                                # It's a string, try to parse it
                                date_str = str(date_value).strip() if date_value else ""

                                # Try multiple date formats
                                date_formats = [
                                    "%d/%m/%Y",  # DD/MM/YYYY
                                    "%m/%d/%Y",  # MM/DD/YYYY
                                    "%Y-%m-%d",  # YYYY-MM-DD
                                    "%Y-%m-%d %H:%M:%S",  # YYYY-MM-DD HH:MM:SS (datetime)
                                    "%Y-%m-%d %H:%M",  # YYYY-MM-DD HH:MM
                                    "%Y.%m.%d",  # YYYY.MM.DD
                                    "%Y.%m.%d %H:%M:%S",  # YYYY.MM.DD HH:MM:SS
                                    "%d-%m-%Y",  # DD-MM-YYYY
                                    "%d-%m-%Y %H:%M:%S",  # DD-MM-YYYY HH:MM:SS
                                    "%m-%d-%Y",  # MM-DD-YYYY
                                    "%d.%m.%Y",  # DD.MM.YYYY
                                    "%d.%m.%Y %H:%M:%S",  # DD.MM.YYYY HH:MM:SS
                                    "%Y/%m/%d",  # YYYY/MM/DD
                                    "%Y/%m/%d %H:%M:%S",  # YYYY/MM/DD HH:MM:SS
                                    "%d/%m/%Y %H:%M:%S",  # DD/MM/YYYY HH:MM:SS
                                    "%m/%d/%Y %H:%M:%S",  # MM/DD/YYYY HH:MM:SS
                                ]

                                for date_format in date_formats:
                                    try:
                                        parsed_datetime = datetime.strptime(
                                            date_str, date_format
                                        )
                                        transaction_datetime = (
                                            parsed_datetime  # Keep full datetime
                                        )
                                        transaction_date = (
                                            parsed_datetime.date()
                                        )  # For database storage
                                        break
                                    except ValueError:
                                        continue

                        if transaction_date is None:
                            date_display = (
                                str(date_value) if date_value is not None else "None"
                            )
                            errors.append(
                                f"Row {row_num}: Invalid date format '{date_display}'. Supported formats: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, etc."
                            )
                            continue

                        # Ensure we have a transaction_datetime for hash generation
                        if (
                            transaction_datetime is None
                            and transaction_date is not None
                        ):
                            # If we only have a date (no time), create datetime with 00:00:00
                            transaction_datetime = datetime.combine(
                                transaction_date, datetime.min.time()
                            )

                        # Parse amount from debit/credit or single amount column
                        final_amount = None

                        # Process debit/credit columns (bank statement perspective)
                        if debit_value is not None or credit_value is not None:
                            debit_amount = Decimal("0")
                            credit_amount = Decimal("0")

                            # Parse debit amount
                            if debit_value is not None:
                                debit_str = (
                                    str(debit_value)
                                    .strip()
                                    .replace(",", "")
                                    .replace("$", "")
                                    .replace("€", "")
                                    .replace("£", "")
                                    .replace("₮", "")
                                )
                                if debit_str and debit_str != "None":
                                    try:
                                        debit_amount = Decimal(debit_str)
                                    except (ValueError, InvalidOperation):
                                        errors.append(
                                            f"Row {row_num}: Invalid debit amount '{debit_str}'"
                                        )
                                        continue

                            # Parse credit amount
                            if credit_value is not None:
                                credit_str = (
                                    str(credit_value)
                                    .strip()
                                    .replace(",", "")
                                    .replace("$", "")
                                    .replace("€", "")
                                    .replace("£", "")
                                    .replace("₮", "")
                                )
                                if credit_str and credit_str != "None":
                                    try:
                                        credit_amount = Decimal(credit_str)
                                    except (ValueError, InvalidOperation):
                                        errors.append(
                                            f"Row {row_num}: Invalid credit amount '{credit_str}'"
                                        )
                                        continue

                            # Determine final amount (from bank's perspective)
                            # Debits from bank = money going out = use as-is (should be negative in data)
                            # Credits from bank = money coming in = use as-is (should be positive in data)
                            if debit_amount != 0 and credit_amount != 0:
                                errors.append(
                                    f"Row {row_num}: Both debit ({debit_amount}) and credit ({credit_amount}) have non-zero values"
                                )
                                continue
                            elif debit_amount != 0:
                                final_amount = debit_amount  # Use debit amount as-is (already negative in your data)
                            elif credit_amount != 0:
                                final_amount = credit_amount  # Use credit amount as-is (positive in your data)
                            else:
                                # Both are zero - this is valid (maybe a balance inquiry or fee waiver)
                                final_amount = Decimal("0")

                        # Process single amount column (fallback)
                        elif amount_value is not None:
                            amount_str = (
                                str(amount_value)
                                .strip()
                                .replace(",", "")
                                .replace("$", "")
                                .replace("€", "")
                                .replace("£", "")
                                .replace("₮", "")
                            )
                            try:
                                final_amount = Decimal(amount_str)
                            except (ValueError, InvalidOperation):
                                errors.append(
                                    f"Row {row_num}: Invalid amount '{amount_str}'"
                                )
                                continue
                        else:
                            errors.append(f"Row {row_num}: No valid amount found")
                            continue

                        # Get other fields with defaults
                        description = (
                            description_value.strip() if description_value else ""
                        )
                        reference = reference_value.strip() if reference_value else ""

                        # Generate transaction hash for duplicate detection using FULL datetime
                        # This ensures transactions with same amount/description but different times are kept separate
                        datetime_for_hash = (
                            transaction_datetime.strftime("%Y-%m-%d %H:%M:%S")
                            if hasattr(transaction_datetime, "strftime")
                            else str(transaction_date)
                        )
                        hash_string = (
                            f"{datetime_for_hash}{final_amount}{reference}{description}"
                        )
                        transaction_hash = hashlib.sha256(
                            hash_string.encode()
                        ).hexdigest()

                        # Check for duplicate
                        if BankTransaction.objects.filter(
                            coa_account=account, transaction_hash=transaction_hash
                        ).exists():
                            duplicates_skipped += 1
                            logger.info(
                                f"Duplicate transaction skipped: Row {row_num} - {transaction_date} | ${final_amount} | '{description[:50]}...'"
                            )
                            continue

                        # Create transaction
                        BankTransaction.objects.create(
                            date=transaction_date,
                            transaction_datetime=transaction_datetime,  # Add the full datetime
                            coa_account=account,
                            company=company,
                            amount=final_amount,
                            description=description,
                            reference=reference,
                            related_account=related_account_value,  # Add related account from Column H
                            transaction_hash=transaction_hash,
                            uploaded_file=uploaded_file_record.stored_filename,  # Keep old field for now
                            uploaded_by=request.user,
                        )
                        transactions_created += 1

                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")

                # Update UploadedFile with results
                uploaded_file_record.total_rows = total_rows
                uploaded_file_record.imported_count = transactions_created
                uploaded_file_record.duplicate_count = duplicates_skipped
                uploaded_file_record.error_count = len(errors)
                uploaded_file_record.save()

            # Show results
            result_messages = []
            if transactions_created > 0:
                result_messages.append(
                    f"✅ Successfully imported {transactions_created} new transactions!"
                )

                # Update account balance (simple sum of all transactions)
                total_amount = sum(
                    t.amount
                    for t in BankTransaction.objects.filter(coa_account=account)
                )
                account.current_balance = total_amount
                account.save()

            if duplicates_skipped > 0:
                result_messages.append(
                    f"📋 Skipped {duplicates_skipped} duplicate transactions"
                )

            if errors:
                result_messages.append(f"⚠️ {len(errors)} errors occurred")

            for msg in result_messages:
                messages.success(request, msg)

            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    messages.warning(request, error)
                if len(errors) > 5:
                    messages.warning(request, f"... and {len(errors) - 5} more errors.")

            return redirect("bank_accounts:dashboard")

        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")

    # Get recent uploads for this account
    recent_uploads = UploadedFile.objects.filter(account=account).order_by(
        "-uploaded_at"
    )[:5]

    return render(
        request,
        "bank_accounts/upload.html",
        {"account": account, "company": company, "recent_uploads": recent_uploads},
    )


@login_required
def delete_upload(request, account_id, upload_id):
    """Delete an uploaded file and all its associated transactions"""
    company_id = request.session.get("active_company_id")
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    try:
        # Get account - only allow accounts specifically marked as bank accounts
        account = get_object_or_404(
            Account,
            id=account_id,
            company=company,
            account_type="CURRENT_ASSET",
            is_bank_account=True,  # Only allow bank accounts
        )
        uploaded_file = get_object_or_404(UploadedFile, id=upload_id, account=account)

        if request.method == "POST":
            try:
                with transaction.atomic():
                    # Get the stored filename for proper transaction matching
                    stored_filename = uploaded_file.stored_filename
                    original_filename = uploaded_file.original_filename

                    # Count transactions to be deleted (try multiple ways to ensure we get them all)
                    transactions_to_delete = BankTransaction.objects.filter(
                        coa_account=account, uploaded_file=stored_filename
                    )

                    # Also check for transactions that might have empty uploaded_file but match this upload
                    # (This is a backup in case there were issues during upload)
                    orphaned_transactions = BankTransaction.objects.filter(
                        coa_account=account, uploaded_file__in=["", None]
                    )

                    transaction_count = transactions_to_delete.count()
                    orphaned_count = orphaned_transactions.count()

                    print(f"Deleting upload {upload_id}:")
                    print(f"  - Stored filename: {stored_filename}")
                    print(f"  - Transactions with filename: {transaction_count}")
                    print(f"  - Orphaned transactions: {orphaned_count}")

                    # Delete transactions with matching filename
                    transactions_to_delete.delete()

                    # If there are orphaned transactions and this is the only upload for this account,
                    # clean them up too (safety measure)
                    remaining_uploads = (
                        UploadedFile.objects.filter(account=account)
                        .exclude(id=upload_id)
                        .count()
                    )
                    if remaining_uploads == 0 and orphaned_count > 0:
                        print(
                            f"  - Cleaning up {orphaned_count} orphaned transactions (no other uploads exist)"
                        )
                        orphaned_transactions.delete()
                        transaction_count += orphaned_count

                    # Delete physical file if it exists
                    file_path = os.path.join(
                        "media",
                        f"bank_statements/{company.id}/{account.id}/{stored_filename}",
                    )
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"  - Deleted physical file: {file_path}")

                    # Delete the upload record
                    uploaded_file.delete()

                    # Recalculate account balance from remaining transactions
                    remaining_transactions = BankTransaction.objects.filter(
                        coa_account=account
                    )
                    new_balance = sum(t.amount for t in remaining_transactions)
                    old_balance = account.current_balance

                    account.current_balance = new_balance
                    account.save()

                    print(f"  - Updated balance from ${old_balance} to ${new_balance}")
                    print(
                        f"  - Remaining transactions: {remaining_transactions.count()}"
                    )

                    messages.success(
                        request,
                        f"✅ Successfully deleted '{original_filename}' and removed {transaction_count} transactions.",
                    )
                    print(f"Successfully completed deletion of upload {upload_id}")

            except Exception as e:
                messages.error(request, f"❌ Error deleting upload: {str(e)}")
                print(f"Error deleting upload {upload_id}: {str(e)}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        messages.error(request, f"❌ Upload not found or access denied: {str(e)}")
        print(f"Error accessing upload {upload_id}: {str(e)}")

    # Smart redirect based on referrer
    referrer = request.META.get("HTTP_REFERER", "")
    if "bank_accounts/" in referrer and "upload" not in referrer:
        # Came from dashboard, redirect back to dashboard
        return redirect("bank_accounts:dashboard")
    else:
        # Came from upload page, redirect back to upload page
        return redirect("bank_accounts:upload_transactions", account_id=account_id)


@login_required
def enhanced_upload(request, account_id):
    """Enhanced upload with Mongolian translation support"""
    company_id = request.session.get("active_company_id")
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    # Get account - only allow accounts specifically marked as bank accounts
    account = get_object_or_404(
        Account,
        id=account_id,
        company=company,
        account_type="CURRENT_ASSET",
        is_bank_account=True,
    )

    if request.method == "POST" and request.FILES.get("statement_file"):
        try:
            uploaded_file = request.FILES["statement_file"]

            # Initialize translation service and file processor
            translation_service = MongolianTranslationService()
            file_processor = BankStatementProcessor(translation_service)

            # Process the uploaded file
            result = file_processor.process_file(
                uploaded_file, account, company, request.user
            )

            if result["success"]:
                # File processed successfully, redirect to translation verification
                processing_id = result["processing_id"]
                messages.success(
                    request,
                    f"File processed successfully. {result['total_transactions']} transactions found.",
                )
                return redirect(
                    "bank_accounts:translation_verification",
                    processing_id=processing_id,
                )
            else:
                # Show error
                messages.error(request, f"Error processing file: {result['error']}")

        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")
            logger.error(f"Enhanced upload error: {str(e)}", exc_info=True)

    # Get recent uploads for this account
    recent_documents = BankStatementDocument.objects.filter(account=account).order_by(
        "-uploaded_at"
    )[:5]

    return render(
        request,
        "bank_accounts/enhanced_upload.html",
        {
            "account": account,
            "company": company,
            "recent_documents": recent_documents,
        },
    )


@login_required
def translation_verification(request, processing_id):
    """Translation verification interface"""
    company_id = request.session.get("active_company_id")
    if not company_id:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")

    # Get processing record
    processing = get_object_or_404(
        BankStatementProcessing, id=processing_id, source_document__company=company
    )

    # Get all transaction records for this processing
    transaction_records = BankTransactionRecord.objects.filter(
        processing=processing
    ).order_by("row_number")

    # Calculate overall confidence
    if transaction_records.exists():
        overall_confidence = (
            transaction_records.aggregate(
                avg_confidence=models.Avg("overall_confidence")
            )["avg_confidence"]
            or 0
        )
    else:
        overall_confidence = 0

    # Determine confidence class for UI
    if overall_confidence >= 0.8:
        overall_confidence_class = "high"
    elif overall_confidence >= 0.5:
        overall_confidence_class = "medium"
    else:
        overall_confidence_class = "low"

    # Convert to percentage
    overall_confidence_percent = int(overall_confidence * 100)

    # Handle POST request for verification completion
    if request.method == "POST":
        try:
            # Here you would process the verification results
            # For now, we'll just mark as complete and redirect
            processing.status = "VERIFIED"
            processing.completed_at = timezone.now()
            processing.save()

            messages.success(
                request, "Translation verification completed successfully!"
            )
            return redirect("bank_accounts:dashboard")

        except Exception as e:
            messages.error(request, f"Error completing verification: {str(e)}")

    context = {
        "processing": processing,
        "transaction_records": transaction_records,
        "overall_confidence": overall_confidence,
        "overall_confidence_class": overall_confidence_class,
        "overall_confidence_percent": overall_confidence_percent,
    }

    return render(request, "bank_accounts/translation_verification.html", context)


@require_http_methods(["POST"])
@csrf_exempt
def analyze_file_preview(request):
    """AJAX endpoint for file analysis preview"""
    try:
        if not request.FILES.get("file"):
            return JsonResponse({"error": "No file provided"}, status=400)

        uploaded_file = request.FILES["file"]

        # Initialize services
        translation_service = MongolianTranslationService()
        file_processor = BankStatementProcessor(translation_service)

        # Analyze file without saving
        analysis = file_processor.analyze_file_preview(uploaded_file)

        return JsonResponse(analysis)

    except Exception as e:
        logger.error(f"File analysis error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def smart_transaction_processing(request):
    """Smart transaction processing with AI-powered suggestions"""

    if request.method == "POST":
        try:
            # Get form data
            description = request.POST.get("description", "").strip()
            amount = request.POST.get("amount", 0)
            customer_name = request.POST.get("customer_name", "").strip()
            loan_number = request.POST.get("loan_number", "").strip()
            related_account = request.POST.get("related_account", "").strip()
            transaction_type = request.POST.get("transaction_type", "auto")
            notes = request.POST.get("notes", "").strip()

            # Validate required fields
            if not description:
                messages.error(request, "Transaction description is required")
                return render(
                    request, "bank_accounts/smart_transaction_processing.html"
                )

            try:
                amount = float(amount) if amount else 0
            except (ValueError, TypeError):
                amount = 0

            # Create bank transaction record
            company_id = request.session.get("active_company_id")
            company = None
            if company_id:
                try:
                    company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    pass

            # Create transaction record
            transaction_record = BankTransaction.objects.create(
                company=company,
                description=description,
                amount=amount,
                customer_name=customer_name,
                loan_number=loan_number if loan_number else None,
                related_account=related_account if related_account else None,
                transaction_type=transaction_type,
                notes=notes,
                processed_by=request.user,
                processing_method="smart_ai",
                confidence_score=getattr(request, "_suggestion_confidence", 0),
            )

            messages.success(
                request,
                f"Transaction processed successfully! (ID: {transaction_record.id})",
            )

            # Return JSON response for AJAX
            if request.headers.get("Content-Type") == "application/json":
                return JsonResponse(
                    {
                        "success": True,
                        "transaction_id": transaction_record.id,
                        "message": "Transaction processed successfully!",
                    }
                )

            # Redirect to prevent re-submission
            return redirect("bank_accounts:smart_transaction_processing")

        except Exception as e:
            logger.error(f"Smart transaction processing error: {e}")
            messages.error(request, f"Error processing transaction: {str(e)}")

            if request.headers.get("Content-Type") == "application/json":
                return JsonResponse({"success": False, "error": str(e)}, status=500)

    # GET request - show the form
    return render(request, "bank_accounts/smart_transaction_processing.html")
