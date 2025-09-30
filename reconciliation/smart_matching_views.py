"""
Smart Matching AJAX Views

AJAX endpoints for testing and using the smart matching system.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


@require_http_methods(["POST"])
@csrf_exempt  # For testing - remove in production
def smart_match_test(request):
    """Test endpoint for smart matching system"""
    try:
        data = json.loads(request.body)
        bank_description = data.get('description', '')
        amount = float(data.get('amount', 0))
        
        print(f"🧠 Smart matching test - Description: '{bank_description}', Amount: {amount}")
        
        from .smart_matching.registry import get_registry
        
        # Get registry and run all engines
        registry = get_registry()
        
        # Get best suggestions
        suggestions = registry.get_best_suggestions(bank_description, amount)
        
        # Get performance metrics
        performance = registry.get_performance_report()
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions,
            'performance': performance,
            'count': len(suggestions)
        })
        
    except Exception as e:
        print(f"❌ Smart matching error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'suggestions': []
        })


@require_http_methods(["GET"])
def smart_match_status(request):
    """Get status of smart matching engines"""
    try:
        from .smart_matching.registry import get_registry
        
        registry = get_registry()
        performance = registry.get_performance_report()
        
        return JsonResponse({
            'success': True,
            'performance': performance
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
