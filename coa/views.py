from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from django.urls import reverse_lazy
from core.mixins import CompanyRequiredMixin, CompanyContextMixin
from .models import Account, TaxRate, AccountType
from .forms import TaxRateForm, TaxRateEditForm, AccountForm, AccountExcelUploadForm


class CompanyAwareAccountMixin(CompanyRequiredMixin):
    """Mixin for account views that ensures company context."""

    def get_queryset(self):
        """Filter accounts by active company."""
        if not self.active_company:
            return Account.objects.none()
        return Account.objects.for_company(self.active_company)


@method_decorator(login_required, name="dispatch")
class ChartOfAccountsView(CompanyAwareAccountMixin, ListView):
    """Display chart of accounts for active company."""

    model = Account
    template_name = "coa/chart_of_accounts_simple.html"
    context_object_name = "accounts"

    def get_queryset(self):
        """Get accounts filtered by company and search parameters."""
        queryset = super().get_queryset()

        # Get search and filter parameters
        search_query = self.request.GET.get("search", "")
        account_type_filter = self.request.GET.get("type", "")

        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                Q(code__icontains=search_query)
                | Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        # Apply account type filter
        if account_type_filter:
            queryset = queryset.filter(account_type=account_type_filter)

        return queryset.select_related(
            "tax_rate", "parent_account", "created_by", "updated_by"
        ).order_by("code")

    def get_context_data(self, **kwargs):
        """Add additional context for chart of accounts."""
        context = super().get_context_data(**kwargs)

        # Calculate totals for active company
        from django.db.models import Sum

        asset_types = [
            "CURRENT_ASSET",
            "FIXED_ASSET",
            "INVENTORY",
            "NON_CURRENT_ASSET",
            "PREPAYMENT",
        ]
        total_assets = (
            self.get_queryset()
            .filter(account_type__in=asset_types)
            .aggregate(total=Sum("ytd_balance"))["total"]
            or 0
        )

        # Get tax rates for active company
        tax_rates = TaxRate.objects.for_company(self.active_company).filter(
            is_active=True
        )

        context.update(
            {
                "total_assets": total_assets,
                "tax_rates": tax_rates,
                "account_types": AccountType.choices,
                "search_query": self.request.GET.get("search", ""),
                "current_filter": self.request.GET.get("type", ""),
            }
        )

        return context


