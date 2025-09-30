"""
Smart Matching API Views

API endpoints for testing and using the smart matching system.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .registry import get_registry


@require_http_methods(["POST"])
@csrf_exempt
def test_smart_matching(request):
    """Test endpoint for smart matching system"""
    try:
        data = json.loads(request.body)
        bank_description = data.get('description', '')
        amount = float(data.get('amount', 0))
        company_id = int(data.get('company_id', 1))
        
        if not bank_description:
            return JsonResponse({'error': 'Bank description is required'}, status=400)
        
        if amount <= 0:
            return JsonResponse({'error': 'Valid amount is required'}, status=400)
        
        # Get smart matching registry
        registry = get_registry()
        
        # Run all engines
        engine_results = registry.run_all_engines(bank_description, amount)
        
        # Get best suggestions
        best_suggestions = registry.get_best_suggestions(bank_description, amount)
        
        # Get performance report
        performance = registry.get_performance_report()
        
        return JsonResponse({
            'success': True,
            'input': {
                'description': bank_description,
                'amount': amount,
                'company_id': company_id
            },
            'best_suggestions': best_suggestions,
            'engine_results': engine_results,
            'performance': performance
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid input: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Internal error: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def smart_matching_status(request):
    """Get status and performance of all smart matching engines"""
    try:
        registry = get_registry()
        performance = registry.get_performance_report()
        
        return JsonResponse({
            'success': True,
            'status': 'Smart matching system operational',
            'performance': performance
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Internal error: {str(e)}'}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def smart_matching_control(request):
    """Control endpoint to enable/disable engines"""
    try:
        data = json.loads(request.body)
        action = data.get('action', '').lower()
        engine_name = data.get('engine_name', '')
        
        if action not in ['enable', 'disable']:
            return JsonResponse({'error': 'Action must be enable or disable'}, status=400)
        
        if not engine_name:
            return JsonResponse({'error': 'Engine name is required'}, status=400)
        
        registry = get_registry()
        
        if action == 'enable':
            registry.enable_engine(engine_name)
        else:
            registry.disable_engine(engine_name)
        
        # Return updated status
        performance = registry.get_performance_report()
        
        return JsonResponse({
            'success': True,
            'message': f'Engine {engine_name} {action}d successfully',
            'performance': performance
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Internal error: {str(e)}'}, status=500)
