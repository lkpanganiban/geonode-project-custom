from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from celery.result import AsyncResult
import json

from .utils import (
    get_worker_stats,
    get_queue_stats,
    get_task_info,
    retry_task,
    purge_queue,
    set_task_rate_limit,
    revoke_task,
    trigger_task
)
from .decorators import staff_required
from .models import TaskTriggerHistory


class MonitoringDashboardView(TemplateView):
    """
    Main Celery monitoring dashboard
    Visible only to staff users
    """
    template_name = 'monitoring/dashboard.html'
    
    @method_decorator(login_required)
    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get worker statistics
        worker_data = get_worker_stats()
        queue_data = get_queue_stats()
        
        # Update task statuses in history
        self._update_task_statuses()
        
        # Get recent task trigger history (last 50)
        task_history = TaskTriggerHistory.objects.all()[:50]
        
        context.update({
            'workers': worker_data.get('workers', []),
            'worker_count': worker_data.get('worker_count', 0),
            'active_tasks': worker_data.get('active_count', 0),
            'scheduled_tasks': queue_data.get('scheduled', 0),
            'reserved_tasks': queue_data.get('reserved', 0),
            'queues': queue_data.get('queues', ['celery', 'default']),
            'error': worker_data.get('error'),
            'page_title': 'Celery Monitoring Dashboard',
            'task_history': task_history,
        })
        
        return context
    
    def _update_task_statuses(self):
        """Update status of pending tasks in history"""
        pending_tasks = TaskTriggerHistory.objects.filter(status='PENDING')
        for task in pending_tasks:
            result = AsyncResult(task.task_id)
            if result.ready():
                if result.successful():
                    task.status = 'SUCCESS'
                    task.result = str(result.result)
                elif result.failed():
                    task.status = 'FAILURE'
                    task.result = str(result.result) if result.result else 'Task failed'
                task.completed_at = timezone.now()
                task.save()


monitoring_dashboard = MonitoringDashboardView.as_view()


# API Views for AJAX calls

@login_required
@staff_required
@require_http_methods(['GET'])
def api_worker_stats(request):
    """API endpoint to get fresh worker stats (for auto-refresh)"""
    return JsonResponse(get_worker_stats())


@login_required
@staff_required
@require_http_methods(['GET'])
def api_task_info(request, task_id):
    """Get detailed task information"""
    return JsonResponse(get_task_info(task_id))


@login_required
@staff_required
@require_http_methods(['POST'])
def api_retry_task(request):
    """Retry a failed task"""
    try:
        data = json.loads(request.body)
        task_name = data.get('task_name')
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        
        if not task_name:
            return JsonResponse({'success': False, 'error': 'Task name required'})
        
        new_task_id = retry_task(task_name, args, kwargs)
        return JsonResponse({
            'success': True,
            'task_id': new_task_id,
            'message': 'Task queued for retry'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_purge_queue(request):
    """Purge all messages from a queue"""
    try:
        data = json.loads(request.body)
        queue_name = data.get('queue_name', 'celery')
        
        result = purge_queue(queue_name)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_set_rate_limit(request):
    """Set rate limit for a task"""
    try:
        data = json.loads(request.body)
        task_name = data.get('task_name')
        rate = data.get('rate')
        
        if not task_name or not rate:
            return JsonResponse({
                'success': False,
                'error': 'Task name and rate required'
            })
        
        result = set_task_rate_limit(task_name, rate)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_revoke_task(request):
    """Revoke a running task"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        terminate = data.get('terminate', False)
        
        if not task_id:
            return JsonResponse({'success': False, 'error': 'Task ID required'})
        
        result = revoke_task(task_id, terminate=terminate)
        
        # Update history if task is tracked
        try:
            history = TaskTriggerHistory.objects.get(task_id=task_id)
            history.status = 'REVOKED'
            history.completed_at = timezone.now()
            history.save()
        except TaskTriggerHistory.DoesNotExist:
            pass
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_trigger_task(request):
    """Manually trigger a Celery task"""
    try:
        data = json.loads(request.body)
        task_name = data.get('task_name')
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        
        if not task_name:
            return JsonResponse({
                'success': False,
                'error': 'Task name is required'
            })
        
        # Validate args is a list
        if not isinstance(args, list):
            return JsonResponse({
                'success': False,
                'error': 'Arguments must be a JSON array'
            })
        
        # Trigger the task
        task_id = trigger_task(task_name, args, kwargs)
        
        # Save to history
        TaskTriggerHistory.objects.create(
            task_id=task_id,
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            triggered_by=request.user,
            status='PENDING'
        )
        
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'task_name': task_name,
            'message': f'Task "{task_name}" triggered successfully'
        })
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid JSON: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['GET'])
def api_task_history(request):
    """Get task trigger history with updated statuses"""
    try:
        # Update pending task statuses
        pending_tasks = TaskTriggerHistory.objects.filter(status='PENDING')
        for task in pending_tasks:
            result = AsyncResult(task.task_id)
            if result.ready():
                if result.successful():
                    task.status = 'SUCCESS'
                    task.result = str(result.result)[:500] if result.result else 'Success'
                elif result.failed():
                    task.status = 'FAILURE'
                    task.result = str(result.result)[:500] if result.result else 'Task failed'
                task.completed_at = timezone.now()
                task.save()
        
        # Get recent history
        history = TaskTriggerHistory.objects.all()[:50]
        
        data = []
        for item in history:
            data.append({
                'task_id': item.task_id,
                'task_name': item.task_name,
                'args': item.args,
                'kwargs': item.kwargs,
                'triggered_by': item.triggered_by.username if item.triggered_by else 'Unknown',
                'triggered_at': item.triggered_at.isoformat(),
                'status': item.status,
                'result': item.result,
                'completed_at': item.completed_at.isoformat() if item.completed_at else None,
            })
        
        return JsonResponse({'success': True, 'history': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_delete_task(request, task_id):
    """Delete a specific task from history"""
    try:
        task = TaskTriggerHistory.objects.get(task_id=task_id)
        task.delete()
        return JsonResponse({
            'success': True,
            'message': f'Task {task_id[:8]} deleted successfully'
        })
    except TaskTriggerHistory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Task not found'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_clear_history(request):
    """Clear all task history"""
    try:
        count = TaskTriggerHistory.objects.count()
        TaskTriggerHistory.objects.all().delete()
        return JsonResponse({
            'success': True,
            'message': f'All {count} task(s) cleared from history'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_required
@require_http_methods(['POST'])
def api_cleanup_completed(request):
    """Delete completed (SUCCESS, FAILURE, REVOKED) tasks from history"""
    try:
        completed_tasks = TaskTriggerHistory.objects.filter(
            status__in=['SUCCESS', 'FAILURE', 'REVOKED']
        )
        count = completed_tasks.count()
        completed_tasks.delete()
        return JsonResponse({
            'success': True,
            'message': f'{count} completed task(s) cleared from history'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
