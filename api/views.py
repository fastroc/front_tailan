from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import json
from users.models import UserProfile


@csrf_exempt
@require_http_methods(["GET"])
def api_status(request):
    """API status endpoint."""
    return JsonResponse({
        'status': 'active',
        'message': 'API is running successfully',
        'version': '1.0.0'
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """API login endpoint."""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({
                'error': 'Email and password required'
            }, status=400)
        
        user = authenticate(username=email, password=password)
        
        if user is not None:
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'is_verified': user.is_verified
                }
            })
        else:
            return JsonResponse({
                'error': 'Invalid credentials'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    """API registration endpoint."""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        if not email or not password:
            return JsonResponse({
                'error': 'Email and password required'
            }, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'error': 'Email already exists'
            }, status=400)
        
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return JsonResponse({
            'success': True,
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)


@login_required
@require_http_methods(["GET"])
def api_user_profile(request):
    """API user profile endpoint."""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    return JsonResponse({
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'phone': user.phone,
            'bio': user.bio,
            'is_verified': user.is_verified,
            'date_joined': user.date_joined.isoformat(),
        },
        'profile': {
            'address': profile.address,
            'city': profile.city,
            'country': profile.country,
            'postal_code': profile.postal_code,
            'website': profile.website,
            'company': profile.company,
            'job_title': profile.job_title,
        }
    })


@require_http_methods(["GET"])
def api_users_list(request):
    """API endpoint to list all users (public info only)."""
    users = User.objects.filter(is_active=True)[:20]  # Limit to 20 users
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'full_name': user.full_name,
            'bio': user.bio[:100] if user.bio else '',  # Truncate bio
            'is_verified': user.is_verified,
            'date_joined': user.date_joined.isoformat(),
        })
    
    return JsonResponse({
        'users': users_data,
        'count': len(users_data)
    })
