from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Main journal pages
    path('', views.manual_journal_list, name='manual_journal'),
    path('new/', views.new_journal, name='new_journal'),
    path('<int:journal_id>/', views.journal_detail, name='journal_detail'),
    path('<int:journal_id>/edit/', views.edit_journal, name='edit_journal'),
    path('<int:journal_id>/duplicate/', views.duplicate_journal, name='duplicate_journal'),
    
    # API endpoints
    path('api/<int:journal_id>/post/', views.post_journal_api, name='post_journal_api'),
    path('api/<int:journal_id>/reverse/', views.reverse_journal_api, name='reverse_journal_api'),
    path('api/<int:journal_id>/delete/', views.delete_journal_api, name='delete_journal_api'),
    path('api/<int:journal_id>/force-delete/', views.force_delete_journal_api, name='force_delete_journal_api'),
]
