from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy
from core.mixins import CompanyRequiredMixin, CompanyContextMixin
from .models import Account, TaxRate, AccountType
from .forms import TaxRateForm, TaxRateEditForm, AccountForm


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
    template_name = "coa/create_account_simple.html"

    def get_form_kwargs(self):
        """Pass company to form."""
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.active_company
        return kwargs

    def form_valid(self, form):
        """Save account with company and user info."""
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

    def get_context_data(self, **kwargs):
        """Add account types to context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Create New Account",
                "active_company": self.active_company,
            }
        )
        return context


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
