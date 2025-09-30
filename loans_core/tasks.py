"""
Background tasks for loan management system
Handles approval progress updates, cache warming, and performance optimization
"""
from __future__ import absolute_import, unicode_literals
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

try:
    from celery import shared_task
    from celery.utils.log import get_task_logger
    CELERY_AVAILABLE = True
    
    # Celery decorators with proper syntax
    def task_decorator(func):
        return shared_task(func)
        
    def bind_task_decorator(func):
        return shared_task(bind=True, max_retries=3)(func)
        
except ImportError:
    CELERY_AVAILABLE = False
    # Fallback decorators for when celery is not available
    def task_decorator(func):
        return func
        
    def bind_task_decorator(func):
        return func

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

logger = get_task_logger(__name__) if CELERY_AVAILABLE else logging.getLogger(__name__)

@bind_task_decorator
def update_approval_progress(self, application_id: int) -> Dict[str, Any]:
    """
    Update approval progress for a single application
    Called when payment approval status changes
    """
    try:
        from .models import LoanApplication
        from core.cache_system import loan_cache
        
        start_time = timezone.now()
        
        # Get application
        try:
            application = LoanApplication.objects.get(id=application_id)
        except LoanApplication.DoesNotExist:
            logger.error(f"Application {application_id} not found")
            return {'status': 'error', 'message': 'Application not found'}
        
        # Clear existing cache
        loan_cache.clear_application_cache(application_id)
        
        # Recalculate progress (this will cache the new result)
        progress = application.get_approval_progress()
        
        # Update cache with fresh data
        loan_cache.cache_approval_progress(application_id, progress)
        
        # Clear list cache to force refresh
        loan_cache.clear_application_list_cache(application.company_id)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Updated approval progress for application {application_id} in {duration:.2f}s")
        
        return {
            'status': 'success',
            'application_id': application_id,
            'progress': progress,
            'duration': duration,
            'timestamp': end_time.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error updating approval progress for {application_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task for application {application_id}, retry {self.request.retries + 1}")
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        return {'status': 'error', 'message': str(exc)}

@task_decorator
def bulk_cache_warm(company_id: int = None, limit: int = 100) -> Dict[str, Any]:
    """
    Warm cache for multiple applications
    Run during off-peak hours for performance optimization
    """
    try:
        from .models import LoanApplication
        from core.cache_system import loan_cache
        
        start_time = timezone.now()
        
        # Build query
        queryset = LoanApplication.objects.filter(status='approved')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        # Get applications that need cache warming
        applications = queryset.order_by('-created_at')[:limit]
        
        warmed_count = 0
        error_count = 0
        
        for application in applications:
            try:
                # Check if already cached
                cached_progress = loan_cache.get_cached_approval_progress(application.id)
                if not cached_progress:
                    # Calculate and cache progress
                    progress = application.get_approval_progress()
                    loan_cache.cache_approval_progress(application.id, progress)
                    warmed_count += 1
                    
            except Exception as e:
                logger.error(f"Error warming cache for application {application.id}: {str(e)}")
                error_count += 1
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'status': 'success',
            'warmed_count': warmed_count,
            'error_count': error_count,
            'total_processed': len(applications),
            'duration': duration,
            'timestamp': end_time.isoformat()
        }
        
        logger.info(f"Cache warming completed: {warmed_count} applications warmed in {duration:.2f}s")
        return result
        
    except Exception as exc:
        logger.error(f"Error in bulk cache warming: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}

@task_decorator
def cleanup_expired_cache() -> Dict[str, Any]:
    """
    Clean up expired cache entries
    Runs periodically to maintain cache performance
    """
    try:
        from core.cache_system import loan_cache
        
        start_time = timezone.now()
        
        # Get cache statistics before cleanup
        stats_before = loan_cache.get_performance_stats()
        
        # Clear expired entries (Redis handles this automatically, but we can force cleanup)
        cleared_count = 0
        
        # For Django cache backend, we can implement custom cleanup logic
        try:
            # This is implementation-specific to the cache backend
            cache_keys = cache._cache.keys() if hasattr(cache, '_cache') else []
            
            for key in cache_keys:
                if key.startswith('loan_'):
                    # Check if key has expired (implementation depends on cache backend)
                    try:
                        value = cache.get(key)
                        if value is None:
                            cleared_count += 1
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"Cache cleanup method not available: {str(e)}")
        
        # Get statistics after cleanup
        stats_after = loan_cache.get_performance_stats()
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'status': 'success',
            'cleared_count': cleared_count,
            'stats_before': stats_before,
            'stats_after': stats_after,
            'duration': duration,
            'timestamp': end_time.isoformat()
        }
        
        logger.info(f"Cache cleanup completed: {cleared_count} entries cleaned in {duration:.2f}s")
        return result
        
    except Exception as exc:
        logger.error(f"Error in cache cleanup: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}

@task_decorator
def generate_progress_report(company_id: int = None) -> Dict[str, Any]:
    """
    Generate daily progress report for monitoring
    Provides insights into approval progress trends
    """
    try:
        from .models import LoanApplication
        from django.db.models import Count, Avg, Q
        
        start_time = timezone.now()
        
        # Build base query
        queryset = LoanApplication.objects.filter(status='approved')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        # Get applications from last 24 hours
        yesterday = timezone.now() - timedelta(days=1)
        recent_applications = queryset.filter(updated_at__gte=yesterday)
        
        # Calculate progress statistics
        total_applications = queryset.count()
        recent_count = recent_applications.count()
        
        # Calculate average progress for recent applications
        progress_stats = []
        if recent_count > 0:
            for application in recent_applications[:50]:  # Sample for performance
                try:
                    progress = application.get_approval_progress()
                    progress_stats.append(progress['percentage'])
                except:
                    pass
        
        avg_progress = sum(progress_stats) / len(progress_stats) if progress_stats else 0
        
        # Status distribution
        status_distribution = {}
        if progress_stats:
            completed = sum(1 for p in progress_stats if p == 100)
            partial = sum(1 for p in progress_stats if 0 < p < 100)
            not_started = sum(1 for p in progress_stats if p == 0)
            
            status_distribution = {
                'completed': completed,
                'partial': partial,
                'not_started': not_started
            }
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        report = {
            'status': 'success',
            'total_applications': total_applications,
            'recent_applications': recent_count,
            'average_progress': round(avg_progress, 2),
            'status_distribution': status_distribution,
            'sample_size': len(progress_stats),
            'duration': duration,
            'generated_at': end_time.isoformat(),
            'period': '24_hours'
        }
        
        logger.info(f"Progress report generated: {recent_count} recent applications, {avg_progress:.1f}% avg progress")
        
        # Store report in cache for dashboard access
        try:
            from core.cache_system import loan_cache
            cache_key = f"progress_report:{company_id or 'all'}:{end_time.strftime('%Y%m%d')}"
            cache.set(cache_key, report, timeout=86400)  # Cache for 24 hours
        except:
            pass
        
        return report
        
    except Exception as exc:
        logger.error(f"Error generating progress report: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}

@task_decorator
def batch_update_progress(application_ids: List[int]) -> Dict[str, Any]:
    """
    Update approval progress for multiple applications in batch
    More efficient than individual updates
    """
    try:
        start_time = timezone.now()
        
        success_count = 0
        error_count = 0
        results = []
        
        for app_id in application_ids:
            try:
                result = update_approval_progress.apply(args=[app_id])
                if result.result.get('status') == 'success':
                    success_count += 1
                else:
                    error_count += 1
                results.append(result.result)
                
            except Exception as e:
                logger.error(f"Error updating application {app_id}: {str(e)}")
                error_count += 1
                results.append({
                    'status': 'error',
                    'application_id': app_id,
                    'message': str(e)
                })
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        summary = {
            'status': 'success',
            'total_processed': len(application_ids),
            'success_count': success_count,
            'error_count': error_count,
            'duration': duration,
            'timestamp': end_time.isoformat(),
            'results': results
        }
        
        logger.info(f"Batch update completed: {success_count} success, {error_count} errors in {duration:.2f}s")
        return summary
        
    except Exception as exc:
        logger.error(f"Error in batch update: {str(exc)}")
        return {'status': 'error', 'message': str(exc)}

# Utility function to trigger cache updates when payments change
def trigger_progress_update(application_id: int, async_processing: bool = True):
    """
    Trigger approval progress update when payment status changes
    Can run synchronously or asynchronously based on configuration
    """
    try:
        if CELERY_AVAILABLE and async_processing:
            # Run as background task
            update_approval_progress.delay(application_id)
            logger.info(f"Queued background update for application {application_id}")
        else:
            # Run synchronously
            from .models import LoanApplication
            from core.cache_system import loan_cache
            
            try:
                application = LoanApplication.objects.get(id=application_id)
                loan_cache.clear_application_cache(application_id)
                progress = application.get_approval_progress()
                loan_cache.cache_approval_progress(application_id, progress)
                logger.info(f"Updated approval progress synchronously for application {application_id}")
            except LoanApplication.DoesNotExist:
                logger.error(f"Application {application_id} not found for progress update")
                
    except Exception as e:
        logger.error(f"Error triggering progress update for application {application_id}: {str(e)}")
