"""
Celery monitoring utilities using celery.control.inspect
"""
from celery.result import AsyncResult
from django.conf import settings
import json


def get_celery_app():
    """Get the Celery app instance"""
    from geonode_project.celeryapp import app
    return app


def celery_inspect():
    """Get Celery inspector instance"""
    app = get_celery_app()
    return app.control.inspect()


def get_celery_app():
    """Get the Celery app instance"""
    from geonode_project.celeryapp import app
    return app


def get_worker_stats():
    """Get comprehensive worker statistics"""
    app = get_celery_app()
    inspector = celery_inspect()
    
    if not inspector:
        return {
            'workers': [],
            'error': 'No Celery workers running',
            'worker_count': 0,
            'active_count': 0
        }
    
    try:
        stats = inspector.stats() or {}
        active = inspector.active() or {}
        registered = inspector.registered() or {}
        scheduled = inspector.scheduled() or {}
        reserved = inspector.reserved() or {}
        revoked = inspector.revoked() or {}
    except Exception as e:
        return {
            'workers': [],
            'error': str(e),
            'worker_count': 0,
            'active_count': 0
        }
    
    workers = []
    total_active = 0
    
    for worker_name in stats:
        worker_stats = stats.get(worker_name, {})
        active_tasks = active.get(worker_name, [])
        total_active += len(active_tasks)
        
        worker_info = {
            'name': worker_name,
            'status': 'online',
            'stats': worker_stats,
            'active_tasks': active_tasks,
            'registered_tasks': registered.get(worker_name, []),
            'scheduled_tasks': scheduled.get(worker_name, []),
            'reserved_tasks': reserved.get(worker_name, []),
            'revoked_tasks': revoked.get(worker_name, []),
        }
        workers.append(worker_info)
    
    return {
        'workers': workers,
        'worker_count': len(workers),
        'active_count': total_active,
    }


def get_queue_stats():
    """Get queue statistics"""
    app = get_celery_app()
    inspector = celery_inspect()
    
    scheduled = 0
    reserved = 0
    
    if inspector:
        try:
            scheduled_data = inspector.scheduled() or {}
            reserved_data = inspector.reserved() or {}
            scheduled = sum(len(tasks) for tasks in scheduled_data.values())
            reserved = sum(len(tasks) for tasks in reserved_data.values())
        except:
            pass
    
    # Get queues from settings or use defaults
    queues = getattr(settings, 'CELERY_MONITORING_QUEUES', ['celery', 'default'])
    
    return {
        'scheduled': scheduled,
        'reserved': reserved,
        'queues': queues
    }


def get_task_info(task_id):
    """Get detailed task information"""
    result = AsyncResult(task_id)
    
    return {
        'id': task_id,
        'state': result.state,
        'result': result.result if result.ready() else None,
        'traceback': result.traceback if result.failed() else None,
        'date_done': str(result.date_done) if result.date_done else None,
    }


def retry_task(task_name, args=None, kwargs=None):
    """Retry a task by sending it again"""
    app = get_celery_app()
    task = app.send_task(task_name, args=args or [], kwargs=kwargs or {})
    return task.id


def purge_queue(queue_name='celery'):
    """Purge all messages from queues"""
    app = get_celery_app()
    
    try:
        # Use Celery's control.purge to clear all task queues
        app.control.purge()
        return {'success': True, 'message': 'All queues purged successfully'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def set_task_rate_limit(task_name, rate):
    """Set rate limit for a task (e.g., '10/m', '100/h')"""
    try:
        app = get_celery_app()
        app.control.rate_limit(task_name, rate)
        return {'success': True, 'message': f'Rate limit set to {rate}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def revoke_task(task_id, terminate=False, signal=None):
    """Revoke a running task"""
    try:
        app = get_celery_app()
        kwargs = {}
        if terminate:
            kwargs['terminate'] = True
        if signal:
            kwargs['signal'] = signal
        
        app.control.revoke(task_id, **kwargs)
        return {'success': True, 'message': 'Task revoked successfully'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def trigger_task(task_name, args=None, kwargs=None):
    """Manually trigger a Celery task
    
    Args:
        task_name: Full path to the task (e.g., 'myapp.tasks.send_email')
        args: List of positional arguments
        kwargs: Dictionary of keyword arguments
    
    Returns:
        task_id: The ID of the triggered task
    """
    app = get_celery_app()
    
    # Send the task to the 'default' queue (matching GeoNode worker config)
    result = app.send_task(
        task_name,
        args=args or [],
        kwargs=kwargs or {},
        queue='default'
    )
    
    return result.id
