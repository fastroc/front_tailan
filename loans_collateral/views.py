from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json

from .models import Collateral, CollateralType
from loans_core.models import LoanApplication

# AJAX Endpoints
@login_required
def search_loan_applications(request):
    """AJAX endpoint for searching loan applications with hybrid search"""
    if request.method == 'GET':
        query = request.GET.get('query', '').strip()
        
        if len(query) < 1:  # Show results even for single character
            # If no query, return all available loan applications
            loan_apps = LoanApplication.objects.filter(
                status__in=['submitted', 'under_review', 'approved']
            ).select_related('customer', 'loan')[:20]  # Show more results
        else:
            # Search primarily by customer first name, then other fields
            loan_apps = LoanApplication.objects.filter(
                Q(customer__first_name__icontains=query) |
                Q(customer__last_name__icontains=query) |
                Q(customer__email__icontains=query) |
                Q(loan__loan_number__icontains=query) |
                Q(application_id__icontains=query),
                status__in=['submitted', 'under_review', 'approved']
            ).select_related('customer', 'loan')[:15]  # More results
        
        results = []
        for app in loan_apps:
            # Try to get the associated loan number
            loan_number = None
            try:
                loan = app.loan
                if loan:
                    loan_number = loan.loan_number
            except Exception:
                pass
            
            # Format the display text
            if loan_number:
                display_text = f"{loan_number} - {app.customer.full_name} (${app.requested_amount:,.0f})"
            else:
                display_text = f"{app.application_id} - {app.customer.full_name} (${app.requested_amount:,.0f})"
            
            results.append({
                'id': app.id,
                'text': display_text,
                'loan_number': loan_number or app.application_id,
                'customer_name': app.customer.full_name,
                'amount': f"${app.requested_amount:,.0f}"
            })
        
        return JsonResponse({'results': results})
    
    return JsonResponse({'error': 'Invalid request method'})

# Dashboard and Main Views
@login_required
def collateral_dashboard(request):
    """Main collateral management dashboard"""
    
    # Statistics
    total_collateral = Collateral.objects.count()
    total_value = Collateral.objects.aggregate(
        declared=Sum('declared_value'),
        market=Sum('market_value'),
        loan=Sum('loan_value')
    )
    
    # Status breakdown
    status_breakdown = Collateral.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Recent activities
    recent_collateral = Collateral.objects.select_related(
        'collateral_type', 'loan_application__customer'
    ).order_by('-created_at')[:10]
    
    # Risk analysis
    risk_breakdown = CollateralType.objects.values('risk_level').annotate(
        count=Count('collateral'),
        total_value=Sum('collateral__loan_value')
    )
    
    # Collateral types with counts
    type_stats = CollateralType.objects.annotate(
        item_count=Count('collateral')
    ).order_by('-item_count')[:5]
    
    context = {
        'total_collateral': total_collateral,
        'total_values': total_value,
        'status_breakdown': status_breakdown,
        'recent_collateral': recent_collateral,
        'risk_breakdown': risk_breakdown,
        'type_stats': type_stats,
    }
    
    return render(request, 'loans_collateral/dashboard.html', context)


# Collateral Type Management
@login_required
def collateral_type_list(request):
    """List all collateral types"""
    types = CollateralType.objects.annotate(
        item_count=Count('collateral')
    ).order_by('category', 'name')
    
    context = {
        'collateral_types': types,
    }
    return render(request, 'loans_collateral/type_list.html', context)


@login_required
def collateral_type_detail(request, pk):
    """View collateral type details"""
    collateral_type = get_object_or_404(CollateralType, pk=pk)
    related_items = collateral_type.collateral_set.select_related(
        'loan_application__customer'
    ).order_by('-created_at')
    
    context = {
        'collateral_type': collateral_type,
        'related_items': related_items,
    }
    return render(request, 'loans_collateral/type_detail.html', context)


