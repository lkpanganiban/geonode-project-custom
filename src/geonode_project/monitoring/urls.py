from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Main dashboard
    path('', views.monitoring_dashboard, name='dashboard'),
    
    # API endpoints
    path('api/workers/', views.api_worker_stats, name='api_workers'),
    path('api/task/<str:task_id>/', views.api_task_info, name='api_task_info'),
    path('api/retry/', views.api_retry_task, name='api_retry'),
    path('api/purge/', views.api_purge_queue, name='api_purge'),
    path('api/rate-limit/', views.api_set_rate_limit, name='api_rate_limit'),
    path('api/revoke/', views.api_revoke_task, name='api_revoke'),
    path('api/trigger/', views.api_trigger_task, name='api_trigger'),
    path('api/history/', views.api_task_history, name='api_history'),
    path('api/history/clear/', views.api_clear_history, name='api_clear_history'),
    path('api/history/cleanup/', views.api_cleanup_completed, name='api_cleanup_completed'),
    path('api/history/delete/<str:task_id>/', views.api_delete_task, name='api_delete_task'),
]
