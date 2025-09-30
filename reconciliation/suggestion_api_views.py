"""
Smart Suggestion API Views

Django REST API endpoints for the smart suggestion system.
Provides real-time suggestions with match percentages.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
import json
import logging
from datetime import datetime

from reconciliation.smart_suggestion_service import SmartSuggestionService

logger = logging.getLogger(__name__)


class SmartSuggestionAPI:
    """API handler for smart suggestions"""
    
    def __init__(self):
        self.suggestion_service = SmartSuggestionService()
    
    def get_suggestions(self, request):
        """Get smart suggestions for a bank transaction description"""
        try:
            # Get parameters
            description = request.GET.get('description', '').strip()
            amount = float(request.GET.get('amount', 0))
            transaction_type = request.GET.get('transaction_type', 'auto')
            
            # Validate input
            if len(description) < 3:
                return JsonResponse({
                    'success': False,
                    'error': 'Description must be at least 3 characters',
                    'suggestions': []
                })
            
            # Get suggestions
            suggestions = self.suggestion_service.get_suggestions(
                description, amount, transaction_type
            )
            
            # Add API metadata
            response_data = {
                'success': True,
                'suggestions': suggestions,
                'total_suggestions': len(suggestions),
                'query': {
                    'description': description,
                    'amount': amount,
                    'transaction_type': transaction_type
                },
                'timestamp': datetime.now().isoformat(),
                'service_version': self.suggestion_service.version
            }
            
            # Log successful request
            logger.info(f"Suggestions generated: {len(suggestions)} for '{description[:30]}...'")
            
            return JsonResponse(response_data)
            
        except ValueError as e:
            logger.warning(f"Invalid input for suggestions: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid input parameters',
                'suggestions': []
            }, status=400)
            
        except Exception as e:
            logger.error(f"Suggestion API error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error',
                'suggestions': []
            }, status=500)
    
    def get_quick_suggestions(self, request):
        """Get quick suggestions for autocomplete"""
        try:
            query = request.GET.get('q', '').strip()
            limit = int(request.GET.get('limit', 5))
            
            if len(query) < 3:
                return JsonResponse([])
            
            quick_suggestions = self.suggestion_service.get_quick_suggestions(query, limit)
            
            return JsonResponse(quick_suggestions, safe=False)
            
        except Exception as e:
            logger.error(f"Quick suggestions error: {e}")
            return JsonResponse([])
    
    def get_suggestion_details(self, request):
        """Get detailed information about a specific suggestion"""
        try:
            suggestion_id = request.GET.get('suggestion_id')
            
            if not suggestion_id:
                return JsonResponse({
                    'success': False,
                    'error': 'suggestion_id is required'
                }, status=400)
            
            details = self.suggestion_service.get_suggestion_details(suggestion_id)
            
            if not details:
                return JsonResponse({
                    'success': False,
                    'error': 'Suggestion not found'
                }, status=404)
            
            return JsonResponse({
                'success': True,
                'details': details
            })
            
        except Exception as e:
            logger.error(f"Suggestion details error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    def provide_feedback(self, request):
        """Provide feedback on suggestion accuracy"""
        try:
            if request.method != 'POST':
                return JsonResponse({
                    'success': False,
                    'error': 'POST method required'
                }, status=405)
            
            data = json.loads(request.body)
            suggestion_id = data.get('suggestion_id')
            was_correct = data.get('was_correct')
            actual_loan_id = data.get('actual_loan_id')
            
            if suggestion_id is None or was_correct is None:
                return JsonResponse({
                    'success': False,
                    'error': 'suggestion_id and was_correct are required'
                }, status=400)
            
            # Provide feedback to the service
            feedback_result = self.suggestion_service.provide_feedback(
                suggestion_id, was_correct, actual_loan_id
            )
            
            # Log feedback for analytics
            logger.info(f"Feedback received: {suggestion_id} -> {was_correct}")
            
            return JsonResponse(feedback_result)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Feedback error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    def get_service_stats(self, request):
        """Get service statistics and performance metrics"""
        try:
            stats = self.suggestion_service.get_service_statistics()
            
            # Add additional system information
            stats.update({
                'api_version': '1.0.0',
                'cache_info': self._get_cache_info(),
                'system_status': 'healthy'
            })
            
            return JsonResponse(stats)
            
        except Exception as e:
            logger.error(f"Service stats error: {e}")
            return JsonResponse({
                'error': 'Failed to get service statistics'
            }, status=500)
    
    def clear_cache(self, request):
        """Clear suggestion cache (admin only)"""
        try:
            if not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Admin access required'
                }, status=403)
            
            result = self.suggestion_service.clear_cache()
            cache.clear()  # Also clear Django cache
            
            logger.info(f"Cache cleared by user: {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Cache cleared successfully',
                'cleared_at': result['timestamp']
            })
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to clear cache'
            }, status=500)
    
    def _get_cache_info(self):
        """Get cache information"""
        try:
            # Basic cache info - could be expanded with Redis stats
            return {
                'django_cache_available': bool(cache),
                'suggestion_service_cache_size': len(self.suggestion_service.suggestion_cache)
            }
        except Exception:
            return {'cache_info_error': True}


# Initialize API handler
suggestion_api = SmartSuggestionAPI()


# Django view functions that use the API handler
@require_http_methods(["GET"])
def suggestions_view(request):
    """Main suggestions endpoint"""
    return suggestion_api.get_suggestions(request)


@require_http_methods(["GET"])
def quick_suggestions_view(request):
    """Quick suggestions for autocomplete"""
    return suggestion_api.get_quick_suggestions(request)


@require_http_methods(["GET"])
def suggestion_details_view(request):
    """Detailed suggestion information"""
    return suggestion_api.get_suggestion_details(request)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def suggestion_feedback_view(request):
    """Suggestion feedback endpoint"""
    return suggestion_api.provide_feedback(request)


@require_http_methods(["GET"])
@login_required
def service_stats_view(request):
    """Service statistics endpoint"""
    return suggestion_api.get_service_stats(request)


@require_http_methods(["POST"])
@login_required
def clear_cache_view(request):
    """Clear cache endpoint (admin only)"""
    return suggestion_api.clear_cache(request)


# Class-based view for more complex operations
@method_decorator(login_required, name='dispatch')
class SuggestionManagementView(View):
    """Advanced suggestion management view"""
    
    def __init__(self):
        super().__init__()
        self.suggestion_service = SmartSuggestionService()
    
    def get(self, request):
        """Get suggestion management dashboard data"""
        try:
            # Get comprehensive statistics
            stats = self.suggestion_service.get_service_statistics()
            
            # Get confidence calculator stats
            confidence_stats = self.suggestion_service.confidence_calculator.get_engine_performance_stats()
            
            # Get weight adjustment suggestions
            weight_suggestions = self.suggestion_service.confidence_calculator.suggest_weight_adjustments()
            
            # Get confidence trends
            trends = self.suggestion_service.confidence_calculator.get_confidence_trends()
            
            dashboard_data = {
                'service_stats': stats,
                'engine_performance': confidence_stats,
                'weight_suggestions': weight_suggestions,
                'confidence_trends': trends,
                'total_engines': len(self.suggestion_service.engines),
                'system_health': self._assess_system_health(stats, confidence_stats)
            }
            
            return JsonResponse(dashboard_data)
            
        except Exception as e:
            logger.error(f"Management dashboard error: {e}")
            return JsonResponse({
                'error': 'Failed to load dashboard data'
            }, status=500)
    
    def post(self, request):
        """Apply configuration changes"""
        try:
            if not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Admin access required'
                }, status=403)
            
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'apply_weight_adjustments':
                adjustments = data.get('adjustments', {})
                self.suggestion_service.confidence_calculator.apply_weight_adjustments(adjustments)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Applied {len(adjustments)} weight adjustments'
                })
            
            elif action == 'enable_debug_mode':
                self.suggestion_service.enable_debug_mode()
                return JsonResponse({
                    'success': True,
                    'message': 'Debug mode enabled'
                })
            
            elif action == 'disable_debug_mode':
                self.suggestion_service.disable_debug_mode()
                return JsonResponse({
                    'success': True,
                    'message': 'Debug mode disabled'
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown action: {action}'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Management action error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to apply changes'
            }, status=500)
    
    def _assess_system_health(self, stats, confidence_stats):
        """Assess overall system health"""
        health_score = 100
        issues = []
        
        # Check if all engines are active
        if stats['active_engines'] < 3:
            health_score -= 20
            issues.append('Some engines are inactive')
        
        # Check engine performance
        for engine, perf in confidence_stats.items():
            if perf.get('accuracy', 100) < 70:
                health_score -= 10
                issues.append(f'{engine} has low accuracy')
        
        # Check cache size (if too large, might indicate memory issues)
        if stats['cache_size'] > 5000:
            health_score -= 5
            issues.append('Large cache size detected')
        
        # Determine health status
        if health_score >= 90:
            status = 'excellent'
        elif health_score >= 75:
            status = 'good'
        elif health_score >= 60:
            status = 'fair'
        else:
            status = 'poor'
        
        return {
            'score': health_score,
            'status': status,
            'issues': issues
        }


# Utility function for error handling
def handle_api_error(func):
    """Decorator for consistent API error handling"""
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error',
                'timestamp': datetime.now().isoformat()
            }, status=500)
    return wrapper


# Test endpoint for development
@require_http_methods(["GET"])
def test_suggestions_view(request):
    """Test endpoint with sample data"""
    try:
        sample_descriptions = [
            "EB-зээл олгов Б.Очмаа",
            "6045УАМ 88980800",
            "EB-200000000371 төлбөр",
            "зээлийн эргэн төлөлт"
        ]
        
        results = {}
        
        for desc in sample_descriptions:
            suggestions = suggestion_api.suggestion_service.get_suggestions(desc, 1000000)
            results[desc] = {
                'suggestion_count': len(suggestions),
                'top_match': suggestions[0] if suggestions else None
            }
        
        return JsonResponse({
            'test_results': results,
            'service_stats': suggestion_api.suggestion_service.get_service_statistics(),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)