# Collateral Item Management
@login_required
def collateral_list(request):
    """List all collateral items with filtering"""
    collateral_items = Collateral.objects.select_related(
        'collateral_type', 
        'loan_application__customer'
    ).order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    search = request.GET.get('search')
    
    if status_filter:
        collateral_items = collateral_items.filter(status=status_filter)
    
    if type_filter:
        collateral_items = collateral_items.filter(collateral_type_id=type_filter)
    
    if search:
        collateral_items = collateral_items.filter(
            Q(title__icontains=search) |
            Q(collateral_id__icontains=search) |
            Q(description__icontains=search) |
            Q(loan_application__customer__first_name__icontains=search) |
            Q(loan_application__customer__last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(collateral_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filter options
    collateral_types = CollateralType.objects.filter(is_active=True)
    status_choices = Collateral.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'collateral_types': collateral_types,
        'status_choices': status_choices,
        'current_filters': {
            'status': status_filter,
            'type': type_filter,
            'search': search,
        }
    }
    
    return render(request, 'loans_collateral/list.html', context)


@login_required
def collateral_detail(request, pk):
    """View collateral item details"""
    collateral = get_object_or_404(
        Collateral.objects.select_related(
            'collateral_type',
            'loan_application__customer',
            'verified_by'
        ),
        pk=pk
    )
    
    # Get related data
    valuations = collateral.valuations.order_by('-valuation_date')
    documents = collateral.documents.order_by('-uploaded_at')
    
    context = {
        'collateral': collateral,
        'valuations': valuations,
        'documents': documents,
    }
    
    return render(request, 'loans_collateral/detail.html', context)


# Collateral Actions
@login_required
def collateral_verify(request, pk):
    """Verify a collateral item"""
    collateral = get_object_or_404(Collateral, pk=pk)
    
    if request.method == 'POST':
        notes = request.POST.get('verification_notes', '')
        collateral.status = 'verified'
        collateral.verification_date = timezone.now()
        collateral.verification_notes = notes
        collateral.verified_by = request.user
        collateral.save()
        
        messages.success(request, f'Collateral {collateral.collateral_id} has been verified.')
        return redirect('loans_collateral:collateral_detail', pk=collateral.pk)
    
    return render(request, 'loans_collateral/verify.html', {'collateral': collateral})


@login_required
def collateral_approve(request, pk):
    """Approve collateral for loan usage"""
    collateral = get_object_or_404(Collateral, pk=pk)
    
    if request.method == 'POST':
        if collateral.status != 'verified':
            messages.error(request, 'Collateral must be verified before approval.')
            return redirect('loans_collateral:collateral_detail', pk=collateral.pk)
        
        collateral.status = 'approved'
        collateral.save()
        
        messages.success(request, f'Collateral {collateral.collateral_id} has been approved.')
        return redirect('loans_collateral:collateral_detail', pk=collateral.pk)
    
    return render(request, 'loans_collateral/approve.html', {'collateral': collateral})


# Application-specific collateral views
@login_required
def application_collateral_list(request, application_id):
    """List collateral for a specific loan application"""
    application = get_object_or_404(LoanApplication, pk=application_id)
    collateral_items = application.collateral_items.select_related('collateral_type')
    
    # Calculate totals
    total_declared = collateral_items.aggregate(Sum('declared_value'))['declared_value__sum'] or 0
    total_market = collateral_items.aggregate(Sum('market_value'))['market_value__sum'] or 0
    total_loan = collateral_items.aggregate(Sum('loan_value'))['loan_value__sum'] or 0
    
    context = {
        'application': application,
        'collateral_items': collateral_items,
        'totals': {
            'declared': total_declared,
            'market': total_market,
            'loan': total_loan,
        },
        'coverage_ratio': (total_loan / application.requested_amount * 100) if application.requested_amount else 0,
    }
    
    return render(request, 'loans_collateral/application_list.html', context)


# API Views for AJAX functionality
@login_required
def api_collateral_type_details(request, type_id):
    """Get collateral type details for dynamic form updates"""
    try:
        collateral_type = CollateralType.objects.get(pk=type_id)
        data = {
            'category': collateral_type.category,
            'max_ltv': float(collateral_type.max_loan_to_value),
            'risk_level': collateral_type.risk_level,
            'requires_insurance': collateral_type.requires_insurance,
            'requires_valuation': collateral_type.requires_professional_valuation,
            'description': collateral_type.description,
        }
        return JsonResponse(data)
    except CollateralType.DoesNotExist:
        return JsonResponse({'error': 'Collateral type not found'}, status=404)


@login_required
def api_calculate_ltv(request):
    """Calculate loan-to-value ratio"""
    try:
        market_value = Decimal(request.GET.get('market_value', '0'))
        loan_amount = Decimal(request.GET.get('loan_amount', '0'))
        
        if market_value > 0:
            ltv_ratio = (loan_amount / market_value) * 100
            return JsonResponse({
                'ltv_ratio': float(ltv_ratio),
                'formatted_ltv': f"{ltv_ratio:.2f}%"
            })
        else:
            return JsonResponse({'error': 'Market value must be greater than 0'}, status=400)
    
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid input values'}, status=400)


# Reports
@login_required
def collateral_reports(request):
    """Main collateral reports page"""
    return render(request, 'loans_collateral/reports.html')


@login_required
def collateral_summary_report(request):
    """Generate collateral summary report"""
    # This will be expanded with actual report generation
    context = {
        'report_title': 'Collateral Summary Report',
        'generated_at': timezone.now(),
    }
    return render(request, 'loans_collateral/reports/summary.html', context)


@login_required
def collateral_create(request):
    """Create new collateral item"""
    from .forms import CollateralForm
    
    if request.method == 'POST':
        form = CollateralForm(request.POST)
        if form.is_valid():
            collateral = form.save()
            messages.success(request, f'Collateral {collateral.collateral_id} created successfully!')
            return redirect('loans_collateral:collateral_detail', pk=collateral.pk)
        else:
            # Add form errors to messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CollateralForm()
    
    context = {
        'form': form,
        'title': 'Add New Collateral',
        'submit_text': 'Create Collateral'
    }
    
    return render(request, 'loans_collateral/create.html', context)


@login_required  
def collateral_create_debug(request):
    """Debug version of collateral creation"""
    from .forms import CollateralForm
    
    if request.method == 'POST':
        form = CollateralForm(request.POST)
        if form.is_valid():
            collateral = form.save()
            messages.success(request, f'Collateral {collateral.collateral_id} created successfully!')
            return redirect('loans_collateral:collateral_detail', pk=collateral.pk)
        else:
            # Show detailed errors
            messages.error(request, 'Form validation failed. Check errors below.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CollateralForm()
    
    context = {
        'form': form,
        'title': 'Add New Collateral - Debug',
        'submit_text': 'Create Collateral'
    }
    
    return render(request, 'loans_collateral/create_debug.html', context)


@login_required
def collateral_update(request, pk):
    """Update/edit collateral item"""
    from .forms import CollateralForm
    
    collateral = get_object_or_404(Collateral, pk=pk)
    
    if request.method == 'POST':
        form = CollateralForm(request.POST, instance=collateral)
        if form.is_valid():
            updated_collateral = form.save()
            messages.success(request, f'Collateral {updated_collateral.collateral_id} updated successfully!')
            return redirect('loans_collateral:collateral_detail', pk=updated_collateral.pk)
    else:
        form = CollateralForm(instance=collateral)
    
    context = {
        'form': form,
        'collateral': collateral,
        'title': f'Edit {collateral.title}',
        'submit_text': 'Update Collateral'
    }
    
    return render(request, 'loans_collateral/update.html', context)


@login_required
def collateral_type_create(request):
    """Create collateral type - placeholder"""
    messages.info(request, 'Collateral type creation form coming soon!')
    return redirect('loans_collateral:type_list')


@login_required
def collateral_type_edit(request, pk):
    """Edit collateral type - placeholder"""
    messages.info(request, 'Collateral type editing form coming soon!')
    return redirect('loans_collateral:type_detail', pk=pk)


@login_required
def collateral_delete(request, pk):
    """Delete collateral item with confirmation"""
    collateral = get_object_or_404(Collateral, pk=pk)
    
    # Allow all logged-in users to delete any collateral
    can_force_delete = True
    force_delete = request.GET.get('force', False) or request.POST.get('force_delete', False)
    
    if request.method == 'POST':
        # Store details before deletion for success message
        collateral_id = collateral.collateral_id
        collateral_title = collateral.title
        customer_name = collateral.loan_application.customer.full_name
        
        # Check if collateral has protected status (for warning only)
        is_protected = collateral.status in ['approved', 'verified', 'valued']
        
        if is_protected and not force_delete:
            messages.warning(
                request, 
                f'Collateral {collateral_id} - {collateral_title} has protected status "{collateral.status}". '
                'Please confirm force deletion to proceed.'
            )
            return redirect('loans_collateral:collateral_delete', pk=pk)
        
        try:
            # Perform the deletion
            collateral.delete()
            
            success_message = f'Collateral "{collateral_title}" ({collateral_id}) for customer {customer_name} has been successfully deleted.'
            if force_delete:
                success_message += ' [FORCED DELETION - Protected status bypassed]'
            
            messages.success(request, success_message)
            
            # Redirect to collateral list
            return redirect('loans_collateral:collateral_list')
            
        except Exception as e:
            messages.error(
                request, 
                f'Error deleting collateral: {str(e)}. Please try again or contact support.'
            )
            return redirect('loans_collateral:collateral_detail', pk=pk)
    
    # GET request - show confirmation page
    is_protected = collateral.status in ['approved', 'verified', 'valued']
    
    context = {
        'collateral': collateral,
        'title': f'Delete {collateral.title}',
        'customer_name': collateral.loan_application.customer.full_name,
        'loan_number': getattr(collateral.loan_application.loan, 'loan_number', collateral.loan_application.application_id) if hasattr(collateral.loan_application, 'loan') else collateral.loan_application.application_id,
        'can_delete': True,  # Always allow deletion since we removed admin restrictions
        'status_warning': is_protected,
        'can_force_delete': can_force_delete,
        'is_protected': is_protected
    }
    
    return render(request, 'loans_collateral/delete_confirm.html', context)


@login_required
def collateral_bulk_delete(request):
    """Bulk delete multiple collateral items"""
    if request.method == 'POST':
        # Get selected collateral IDs
        selected_ids = request.POST.getlist('selected_collateral')
        force_delete = request.POST.get('force_bulk_delete', False)
        
        if not selected_ids:
            messages.warning(request, 'No collateral items selected for deletion.')
            return redirect('loans_collateral:collateral_list')
        
        # Allow all logged-in users to delete any collateral
        can_force_delete = True
        
        try:
            # Get selected collateral items
            collateral_items = Collateral.objects.filter(id__in=selected_ids)
            
            # Check permissions and status
            protected_items = []
            deletable_items = []
            
            for item in collateral_items:
                if item.status in ['approved', 'verified', 'valued']:
                    if can_force_delete and force_delete:
                        deletable_items.append(item)
                    else:
                        protected_items.append(item)
                else:
                    deletable_items.append(item)
            
            if protected_items and not force_delete:
                protected_names = [f"{item.collateral_id} - {item.title}" for item in protected_items]
                error_msg = f'Cannot delete {len(protected_items)} protected items: {", ".join(protected_names[:3])}'
                if len(protected_names) > 3:
                    error_msg += f' and {len(protected_names) - 3} more...'
                error_msg += ' Use Force Delete option to override protection.'
                messages.error(request, error_msg)
            
            if deletable_items:
                deleted_count = len(deletable_items)
                deleted_names = [f"{item.collateral_id} - {item.title}" for item in deletable_items]
                
                # Perform bulk deletion
                collateral_items.filter(id__in=[item.id for item in deletable_items]).delete()
                
                success_msg = f'Successfully deleted {deleted_count} collateral item(s): {", ".join(deleted_names[:3])}'
                if len(deleted_names) > 3:
                    success_msg += f' and {len(deleted_names) - 3} more...'
                if force_delete:
                    success_msg += ' [FORCED DELETION - Protected items included]'
                
                messages.success(request, success_msg)
            
            if not deletable_items:
                if protected_items:
                    messages.warning(request, 'No items were deleted. All selected items are protected.')
                else:
                    messages.warning(request, 'No valid items found for deletion.')
                
        except Exception as e:
            messages.error(request, f'Error during bulk deletion: {str(e)}')
    
    return redirect('loans_collateral:collateral_list')


@login_required
def collateral_reject(request, pk):
    """Reject collateral - placeholder"""
    messages.info(request, 'Collateral rejection form coming soon!')
    return redirect('loans_collateral:collateral_detail', pk=pk)


@login_required
def collateral_release(request, pk):
    """Release collateral - placeholder"""
    messages.info(request, 'Collateral release form coming soon!')
    return redirect('loans_collateral:collateral_detail', pk=pk)


@login_required
def application_collateral_add(request, application_id):
    """Add collateral to application - placeholder"""
    messages.info(request, 'Add collateral form coming soon!')
    return redirect('loans_collateral:application_list', application_id=application_id)


# Valuation views - placeholders
@login_required
def collateral_valuation_list(request, collateral_id):
    """List valuations for collateral - placeholder"""
    messages.info(request, 'Valuation list coming soon!')
    return redirect('loans_collateral:collateral_detail', pk=collateral_id)


@login_required
def collateral_valuation_create(request, collateral_id):
    """Create new valuation - placeholder"""
    messages.info(request, 'Valuation creation form coming soon!')
    return redirect('loans_collateral:collateral_detail', pk=collateral_id)


@login_required
def collateral_valuation_detail(request, pk):
    """Valuation detail - placeholder"""
    messages.info(request, 'Valuation details coming soon!')
    return redirect('loans_collateral:collateral_list')


@login_required
def collateral_valuation_edit(request, pk):
    """Edit valuation - placeholder"""
    messages.info(request, 'Valuation editing form coming soon!')
    return redirect('loans_collateral:collateral_list')


# Document views - placeholders
@login_required
def collateral_document_list(request, collateral_id):
    """List documents for collateral - placeholder"""
    messages.info(request, 'Document list coming soon!')
    return redirect('loans_collateral:collateral_detail', pk=collateral_id)


@login_required
def collateral_document_upload(request, collateral_id):
    """Upload document - placeholder"""
    messages.info(request, 'Document upload form coming soon!')
    return redirect('loans_collateral:collateral_detail', pk=collateral_id)


@login_required
def collateral_document_detail(request, pk):
    """Document detail - placeholder"""
    messages.info(request, 'Document details coming soon!')
    return redirect('loans_collateral:collateral_list')


@login_required
def collateral_document_delete(request, pk):
    """Delete document - placeholder"""
    messages.info(request, 'Document deletion confirmation coming soon!')
    return redirect('loans_collateral:collateral_list')


@login_required
def api_collateral_summary(request, pk):
    """Get collateral summary via API - placeholder"""
    return JsonResponse({'message': 'API endpoint coming soon!'})


@csrf_exempt
@login_required
def api_check_duplicates(request):
    """API endpoint to check for potential duplicate collaterals"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        from .duplicate_detector import detect_collateral_duplicates
        from loans_core.models import LoanApplication
        
        # Parse request data
        data = json.loads(request.body)
        
        # Log the received data for debugging
        print(f"API received data: {data}")
        
        # Get loan application if provided
        loan_app_id = data.get('loan_application')
        if loan_app_id:
            try:
                loan_application = LoanApplication.objects.get(id=loan_app_id)
                data['loan_application'] = loan_application
            except (LoanApplication.DoesNotExist, ValueError):
                print(f"Loan application not found: {loan_app_id}")
                pass
        
        # Get collateral type if provided
        collateral_type_id = data.get('collateral_type')
        if collateral_type_id:
            try:
                from .models import CollateralType
                collateral_type = CollateralType.objects.get(id=collateral_type_id)
                data['collateral_type'] = collateral_type
            except (CollateralType.DoesNotExist, ValueError):
                print(f"Collateral type not found: {collateral_type_id}")
                pass
        
        # Exclude current collateral if updating
        exclude_id = data.get('exclude_collateral_id')
        
        # Detect duplicates
        duplicate_results = detect_collateral_duplicates(
            data, 
            exclude_id=exclude_id
        )
        
        # Format results for JSON response
        formatted_results = {
            'total_count': duplicate_results['total_count'],
            'has_high_risk': duplicate_results['has_high_risk'],
            'exact_matches': [],
            'high_probability': [],
            'medium_probability': [],
            'low_probability': []
        }
        
        # Format each category
        for category in ['exact_matches', 'high_probability', 'medium_probability', 'low_probability']:
            for result in duplicate_results[category]:
                collateral = result['collateral']
                formatted_result = {
                    'collateral_id': collateral.collateral_id,
                    'title': collateral.title,
                    'customer_name': collateral.loan_application.customer.full_name,
                    'declared_value': float(collateral.declared_value),
                    'status': collateral.get_status_display(),
                    'created_at': collateral.created_at.strftime('%Y-%m-%d'),
                    'match_type': result['match_type'],
                    'confidence': round(result['confidence'] * 100, 1),
                    'reason': result['reason'],
                    'risk_level': result['risk_level'],
                    'detail_url': f"/loans/collateral/items/{collateral.pk}/"
                }
                
                # Add vehicle-specific details if available
                if collateral.vehicle_make:
                    formatted_result['vehicle_details'] = {
                        'make': collateral.vehicle_make,
                        'model': collateral.vehicle_model,
                        'year': collateral.vehicle_year,
                        'license_plate': collateral.vehicle_license_plate,
                        'vin': collateral.vehicle_vin
                    }
                
                formatted_results[category].append(formatted_result)
        
        return JsonResponse(formatted_results)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def collateral_risk_report(request):
    """Risk analysis report - placeholder"""
    messages.info(request, 'Risk analysis report coming soon!')
    return redirect('loans_collateral:reports')