@method_decorator(login_required, name="dispatch")
class AccountDetailView(CompanyAwareAccountMixin, DetailView):
    """Display account details."""

    model = Account
    template_name = "coa/account_detail.html"
    context_object_name = "account"
    pk_url_kwarg = "account_id"

    def get_context_data(self, **kwargs):
        """Add children and balance info."""
        context = super().get_context_data(**kwargs)
        account = self.get_object()

        # Get child accounts for the same company
        children = account.get_children().filter(company=self.active_company)

        context.update(
            {
                "children": children,
                "balance": account.ytd_balance,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class CreateAccountView(CompanyAwareAccountMixin, CreateView):
    """Create new account for active company."""

    model = Account
    form_class = AccountForm
    template_name = "coa/test_create_account.html"

    def get_form_kwargs(self):
        """Pass company to form."""
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.active_company
        return kwargs

    def form_valid(self, form):
        """Save account with company and user info."""
        try:
            account = form.save(commit=False)
            account.company = self.active_company
            account.created_by = self.request.user
            account.updated_by = self.request.user
            account.ytd_balance = 0.00
            account.save()

            messages.success(
                self.request, f'Account "{account.full_name}" created successfully!'
            )
            return redirect("coa:chart_of_accounts")
        
        except IntegrityError as e:
            # Handle duplicate account code gracefully
            if "UNIQUE constraint failed" in str(e) and "code" in str(e):
                code = form.cleaned_data.get('code', '')
                suggested_code = self._get_suggested_code(code)
                
                messages.warning(
                    self.request, 
                    f'⚠️ Account code "{code}" already exists! Try using "{suggested_code}" instead.'
                )
                
                # Add the error to the form to show it inline
                form.add_error('code', f'This code is already taken. Try "{suggested_code}" instead.')
            else:
                messages.error(
                    self.request, 
                    'Unable to create account. Please check your input and try again.'
                )
            
            # Return form with errors
            return self.form_invalid(form)

    def _get_suggested_code(self, attempted_code):
        """Generate suggested alternative codes."""
        try:
            base_num = int(attempted_code)
            # Try incrementing the code
            for i in range(1, 10):
                suggested_code = str(base_num + i)
                if not Account.objects.filter(
                    company=self.active_company, 
                    code=suggested_code
                ).exists():
                    return suggested_code
        except ValueError:
            # If code is not numeric, suggest adding a suffix
            for suffix in ['A', 'B', 'C', '1', '2']:
                suggested_code = f"{attempted_code}{suffix}"
                if not Account.objects.filter(
                    company=self.active_company, 
                    code=suggested_code[:10]  # Respect max length
                ).exists():
                    return suggested_code[:10]
        
        # Fallback suggestion
        return f"{attempted_code[:8]}01"

    def get_context_data(self, **kwargs):
        """Add basic context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Create New Account",
                "active_company": self.active_company,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class EditAccountView(CompanyAwareAccountMixin, UpdateView):
    """Edit existing account for active company."""

    model = Account
    form_class = AccountForm
    template_name = "coa/edit_account.html"
    pk_url_kwarg = "account_id"

    def get_form_kwargs(self):
        """Pass company to form."""
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.active_company
        return kwargs

    def form_valid(self, form):
        """Update account with user info."""
        try:
            # Get the account object first
            account = form.save(commit=False)
            account.updated_by = self.request.user
            
            # Save the account
            account.save()

            messages.success(
                self.request, f'Account "{account.full_name}" updated successfully!'
            )
            return redirect("coa:chart_of_accounts")
        
        except IntegrityError as e:
            # Handle duplicate account code gracefully
            if "UNIQUE constraint failed" in str(e) and "code" in str(e):
                code = form.cleaned_data.get('code', '')
                
                # Get a fresh suggestion that excludes the current account
                suggested_code = self._get_suggested_code(code, exclude_pk=self.object.pk)
                
                messages.warning(
                    self.request, 
                    f'⚠️ Account code "{code}" is already in use! Try "{suggested_code}" instead.'
                )
                
                # Add the error to the form to show it inline
                form.add_error('code', f'This code is already taken. Try "{suggested_code}" instead.')
            else:
                messages.error(
                    self.request, 
                    'Unable to update account. Please check your input and try again.'
                )
            
            # Return form with errors
            return self.form_invalid(form)

    def _get_suggested_code(self, attempted_code, exclude_pk=None):
        """Generate suggested alternative codes, excluding specific account."""
        try:
            base_num = int(attempted_code)
            for i in range(1, 10):
                suggested_code = str(base_num + i)
                query = Account.objects.filter(
                    company=self.active_company, 
                    code=suggested_code
                )
                if exclude_pk:
                    query = query.exclude(pk=exclude_pk)
                
                if not query.exists():
                    return suggested_code
        except ValueError:
            for suffix in ['A', 'B', 'C', '1', '2']:
                suggested_code = f"{attempted_code}{suffix}"
                query = Account.objects.filter(
                    company=self.active_company, 
                    code=suggested_code[:10]
                )
                if exclude_pk:
                    query = query.exclude(pk=exclude_pk)
                
                if not query.exists():
                    return suggested_code[:10]
        
        return f"{attempted_code[:8]}01"

    def get_object(self, queryset=None):
        """Get the account object with fresh data from database."""
        if queryset is None:
            queryset = self.get_queryset()
        
        # Always fetch fresh data from database to avoid stale data issues
        queryset = queryset.select_related('tax_rate', 'company')
        
        return super().get_object(queryset=queryset)

    def get_context_data(self, **kwargs):
        """Add basic context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": f"Edit Account: {self.object.full_name}",
                "active_company": self.active_company,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class DeleteAccountView(CompanyAwareAccountMixin, DeleteView):
    """Delete account for active company."""

    model = Account
    template_name = "coa/delete_account.html"
    pk_url_kwarg = "account_id"
    success_url = reverse_lazy("coa:chart_of_accounts")

    def form_valid(self, form):
        """Override to handle AI data before deletion."""
        account = self.get_object()
        
        # Check if account can be deleted
        can_delete, reason = self._can_delete_account(account)
        
        if not can_delete:
            messages.warning(self.request, f"⚠️ Cannot delete account: {reason}")
            return redirect("coa:chart_of_accounts")
        
        # Get the action type from the form
        action = self.request.POST.get('action', 'deactivate')
        
        # Check for AI learning data
        has_ai_data = False
        ai_patterns_count = 0
        ai_history_count = 0
        
        try:
            from smart_learning.models import MatchPattern, TransactionMatchHistory
            ai_patterns_count = MatchPattern.objects.filter(suggested_what=account).count()
            ai_history_count = TransactionMatchHistory.objects.filter(matched_what=account).count()
            has_ai_data = ai_patterns_count > 0 or ai_history_count > 0
        except ImportError:
            pass  # Smart learning not installed
        
        # If user confirmed to delete AI data
        delete_ai_data = self.request.POST.get('delete_ai_data') == 'yes'
        
        if has_ai_data and not delete_ai_data and action == 'permanent_delete':
            # Show warning with options
            messages.warning(
                self.request,
                f"⚠️ This account is used by the AI Learning System! "
                f"It has {ai_patterns_count} learned pattern(s) and {ai_history_count} training record(s). "
                f"Please confirm if you want to delete the AI data as well."
            )
            # Store the warning in session to show on confirmation page
            self.request.session['pending_delete_account'] = account.id
            self.request.session['ai_patterns_count'] = ai_patterns_count
            self.request.session['ai_history_count'] = ai_history_count
            return redirect('coa:confirm_delete_with_ai', account_id=account.id)
        
        # Delete AI data if confirmed and permanent delete
        if has_ai_data and action == 'permanent_delete':
            try:
                from smart_learning.models import MatchPattern, TransactionMatchHistory
                MatchPattern.objects.filter(suggested_what=account).delete()
                TransactionMatchHistory.objects.filter(matched_what=account).delete()
                messages.info(
                    self.request,
                    f"🗑️ Deleted {ai_patterns_count} AI pattern(s) and {ai_history_count} training record(s)"
                )
            except ImportError:
                pass
        
        # Handle based on action type
        if action == 'permanent_delete':
            # Permanently delete the account
            account_name = account.full_name
            try:
                account.delete()
                messages.success(
                    self.request, 
                    f'✅ Account "{account_name}" has been permanently deleted!'
                )
            except Exception as e:
                messages.error(
                    self.request,
                    f'❌ Error deleting account: {str(e)}'
                )
        else:
            # Soft delete by deactivating (default)
            account.is_active = False
            account.updated_by = self.request.user
            account.save()
            messages.success(
                self.request, 
                f'✅ Account "{account.full_name}" has been deactivated successfully!'
            )
        
        return redirect("coa:chart_of_accounts")

    def _can_delete_account(self, account):
        """Check if account can be safely deleted."""
        # Check if it's a system essential account
        if account.is_essential:
            return False, "Essential system accounts cannot be deleted"
        
        # Check if locked (system accounts)
        if account.is_locked:
            return False, "Locked accounts cannot be deleted"
        
        # Check if has child accounts
        if account.get_children().exists():
            return False, f"This account has {account.get_children().count()} child account(s). Please delete or reassign child accounts first"
        
        # Allow deletion (will deactivate, not hard delete)
        return True, "Account can be deleted"

    def get_context_data(self, **kwargs):
        """Add basic context."""
        context = super().get_context_data(**kwargs)
        can_delete, reason = self._can_delete_account(self.object)
        
        context.update(
            {
                "active_company": self.active_company,
                "can_delete": can_delete,
                "delete_reason": reason,
            }
        )
        return context


# Function-based view wrappers
edit_account_view = EditAccountView.as_view()
delete_account_view = DeleteAccountView.as_view()


@login_required
def confirm_delete_with_ai(request, account_id):
    """Confirmation page for deleting an account with AI data."""
    # Get active company
    mixin = CompanyContextMixin()
    mixin.request = request
    active_company = mixin.get_active_company()
    
    if not active_company:
        messages.error(request, "Please select a company first.")
        return redirect("dashboard")
    
    account = Account.objects.for_company(active_company).get(id=account_id)
    
    # Get AI data counts
    ai_patterns_count = request.session.get('ai_patterns_count', 0)
    ai_history_count = request.session.get('ai_history_count', 0)
    
    # Get AI patterns details
    ai_patterns = []
    try:
        from smart_learning.models import MatchPattern
        patterns = MatchPattern.objects.filter(suggested_what=account)
        for p in patterns:
            ai_patterns.append({
                'name': p.pattern_name,
                'description': p.description_pattern,
                'confidence': p.confidence,
                'times_seen': p.times_seen,
            })
    except ImportError:
        pass
    
    context = {
        'account': account,
        'active_company': active_company,
        'ai_patterns_count': ai_patterns_count,
        'ai_history_count': ai_history_count,
        'ai_patterns': ai_patterns,
    }
    
    return render(request, 'coa/confirm_delete_with_ai.html', context)


@login_required
def account_search_api(request):
    """API endpoint for searching accounts within active company."""
    # Get active company from context mixin approach
    mixin = CompanyContextMixin()
    mixin.request = request
    active_company = mixin.get_active_company()

    if not active_company:
        return JsonResponse({"accounts": [], "error": "No active company"})

    query = request.GET.get("q", "")
    if len(query) < 2:
        return JsonResponse({"accounts": []})

    accounts = Account.objects.for_company(active_company).filter(
        Q(name__icontains=query) | Q(code__icontains=query), is_active=True
    )[
        :10
    ]  # Limit to 10 results

    accounts_data = []
    for account in accounts:
        accounts_data.append(
            {
                "id": account.id,
                "name": account.name,
                "code": account.code,
                "account_type": account.account_type,
                "balance": str(account.ytd_balance),
                "tax_rate": account.tax_rate.name,
            }
        )

    return JsonResponse({"accounts": accounts_data})


@login_required
def check_code_availability_api(request):
    """API endpoint to check if an account code is available."""
    # Get active company from context mixin approach
    mixin = CompanyContextMixin()
    mixin.request = request
    active_company = mixin.get_active_company()

    if not active_company:
        return JsonResponse({"available": True, "error": "No active company"})

    code = request.GET.get("code", "").strip()
    account_id = request.GET.get("account_id")  # For edit mode
    
    if not code:
        return JsonResponse({"available": True})

    # Check if account with this code already exists
    existing_accounts = Account.objects.filter(
        company=active_company, 
        code=code,
        is_active=True
    )
    
    # Exclude current account if editing
    if account_id:
        try:
            existing_accounts = existing_accounts.exclude(pk=int(account_id))
        except (ValueError, TypeError):
            pass
    
    if existing_accounts.exists():
        existing_account = existing_accounts.first()
        
        # Generate suggestion
        suggested_code = _generate_code_suggestion(code, active_company, account_id)
        
        return JsonResponse({
            "available": False,
            "existing_account": existing_account.name,
            "suggested_code": suggested_code
        })
    
    return JsonResponse({"available": True})


def _generate_code_suggestion(attempted_code, company, exclude_account_id=None):
    """Generate a suggested alternative code."""
    try:
        base_num = int(attempted_code)
        for i in range(1, 10):
            suggested_code = str(base_num + i)
            query = Account.objects.filter(
                company=company, 
                code=suggested_code,
                is_active=True
            )
            if exclude_account_id:
                try:
                    query = query.exclude(pk=int(exclude_account_id))
                except (ValueError, TypeError):
                    pass
            
            if not query.exists():
                return suggested_code
    except ValueError:
        for suffix in ['A', 'B', 'C', '1', '2']:
            suggested_code = f"{attempted_code}{suffix}"[:10]
            query = Account.objects.filter(
                company=company, 
                code=suggested_code,
                is_active=True
            )
            if exclude_account_id:
                try:
                    query = query.exclude(pk=int(exclude_account_id))
                except (ValueError, TypeError):
                    pass
            
            if not query.exists():
                return suggested_code
    
    return f"{attempted_code[:8]}01"


# Legacy function-based views for compatibility
chart_of_accounts_view = ChartOfAccountsView.as_view()
account_detail_view = AccountDetailView.as_view()
create_account_view = CreateAccountView.as_view()


# Tax Rate Views
class CompanyAwareTaxRateMixin(CompanyRequiredMixin):
    """Mixin for tax rate views that ensures company context."""

    def get_queryset(self):
        """Filter tax rates by active company."""
        if not self.active_company:
            return TaxRate.objects.none()
        return TaxRate.objects.for_company(self.active_company)


@method_decorator(login_required, name="dispatch")
class TaxRateListView(CompanyAwareTaxRateMixin, ListView):
    """Display tax rates for active company."""

    model = TaxRate
    template_name = "coa/tax_rates.html"
    context_object_name = "tax_rates"

    def get_queryset(self):
        """Get tax rates with account count annotation."""
        queryset = super().get_queryset()

        # Annotate with count of accounts using each tax rate
        queryset = queryset.annotate(
            account_count=Count("account", filter=Q(account__is_active=True))
        ).order_by("name")

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context for tax rates."""
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "total_tax_rates": self.get_queryset().count(),
            }
        )

        return context


@method_decorator(login_required, name="dispatch")
class TaxRateCreateView(CompanyAwareTaxRateMixin, CreateView):
    """Create new tax rate for active company."""

    model = TaxRate
    form_class = TaxRateForm
    template_name = "coa/tax_rate_new.html"
    success_url = reverse_lazy("coa:tax_rates")

    def form_valid(self, form):
        """Save tax rate with company info."""
        tax_rate = form.save(commit=False)
        tax_rate.company = self.active_company
        tax_rate.save()

        messages.success(
            self.request, f'Tax rate "{tax_rate.name}" created successfully!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Add New Tax Rate"
        return context


@method_decorator(login_required, name="dispatch")
class TaxRateUpdateView(CompanyAwareTaxRateMixin, UpdateView):
    """Edit existing tax rate."""

    model = TaxRate
    form_class = TaxRateEditForm
    template_name = "coa/tax_rate_edit.html"
    success_url = reverse_lazy("coa:tax_rates")
    pk_url_kwarg = "tax_rate_id"

    def get_form_kwargs(self):
        """Pass company to form for validation."""
        kwargs = super().get_form_kwargs()
        if self.active_company:
            kwargs["instance"].company = self.active_company
        return kwargs

    def form_valid(self, form):
        """Update tax rate."""
        messages.success(
            self.request, f'Tax rate "{form.instance.name}" updated successfully!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        tax_rate = self.get_object()

        # Get accounts using this tax rate
        accounts_using = (
            Account.objects.for_company(self.active_company)
            .filter(tax_rate=tax_rate, is_active=True)
            .order_by("code")
        )

        context.update(
            {
                "form_title": f"Edit Tax Rate: {tax_rate.name}",
                "accounts_using": accounts_using,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class TaxRateDeleteView(CompanyAwareTaxRateMixin, DeleteView):
    """Delete tax rate if not in use."""

    model = TaxRate
    template_name = "coa/tax_rate_confirm_delete.html"
    success_url = reverse_lazy("coa:tax_rates")
    pk_url_kwarg = "tax_rate_id"

    def delete(self, request, *args, **kwargs):
        """Check if tax rate can be deleted before deletion."""
        tax_rate = self.get_object()

        # Use the model's protection method
        can_delete, message = tax_rate.can_be_deleted()

        if not can_delete:
            messages.error(
                request, f'Cannot delete tax rate "{tax_rate.name}" - {message}'
            )
            return redirect("coa:tax_rates")

        messages.success(request, f'Tax rate "{tax_rate.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Tax Rate function-based views
tax_rate_list_view = TaxRateListView.as_view()
tax_rate_create_view = TaxRateCreateView.as_view()
tax_rate_update_view = TaxRateUpdateView.as_view()
tax_rate_delete_view = TaxRateDeleteView.as_view()


@login_required
def tax_rate_api_create(request):
    """API endpoint for creating tax rates with components."""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    # Get active company
    mixin = CompanyContextMixin()
    mixin.request = request
    active_company = mixin.get_active_company()

    if not active_company:
        return JsonResponse({"error": "No active company"}, status=400)

    try:
        import json

        data = json.loads(request.body)

        name = data.get("name", "").strip()
        components = data.get("components", [])

        if not name:
            return JsonResponse({"error": "Name is required"}, status=400)

        # Calculate total rate from components
        total_rate = sum(
            float(comp.get("rate", 0)) for comp in components if comp.get("name")
        )

        # Check if tax rate name exists for this company
        if TaxRate.objects.for_company(active_company).filter(name=name).exists():
            return JsonResponse(
                {"error": f'Tax rate "{name}" already exists'}, status=400
            )

        # Create component description
        component_names = [
            f"{c['name']} ({c['rate']}%)" for c in components if c.get("name")
        ]
        description = (
            f"Components: {', '.join(component_names)}" if component_names else ""
        )

        # Create the tax rate
        tax_rate = TaxRate.objects.create(
            company=active_company,
            name=name,
            rate=total_rate / 100,  # Convert percentage to decimal
            description=description,
        )

        return JsonResponse(
            {
                "success": True,
                "tax_rate": {
                    "id": tax_rate.id,
                    "name": tax_rate.name,
                    "rate": tax_rate.rate * 100,  # Return as percentage
                    "description": tax_rate.description,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@method_decorator(login_required, name="dispatch")
class AccountExcelUploadView(CompanyRequiredMixin, View):
    """Company-aware Excel upload view for Chart of Accounts."""
    
    template_name = "coa/account_excel_upload.html"
    
    def get(self, request):
        """Display upload form."""
        form = AccountExcelUploadForm(company=self.active_company)
        
        context = {
            'form': form,
            'active_company': self.active_company,
            'account_types': AccountType.get_grouped_choices(),
            'tax_rates': TaxRate.objects.for_company(self.active_company).filter(is_active=True),
            'valid_types': [choice[0] for choice in AccountType.choices],
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Process uploaded Excel file."""
        form = AccountExcelUploadForm(request.POST, request.FILES, company=self.active_company)
        
        # Handle save action with session data (no new file upload needed)
        if request.POST.get('action') == 'save' and 'coa_upload_data' in request.session:
            try:
                processed_data = request.session.get('coa_upload_data')
                result = self._save_processed_data(processed_data, request.user)
                
                if result['success']:
                    messages.success(
                        request, 
                        f"Successfully created {result['created_count']} accounts! "
                        f"Skipped {result['skipped_count']} invalid rows."
                    )
                    # Clear session data after successful save
                    request.session.pop('coa_upload_data', None)
                    request.session.pop('coa_upload_filename', None)
                    return redirect('coa:chart_of_accounts')
                else:
                    messages.error(request, f"Error saving accounts: {result['error']}")
                    # Show preview again with error
                    context = {
                        'form': AccountExcelUploadForm(company=self.active_company),
                        'active_company': self.active_company,
                        'processed_data': processed_data,
                        'account_types': AccountType.get_grouped_choices(),
                        'tax_rates': TaxRate.objects.for_company(self.active_company).filter(is_active=True),
                        'valid_types': [choice[0] for choice in AccountType.choices],
                        'show_preview': True,
                        'uploaded_filename': request.session.get('coa_upload_filename', 'uploaded file'),
                    }
                    return render(request, self.template_name, context)
            except Exception as e:
                messages.error(request, f"Error saving accounts: {str(e)}")
        
        # Handle preview action with existing session data (Upload New File clicked)
        if request.POST.get('action') == 'preview' and 'coa_upload_data' in request.session and not request.FILES:
            # Clear session to allow new upload
            request.session.pop('coa_upload_data', None)
            request.session.pop('coa_upload_filename', None)
            messages.info(request, "Ready to upload a new file.")
            
            context = {
                'form': AccountExcelUploadForm(company=self.active_company),
                'active_company': self.active_company,
                'account_types': AccountType.get_grouped_choices(),
                'tax_rates': TaxRate.objects.for_company(self.active_company).filter(is_active=True),
                'valid_types': [choice[0] for choice in AccountType.choices],
            }
            return render(request, self.template_name, context)
        
        if not form.is_valid():
            context = {
                'form': form,
                'active_company': self.active_company,
                'account_types': AccountType.get_grouped_choices(),
                'tax_rates': TaxRate.objects.for_company(self.active_company).filter(is_active=True),
                'valid_types': [choice[0] for choice in AccountType.choices],
            }
            return render(request, self.template_name, context)
        
        # Process the Excel file
        excel_file = form.cleaned_data['excel_file']
        
        try:
            # Process Excel file with company context
            processed_data = self._process_excel_file(excel_file)
            
            # Store processed data in session for later use
            request.session['coa_upload_data'] = processed_data
            request.session['coa_upload_filename'] = excel_file.name
            
            # If this is a preview request, show preview
            if request.POST.get('action') == 'preview':
                context = {
                    'form': form,
                    'active_company': self.active_company,
                    'processed_data': processed_data,
                    'account_types': AccountType.get_grouped_choices(),
                    'tax_rates': TaxRate.objects.for_company(self.active_company).filter(is_active=True),
                    'valid_types': [choice[0] for choice in AccountType.choices],
                    'show_preview': True,
                    'uploaded_filename': excel_file.name,
                }
                return render(request, self.template_name, context)
            
            # If this is a save request, save the data
            elif request.POST.get('action') == 'save':
                result = self._save_processed_data(processed_data, request.user)
                
                if result['success']:
                    messages.success(
                        request, 
                        f"Successfully created {result['created_count']} accounts! "
                        f"Skipped {result['skipped_count']} invalid rows."
                    )
                    # Clear session data after successful save
                    request.session.pop('coa_upload_data', None)
                    request.session.pop('coa_upload_filename', None)
                    return redirect('coa:chart_of_accounts')
                else:
                    messages.error(request, f"Error saving accounts: {result['error']}")
            
        except Exception as e:
            messages.error(request, f"Error processing Excel file: {str(e)}")
        
        # Return to form with errors
        context = {
            'form': form,
            'active_company': self.active_company,
            'account_types': AccountType.get_grouped_choices(),
            'tax_rates': TaxRate.objects.for_company(self.active_company).filter(is_active=True),
            'valid_types': [choice[0] for choice in AccountType.choices],
        }
        return render(request, self.template_name, context)
    
    def _get_restricted_account_codes(self):
        """
        Get account codes that are restricted from Excel upload.
        These accounts must be created manually for proper integration.
        
        NOTE: CURRENT_ASSET accounts are NOT restricted - they can be created via Excel
        and then manually converted to bank accounts later if needed.
        """
        return {
            # Removing all restrictions - all account types can be created via Excel
            # Bank accounts will be created as CURRENT_ASSET first, then converted manually
        }
    
    def _process_excel_file(self, excel_file):
        """Process Excel file and return validated data with company context."""
        import openpyxl
        from io import BytesIO
        
        # Load workbook
        wb = openpyxl.load_workbook(BytesIO(excel_file.read()))
        ws = wb.active
        
        processed_data = {
            'valid_rows': [],
            'invalid_rows': [],
            'total_rows': 0
        }
        
        # Get existing account codes for this company
        existing_codes = set(
            Account.objects.for_company(self.active_company)
            .values_list('code', flat=True)
        )
        
        # Get existing tax rates for this company
        tax_rates_map = {
            tax_rate.name: tax_rate for tax_rate in 
            TaxRate.objects.for_company(self.active_company).filter(is_active=True)
        }
        
        # Valid account types
        valid_types = {choice[0]: choice[1] for choice in AccountType.choices}
        
        # Get restricted account codes
        restricted_accounts = self._get_restricted_account_codes()
        all_restricted_codes = {}
        
        for category, info in restricted_accounts.items():
            for code in info['codes']:
                all_restricted_codes[code] = {
                    'category': category,
                    'reason': info['reason']
                }
        
        # Process rows (skip header row)
        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row):  # Skip empty rows
                continue
                
            processed_data['total_rows'] += 1
            
            # Extract data from row
            code = str(row[0]).strip() if row[0] else ""
            name = str(row[1]).strip() if row[1] else ""
            account_type = str(row[2]).strip() if row[2] else ""
            tax_rate_name = str(row[3]).strip() if row[3] and str(row[3]).strip() else None
            
            # Validation
            errors = []
            warnings = []
            
            # Check for restricted account codes first
            if code and code in all_restricted_codes:
                restriction_info = all_restricted_codes[code]
                errors.append(f"❌ Code '{code}' is RESTRICTED: {restriction_info['reason']}")
            
            # Validate Code (required and unique)
            if not code:
                errors.append("Code is required")
            elif code in existing_codes:
                errors.append(f"Code '{code}' already exists in this company")
            elif len(code) > 10:
                errors.append("Code must be 10 characters or less")
            
            # Validate Name (required)
            if not name:
                errors.append("Name is required")
            elif len(name) > 150:
                errors.append("Name must be 150 characters or less")
            
            # Validate Account Type (required and must be valid)
            if not account_type:
                errors.append("Type is required")
            elif account_type not in valid_types:
                errors.append(f"Invalid account type '{account_type}'. Must be one of: {', '.join(valid_types.keys())}")
            
            # Validate Tax Rate (optional but must exist if provided)
            tax_rate_obj = None
            if tax_rate_name:
                if tax_rate_name in tax_rates_map:
                    tax_rate_obj = tax_rates_map[tax_rate_name]
                else:
                    warnings.append(f"Tax rate '{tax_rate_name}' not found for this company - will be set to None")
            
            row_data = {
                'row_number': row_num,
                'code': code,
                'name': name,
                'account_type': account_type,
                'account_type_display': valid_types.get(account_type, account_type),
                'tax_rate_name': tax_rate_name,
                'tax_rate_obj': tax_rate_obj,
                'errors': errors,
                'warnings': warnings,
                'is_valid': len(errors) == 0
            }
            
            if row_data['is_valid']:
                processed_data['valid_rows'].append(row_data)
                # Add to existing codes to prevent duplicates within the same file
                existing_codes.add(code)
            else:
                processed_data['invalid_rows'].append(row_data)
        
        return processed_data
    
    def _save_processed_data(self, processed_data, user):
        """Save valid rows to database with company context."""
        created_count = 0
        skipped_count = len(processed_data['invalid_rows'])
        
        try:
            from django.db import transaction
            
            with transaction.atomic():
                for row_data in processed_data['valid_rows']:
                    if row_data['is_valid']:
                        account = Account(
                            company=self.active_company,
                            code=row_data['code'],
                            name=row_data['name'],
                            account_type=row_data['account_type'],
                            tax_rate=row_data['tax_rate_obj'],
                            created_by=user,
                            updated_by=user,
                            ytd_balance=0.00,
                            current_balance=0.00,
                            opening_balance=0.00
                        )
                        account.save()
                        created_count += 1
                    else:
                        skipped_count += 1
            
            return {
                'success': True,
                'created_count': created_count,
                'skipped_count': skipped_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'created_count': created_count,
                'skipped_count': skipped_count
            }


# Function-based view wrapper for compatibility
account_excel_upload_view = AccountExcelUploadView.as_view()
