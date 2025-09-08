from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Journal, JournalLine
from coa.models import Account
import json


def manual_journal_list(request):
    """Display list of manual journals"""
    # Get filters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    period_filter = request.GET.get('period', '')
    
    # Base queryset
    journals = Journal.objects.select_related('created_by').prefetch_related('lines')
    
    # Apply search filter
    if search_query:
        journals = journals.filter(
            Q(narration__icontains=search_query) |
            Q(reference__icontains=search_query) |
            Q(id__icontains=search_query.replace('JE', '').replace('#', ''))
        )
    
    # Apply status filter
    if status_filter:
        journals = journals.filter(status=status_filter)
    
    # Apply period filter
    if period_filter == 'this_month':
        from datetime import date
        today = date.today()
        journals = journals.filter(
            date__year=today.year, 
            date__month=today.month
        )
    elif period_filter == 'this_year':
        from datetime import date
        today = date.today()
        journals = journals.filter(date__year=today.year)
    
    # Calculate stats
    posted_count = journals.filter(status='posted').count()
    draft_count = journals.filter(status='draft').count()
    
    # Pagination
    paginator = Paginator(journals, 20)
    page_number = request.GET.get('page')
    journals_page = paginator.get_page(page_number)
    
    context = {
        'journals': journals_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'period_filter': period_filter,
        'posted_count': posted_count,
        'draft_count': draft_count,
    }
    
    return render(request, 'journal/list.html', context)


def new_journal(request):
    """Create new manual journal"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create journal
            journal = Journal.objects.create(
                narration=data.get('narration', ''),
                date=data.get('date'),
                auto_reversing_date=data.get('reversing_date') or None,
                cash_basis=data.get('cash_basis', True),
                amount_mode=data.get('amount_mode', 'No Tax'),
                status=data.get('status', 'draft'),
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # Create journal lines
            for i, line_data in enumerate(data.get('lines', [])):
                JournalLine.objects.create(
                    journal=journal,
                    description=line_data.get('description', ''),
                    account_code=line_data.get('account', ''),
                    tax_rate=line_data.get('tax') or None,
                    debit=line_data.get('debit', 0),
                    credit=line_data.get('credit', 0),
                    line_order=i
                )
            
            return JsonResponse({
                'success': True,
                'journal_id': journal.id,
                'message': f'Journal JE{journal.id:04d} created successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # GET request - show form
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    context = {
        'accounts': accounts,
        'today': timezone.now().date(),
    }
    
    return render(request, 'journal/new.html', context)


def journal_detail(request, journal_id):
    """View journal details"""
    journal = get_object_or_404(Journal, id=journal_id)
    
    context = {
        'journal': journal,
    }
    
    return render(request, 'journal/detail.html', context)


def edit_journal(request, journal_id):
    """Edit existing journal (only drafts)"""
    journal = get_object_or_404(Journal, id=journal_id)
    
    if journal.status != 'draft':
        messages.error(request, 'Only draft journals can be edited.')
        return redirect('journal:manual_journal')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Update journal
            journal.narration = data.get('narration', '')
            journal.date = data.get('date')
            journal.auto_reversing_date = data.get('reversing_date') or None
            journal.cash_basis = data.get('cash_basis', True)
            journal.amount_mode = data.get('amount_mode', 'No Tax')
            journal.status = data.get('status', 'draft')
            journal.save()
            
            # Delete existing lines and recreate
            journal.lines.all().delete()
            
            for i, line_data in enumerate(data.get('lines', [])):
                JournalLine.objects.create(
                    journal=journal,
                    description=line_data.get('description', ''),
                    account_code=line_data.get('account', ''),
                    tax_rate=line_data.get('tax') or None,
                    debit=line_data.get('debit', 0),
                    credit=line_data.get('credit', 0),
                    line_order=i
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Journal JE{journal.id:04d} updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # GET request - show form with existing data
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    context = {
        'journal': journal,
        'accounts': accounts,
    }
    
    return render(request, 'journal/edit_journal.html', context)


def duplicate_journal(request, journal_id):
    """Duplicate existing journal as draft"""
    original = get_object_or_404(Journal, id=journal_id)
    
    # Create duplicate
    duplicate = Journal.objects.create(
        narration=f"Copy of {original.narration}",
        date=timezone.now().date(),
        cash_basis=original.cash_basis,
        amount_mode=original.amount_mode,
        status='draft',
        created_by=request.user if request.user.is_authenticated else None
    )
    
    # Duplicate lines
    for line in original.lines.all():
        JournalLine.objects.create(
            journal=duplicate,
            description=line.description,
            account_code=line.account_code,
            tax_rate=line.tax_rate,
            debit=line.debit,
            credit=line.credit,
            line_order=line.line_order
        )
    
    messages.success(request, f'Journal duplicated as JE{duplicate.id:04d}')
    return redirect('journal:edit_journal', journal_id=duplicate.id)


def post_journal_api(request, journal_id):
    """API endpoint to post journal"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    journal = get_object_or_404(Journal, id=journal_id)
    
    if journal.status != 'draft':
        return JsonResponse({'error': 'Only draft journals can be posted'}, status=400)
    
    if not journal.is_balanced:
        return JsonResponse({'error': 'Journal is not balanced'}, status=400)
    
    if not journal.lines.exists():
        return JsonResponse({'error': 'Journal has no lines'}, status=400)
    
    # Post the journal
    journal.status = 'posted'
    journal.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Journal JE{journal.id:04d} posted successfully'
    })


def reverse_journal_api(request, journal_id):
    """API endpoint to reverse journal"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    journal = get_object_or_404(Journal, id=journal_id)
    
    if journal.status != 'posted':
        return JsonResponse({'error': 'Only posted journals can be reversed'}, status=400)
    
    # Create reversing journal
    reversing_journal = Journal.objects.create(
        narration=f"Reversing {journal.narration}",
        date=timezone.now().date(),
        cash_basis=journal.cash_basis,
        amount_mode=journal.amount_mode,
        status='posted',
        created_by=request.user if request.user.is_authenticated else None
    )
    
    # Create reversing lines (swap debits and credits)
    for line in journal.lines.all():
        JournalLine.objects.create(
            journal=reversing_journal,
            description=f"Reversing {line.description}",
            account_code=line.account_code,
            tax_rate=line.tax_rate,
            debit=line.credit,  # Swap
            credit=line.debit,  # Swap
            line_order=line.line_order
        )
    
    # Mark original as reversed
    journal.status = 'reversed'
    journal.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Journal reversed as JE{reversing_journal.id:04d}'
    })


def delete_journal_api(request, journal_id):
    """API endpoint to delete journal"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    journal = get_object_or_404(Journal, id=journal_id)
    
    if journal.status != 'draft':
        return JsonResponse({'error': 'Only draft journals can be deleted'}, status=400)
    
    journal.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Journal deleted successfully'
    })
