from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('status/', views.api_status, name='status'),
    path('auth/login/', views.api_login, name='login'),
    path('auth/register/', views.api_register, name='register'),
    path('user/profile/', views.api_user_profile, name='user_profile'),
    path('users/', views.api_users_list, name='users_list'),
]
