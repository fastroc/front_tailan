"""
Celery configuration for loan management system
Provides background task processing for performance optimization
"""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Set default Django settings module for celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Create celery instance
app = Celery('myproject')

# Configure celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all apps
app.autodiscover_tasks()

# Task routes for different priorities
app.conf.task_routes = {
    'loans_core.tasks.update_approval_progress': {'queue': 'high_priority'},
    'loans_core.tasks.bulk_cache_warm': {'queue': 'low_priority'},
    'loans_core.tasks.cleanup_expired_cache': {'queue': 'low_priority'},
    'loans_core.tasks.generate_progress_report': {'queue': 'medium_priority'},
}

# Task configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_hijack_root_logger=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Redis broker configuration
if hasattr(settings, 'CELERY_BROKER_URL'):
    app.conf.broker_url = settings.CELERY_BROKER_URL
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND
else:
    # Fallback to Django database
    app.conf.broker_url = 'django://'
    app.conf.result_backend = 'django-db'

# Queue configuration
app.conf.task_default_queue = 'default'
app.conf.task_queues = {
    'high_priority': {
        'routing_key': 'high_priority',
    },
    'medium_priority': {
        'routing_key': 'medium_priority',
    },
    'low_priority': {
        'routing_key': 'low_priority',
    },
}

# Periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-cache': {
        'task': 'loans_core.tasks.cleanup_expired_cache',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'low_priority'}
    },
    'warm-application-cache': {
        'task': 'loans_core.tasks.bulk_cache_warm',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'low_priority'}
    },
    'generate-daily-progress-report': {
        'task': 'loans_core.tasks.generate_progress_report',
        'schedule': 86400.0,  # Daily at midnight
        'options': {'queue': 'medium_priority'}
    },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task to test celery configuration"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'
