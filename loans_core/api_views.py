"""
Advanced API views for loan system Phase 3
Provides AJAX endpoints for lazy loading and real-time updates
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from typing import Dict, List, Any

from .models import LoanApplication
from .tasks import trigger_progress_update

logger = logging.getLogger(__name__)

# Debug view for testing (remove in production)
@require_http_methods(["GET"])
def debug_progress_api(request, application_id):
    """Debug API without authentication"""
    try:
        application = LoanApplication.objects.get(id=application_id)
        progress_data = application.get_approval_progress()
        return JsonResponse({
            'status': 'success',
            'application_id': application_id,
            'progress': progress_data,
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def application_progress_api(request, application_id):
    """
    Get approval progress for a single application
    Used by lazy loading frontend
    """
    try:
        application = LoanApplication.objects.get(
            id=application_id,
            company=request.user.company
        )
        
        progress_data = application.get_approval_progress()
        
        return JsonResponse({
            'status': 'success',
            'application_id': application_id,
            'progress': progress_data,
        })
        
    except LoanApplication.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Application not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting progress for application {application_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def batch_progress_api(request):
    """
    Get approval progress for multiple applications
    Optimized for batch processing
    """
    try:
        data = json.loads(request.body)
        application_ids = data.get('application_ids', [])
        
        if not application_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'No application IDs provided'
            }, status=400)
        
        # Limit batch size for performance
        if len(application_ids) > 50:
            application_ids = application_ids[:50]
        
        applications = LoanApplication.objects.filter(
            id__in=application_ids,
            company=request.user.company
        ).select_related('company')
        
        results = []
        for application in applications:
            try:
                progress_data = application.get_approval_progress()
                results.append({
                    'status': 'success',
                    'application_id': application.id,
                    'progress': progress_data,
                })
            except Exception as e:
                logger.error(f"Error getting progress for application {application.id}: {str(e)}")
                results.append({
                    'status': 'error',
                    'application_id': application.id,
                    'message': str(e)
                })
        
        return JsonResponse(results, safe=False)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in batch progress API: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def applications_list_api(request):
    """
    Paginated applications list for infinite scroll
    """
    try:
        # Get pagination parameters
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 20))
        
        # Limit the maximum items per request
        limit = min(limit, 100)
        
        # Get search and filter parameters
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '')
        progress_filter = request.GET.get('progress', '')
        
        # Build query
        queryset = LoanApplication.objects.filter(
            company=request.user.company,
            status='approved'
        ).select_related('company').order_by('-created_at')
        
        # Apply search
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(id__icontains=search) |
                Q(loan_amount__icontains=search)
            )
        
        # Apply status filter
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Get total count for pagination
        total_count = queryset.count()
        
        # Apply pagination
        applications = queryset[offset:offset + limit]
        
        # Serialize data
        applications_data = []
        for app in applications:
            applications_data.append({
                'id': app.id,
                'customer': getattr(app, 'customer_name', 'N/A'),
                'loan_amount': str(getattr(app, 'loan_amount', 0)),
                'status': app.status,
                'created_at': app.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        
        # Check if there are more items
        has_more = (offset + limit) < total_count
        
        response_data = {
            'status': 'success',
            'applications': applications_data,
            'pagination': {
                'offset': offset,
                'limit': limit,
                'total': total_count,
                'has_more': has_more,
                'next_offset': offset + limit if has_more else None
            }
        }
        
        return JsonResponse(response_data)
        
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid pagination parameters'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in applications list API: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)

@method_decorator(login_required, name='dispatch')
class ApplicationProgressUpdateView(View):
    """
    Handle progress update webhooks and triggers
    """
    
    def post(self, request, application_id):
        """
        Trigger progress update for an application
        Usually called when payment status changes
        """
        try:
            application = LoanApplication.objects.get(
                id=application_id,
                company=request.user.company
            )
            
            # Get update parameters
            data = json.loads(request.body) if request.body else {}
            force_refresh = data.get('force_refresh', False)
            async_processing = data.get('async_processing', True)
            
            if force_refresh:
                # Clear cache for this application
                try:
                    from core.cache_system import loan_cache
                    loan_cache.clear_application_cache(application_id)
                except ImportError:
                    pass
            
            # Trigger progress update
            trigger_progress_update(application_id, async_processing)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Progress update triggered',
                'application_id': application_id,
                'async_processing': async_processing
            })
            
        except LoanApplication.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Application not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error triggering progress update for application {application_id}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Internal server error'
            }, status=500)

@login_required
@require_http_methods(["GET"])
def system_performance_api(request):
    """
    Get system performance metrics for monitoring
    """
    try:
        from core.cache_system import loan_cache
        
        # Get cache performance stats
        cache_stats = loan_cache.get_performance_stats()
        
        # Get database performance metrics
        from django.db import connection
        
        db_queries = len(connection.queries) if hasattr(connection, 'queries') else 0
        
        performance_data = {
            'status': 'success',
            'cache_stats': cache_stats,
            'database_queries': db_queries,
            'active_users': request.user.company.users.filter(is_active=True).count(),
            'system_status': 'healthy'
        }
        
        return JsonResponse(performance_data)
        
    except Exception as e:
        logger.error(f"Error getting system performance: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def cache_warm_api(request):
    """
    Trigger cache warming for improved performance
    """
    try:
        data = json.loads(request.body) if request.body else {}
        company_id = request.user.company.id
        limit = min(int(data.get('limit', 100)), 500)  # Max 500 items
        
        # Trigger background cache warming
        from .tasks import bulk_cache_warm
        
        try:
            # Try to run as background task
            task = bulk_cache_warm.delay(company_id, limit)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Cache warming started',
                'task_id': task.id,
                'limit': limit
            })
            
        except Exception:
            # Fallback to synchronous execution
            result = bulk_cache_warm(company_id, limit)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Cache warming completed',
                'result': result,
                'limit': limit
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error triggering cache warming: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def progress_dashboard_api(request):
    """
    Get dashboard data for progress monitoring
    """
    try:
        company = request.user.company
        
        # Get basic statistics
        total_applications = LoanApplication.objects.filter(
            company=company,
            status='approved'
        ).count()
        
        # Sample applications for progress calculation
        sample_applications = LoanApplication.objects.filter(
            company=company,
            status='approved'
        ).order_by('-updated_at')[:100]
        
        progress_distribution = {
            'completed': 0,
            'partial': 0,
            'not_started': 0,
            'pending_disbursement': 0
        }
        
        total_progress = 0
        sample_count = 0
        
        for application in sample_applications:
            try:
                progress = application.get_approval_progress()
                status = progress.get('status', 'not_started')
                progress_distribution[status] += 1
                total_progress += progress.get('percentage', 0)
                sample_count += 1
            except Exception:
                pass
        
        average_progress = total_progress / sample_count if sample_count > 0 else 0
        
        dashboard_data = {
            'status': 'success',
            'statistics': {
                'total_applications': total_applications,
                'average_progress': round(average_progress, 2),
                'progress_distribution': progress_distribution,
                'sample_size': sample_count
            },
            'timestamp': request.META.get('HTTP_X_TIMESTAMP', 'unknown')
        }
        
        return JsonResponse(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)
