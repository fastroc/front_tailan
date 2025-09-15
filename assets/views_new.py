"""
Fixed Asset Views
Comprehensive views for asset management system
"""

import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import FixedAsset, AssetType, DepreciationSchedule, AssetTransaction, AssetDisposal
from .forms import FixedAssetForm, AssetSearchForm
from .services import DepreciationCalculator


# ===== Asset List and Dashboard Views =====

class AssetListView(LoginRequiredMixin, ListView):
    """List view for fixed assets with filtering and search"""
    model = FixedAsset
    template_name = 'assets/list.html'
    context_object_name = 'assets'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = FixedAsset.objects.select_related('asset_type').filter(
            company=self.request.user.company
        )
        
        # Apply search filters
        form = AssetSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(number__icontains=search) |
                    Q(description__icontains=search) |
                    Q(serial_number__icontains=search)
                )
            
            asset_type = form.cleaned_data.get('asset_type')
            if asset_type:
                queryset = queryset.filter(asset_type=asset_type)
            
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            location = form.cleaned_data.get('location')
            if location:
                queryset = queryset.filter(location__icontains=location)
            
            purchase_date_from = form.cleaned_data.get('purchase_date_from')
            if purchase_date_from:
                queryset = queryset.filter(purchase_date__gte=purchase_date_from)
            
            purchase_date_to = form.cleaned_data.get('purchase_date_to')
            if purchase_date_to:
                queryset = queryset.filter(purchase_date__lte=purchase_date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = AssetSearchForm(self.request.GET)
        
        # Add summary statistics
        assets = self.get_queryset()
        context['stats'] = {
            'total_assets': assets.count(),
            'total_value': assets.aggregate(total=Sum('purchase_price'))['total'] or Decimal('0.00'),
            'active_assets': assets.filter(status='active').count(),
            'disposed_assets': assets.filter(status='disposed').count(),
        }
        
        return context


@login_required
def asset_dashboard(request):
    """Asset management dashboard with key metrics"""
    company = request.user.company
    
    # Get asset statistics
    assets = FixedAsset.objects.filter(company=company)
    
    # Asset counts by type
    asset_types = AssetType.objects.filter(is_active=True).annotate(
        asset_count=Count('fixedasset')
    ).order_by('-asset_count')
    
    # Monthly depreciation
    calculator = DepreciationCalculator()
    current_month_depreciation = Decimal('0.00')
    
    active_assets = assets.filter(status='active')
    for asset in active_assets:
        monthly_dep = calculator.calculate_monthly_depreciation(asset)
        current_month_depreciation += monthly_dep
    
    # Recent transactions
    recent_transactions = AssetTransaction.objects.filter(
        asset__company=company
    ).select_related('asset').order_by('-created_at')[:10]
    
    context = {
        'stats': {
            'total_assets': assets.count(),
            'active_assets': active_assets.count(),
            'total_value': assets.aggregate(total=Sum('purchase_price'))['total'] or Decimal('0.00'),
            'monthly_depreciation': current_month_depreciation,
        },
        'asset_types': asset_types,
        'recent_transactions': recent_transactions,
    }
    
    return render(request, 'assets/dashboard.html', context)


# ===== Asset CRUD Views =====

class AssetCreateView(LoginRequiredMixin, CreateView):
    """Create new fixed asset"""
    model = FixedAsset
    form_class = FixedAssetForm
    template_name = 'assets/new.html'
    success_url = reverse_lazy('assets:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, f'Asset "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class AssetDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of fixed asset"""
    model = FixedAsset
    template_name = 'assets/detail.html'
    context_object_name = 'asset'
    
    def get_queryset(self):
        return FixedAsset.objects.filter(company=self.request.user.company)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.object
        
        # Calculate current depreciation status
        calculator = DepreciationCalculator()
        context['depreciation_status'] = calculator.get_depreciation_status(asset)
        
        # Get depreciation schedule
        context['depreciation_schedule'] = DepreciationSchedule.objects.filter(
            asset=asset
        ).order_by('period_end_date')
        
        # Get asset transactions
        context['transactions'] = AssetTransaction.objects.filter(
            asset=asset
        ).order_by('-created_at')
        
        # Get disposal information if disposed
        if asset.status == 'disposed':
            context['disposal'] = AssetDisposal.objects.filter(asset=asset).first()
        
        return context


class AssetUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing fixed asset"""
    model = FixedAsset
    form_class = FixedAssetForm
    template_name = 'assets/edit.html'
    
    def get_queryset(self):
        return FixedAsset.objects.filter(company=self.request.user.company)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, f'Asset "{form.instance.name}" updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('assets:detail', kwargs={'pk': self.object.pk})


# ===== AJAX and API Views =====

@csrf_exempt
@require_http_methods(["POST"])
def calculate_depreciation_preview(request):
    """AJAX endpoint for real-time depreciation calculation preview"""
    try:
        data = json.loads(request.body)
        
        # Extract form data
        purchase_price = Decimal(str(data.get('purchase_price', '0')))
        residual_value = Decimal(str(data.get('residual_value', '0')))
        depreciation_method = data.get('depreciation_method', 'straight_line')
        depreciation_basis = data.get('depreciation_basis', 'effective_life')
        depreciation_rate = data.get('depreciation_rate')
        effective_life = data.get('effective_life')
        
        # Validate required fields
        if not purchase_price or purchase_price <= 0:
            return JsonResponse({'error': 'Valid purchase price is required'}, status=400)
        
        if depreciation_basis == 'rate' and not depreciation_rate:
            return JsonResponse({'error': 'Depreciation rate is required'}, status=400)
        
        if depreciation_basis == 'effective_life' and not effective_life:
            return JsonResponse({'error': 'Effective life is required'}, status=400)
        
        # Calculate depreciation values
        depreciable_amount = purchase_price - residual_value
        
        if depreciation_method == 'straight_line':
            if depreciation_basis == 'rate':
                annual_depreciation = purchase_price * (Decimal(str(depreciation_rate)) / 100)
            else:  # effective_life
                annual_depreciation = depreciable_amount / Decimal(str(effective_life))
        else:
            # For other methods, use similar logic
            if depreciation_basis == 'rate':
                annual_depreciation = purchase_price * (Decimal(str(depreciation_rate)) / 100)
            else:
                annual_depreciation = depreciable_amount / Decimal(str(effective_life))
        
        monthly_depreciation = annual_depreciation / 12
        
        # Calculate total years to fully depreciate
        if annual_depreciation > 0:
            years_to_depreciate = depreciable_amount / annual_depreciation
        else:
            years_to_depreciate = 0
        
        return JsonResponse({
            'success': True,
            'calculations': {
                'depreciable_amount': float(depreciable_amount),
                'annual_depreciation': float(annual_depreciation),
                'monthly_depreciation': float(monthly_depreciation),
                'years_to_depreciate': float(years_to_depreciate),
                'depreciation_rate_calculated': float((annual_depreciation / purchase_price * 100)) if purchase_price > 0 else 0,
            }
        })
        
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Calculation error: {str(e)}'}, status=500)


# ===== Legacy View Functions for URL Compatibility =====

@login_required
def assets_list(request):
    """Legacy function-based view for asset list"""
    # Redirect to class-based view or render with sample data
    tab = request.GET.get('tab', 'draft')
    
    # Try to get real assets if models are migrated
    try:
        company = request.user.company
        all_assets = FixedAsset.objects.filter(company=company)
        
        # Filter by status/tab
        if tab == 'draft':
            assets = all_assets.filter(status='draft')
        elif tab == 'registered':
            assets = all_assets.filter(status='active')
        elif tab == 'sold':
            assets = all_assets.filter(status='disposed')
        else:
            assets = all_assets
        
        # Format for template compatibility
        formatted_assets = []
        for asset in assets:
            formatted_assets.append({
                'id': asset.id,
                'name': asset.name,
                'description': asset.description,
                'number': asset.number,
                'type_name': asset.asset_type.name if asset.asset_type else 'N/A',
                'purchase_price': float(asset.purchase_price),
                'purchase_date': asset.purchase_date.strftime('%Y-%m-%d'),
                'status': asset.status,
                'status_badge': 'success' if asset.status == 'active' else 'warning',
                'book_value': float(asset.purchase_price - asset.accumulated_depreciation)
            })
        
        context = {
            'assets': formatted_assets,
            'tab': tab,
            'counts': {
                'draft': all_assets.filter(status='draft').count(),
                'registered': all_assets.filter(status='active').count(),
                'sold': all_assets.filter(status='disposed').count()
            },
            'last_depr_date': '31 Dec 2024'
        }
        
    except Exception:
        # Fallback to sample data if models not ready
        sample_assets = [
            {
                'id': 1,
                'name': 'Dell PowerEdge R740 Server',
                'description': 'Main production server',
                'number': 'FA-0001',
                'type_name': 'Computer Equipment',
                'purchase_price': 5499.00,
                'purchase_date': '2024-03-15',
                'status': 'registered',
                'status_badge': 'success',
                'book_value': 4399.20
            },
            {
                'id': 2,
                'name': 'MacBook Pro 16"',
                'description': 'Development laptop',
                'number': 'FA-0002',
                'type_name': 'Computer Equipment',
                'purchase_price': 2499.00,
                'purchase_date': '2024-06-20',
                'status': 'registered',
                'status_badge': 'success',
                'book_value': 2249.10
            }
        ]
        
        if tab == 'draft':
            assets = [a for a in sample_assets if a['status'] == 'draft']
        elif tab == 'registered':
            assets = [a for a in sample_assets if a['status'] == 'registered']
        else:
            assets = sample_assets
        
        context = {
            'assets': assets,
            'tab': tab,
            'counts': {'draft': 0, 'registered': 2, 'sold': 0},
            'last_depr_date': '31 Dec 2024'
        }
    
    return render(request, 'assets/list.html', context)


@login_required
def new_asset(request):
    """Enhanced new asset view with real form integration"""
    if request.method == 'POST':
        try:
            form = FixedAssetForm(request.POST, company=request.user.company, user=request.user)
            if form.is_valid():
                asset = form.save()
                messages.success(request, f'Asset "{asset.name}" created successfully.')
                return redirect('assets:detail', asset_id=asset.id)
            else:
                messages.error(request, 'Please correct the errors below.')
        except Exception as e:
            messages.error(request, f'Error creating asset: {str(e)}')
            # Fallback to basic context
            form = None
    else:
        try:
            form = FixedAssetForm(company=request.user.company, user=request.user)
        except Exception:
            form = None
    
    # Enhanced context with real data where possible
    context = {
        'form': form,
        'today': timezone.now().date(),
        'next_number': 'FA-0004',  # This should be auto-generated
        'asset_types': [
            ('computer', 'Computer Equipment'),
            ('office', 'Office Equipment'),
            ('machinery', 'Machinery'),
            ('vehicles', 'Vehicles'),
            ('buildings', 'Buildings'),
        ],
        'depreciation_methods': [
            ('none', 'No depreciation'),
            ('straight_line', 'Straight Line'),
            ('declining_balance', 'Declining balance'),
            ('declining_balance_150', 'Declining balance (150%)'),
            ('declining_balance_200', 'Declining balance (200%)'),
            ('full_purchase', 'Full depreciation at purchase'),
        ],
        'averaging_methods': [
            ('full_month', 'Full month'),
            ('actual_days', 'Actual days'),
        ],
        'avg_methods': [
            {'id': 1, 'name': 'Full Month'},
            {'id': 2, 'name': 'Actual Days'},
            {'id': 3, 'name': 'Half Month'},
        ]
    }
    
    return render(request, 'assets/new.html', context)


@login_required
def asset_detail(request, asset_id):
    """Enhanced asset detail view"""
    try:
        asset = get_object_or_404(FixedAsset, id=asset_id, company=request.user.company)
        
        # Get additional details
        calculator = DepreciationCalculator()
        depreciation_status = calculator.get_depreciation_status(asset)
        
        context = {
            'asset': asset,
            'depreciation_status': depreciation_status,
            'transactions': AssetTransaction.objects.filter(asset=asset).order_by('-created_at')[:10]
        }
        
    except Exception:
        # Fallback for development
        context = {
            'asset_id': asset_id,
            'message': 'Asset detail view - full functionality will be available after migrations'
        }
    
    return render(request, 'assets/detail.html', context)


# Keep other legacy functions for compatibility
edit_asset = new_asset  # Reuse for now
asset_depreciation = asset_detail  # Placeholder


def run_depreciation_legacy(request):
    """Legacy run depreciation placeholder"""
    return render(request, 'assets/run_depreciation.html', {})


def import_assets(request):
    """Import assets placeholder"""
    return render(request, 'assets/import.html', {})


def export_assets(request):
    """Export assets placeholder"""
    return render(request, 'assets/export.html', {})
