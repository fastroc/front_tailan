from django.urls import path
from . import views

app_name = 'setup'

urlpatterns = [
    path('', views.setup_dashboard, name='dashboard'),
    path('step/<str:step_name>/', views.setup_step, name='step'),
    path('skip/<str:step_name>/', views.skip_step, name='skip_step'),
    path('complete/', views.complete_setup, name='complete'),
    path('debug/', views.debug_setup_status, name='debug'),  # Debug view
]
