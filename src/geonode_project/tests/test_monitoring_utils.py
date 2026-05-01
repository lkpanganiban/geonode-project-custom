"""
Unit tests for geonode_project.monitoring.utils module.
"""
import os
import django
from unittest.mock import Mock, patch, MagicMock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode_project.test_settings')
django.setup()

from django.test import TestCase
from geonode_project.monitoring.utils import (
    get_celery_app,
    celery_inspect,
    get_worker_stats,
    get_queue_stats,
    get_task_info,
    retry_task,
    purge_queue,
    set_task_rate_limit,
    revoke_task,
    trigger_task,
)


class GetCeleryAppTests(TestCase):
    """Tests for get_celery_app function."""

    def test_get_celery_app_returns_app(self):
        """Test that get_celery_app returns a Celery app instance."""
        app = get_celery_app()
        self.assertIsNotNone(app)
        self.assertTrue(hasattr(app, 'control'))

    def test_get_celery_app_is_consistent(self):
        """Test that get_celery_app returns the same app instance."""
        app1 = get_celery_app()
        app2 = get_celery_app()
        self.assertEqual(app1, app2)


class CeleryInspectTests(TestCase):
    """Tests for celery_inspect function."""

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_celery_inspect_returns_inspector(self, mock_get_app):
        """Test that celery_inspect returns an inspector."""
        mock_app = Mock()
        mock_inspector = Mock()
        mock_app.control.inspect.return_value = mock_inspector
        mock_get_app.return_value = mock_app

        result = celery_inspect()
        self.assertEqual(result, mock_inspector)


class GetWorkerStatsTests(TestCase):
    """Tests for get_worker_stats function."""

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_worker_stats_no_workers(self, mock_inspect):
        """Test get_worker_stats when no inspector is available."""
        mock_inspect.return_value = None
        result = get_worker_stats()
        self.assertEqual(result['worker_count'], 0)
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'No Celery workers running')

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_worker_stats_with_workers(self, mock_inspect):
        """Test get_worker_stats with active workers."""
        mock_inspector = Mock()
        mock_inspector.stats.return_value = {
            'worker1@host': {'pool': {'max-concurrency': 4}}
        }
        mock_inspector.active.return_value = {'worker1@host': []}
        mock_inspector.registered.return_value = {'worker1@host': ['task1']}
        mock_inspector.scheduled.return_value = {'worker1@host': []}
        mock_inspector.reserved.return_value = {'worker1@host': []}
        mock_inspector.revoked.return_value = {'worker1@host': []}
        mock_inspect.return_value = mock_inspector

        result = get_worker_stats()
        self.assertEqual(result['worker_count'], 1)
        self.assertEqual(len(result['workers']), 1)
        self.assertEqual(result['active_count'], 0)
        self.assertNotIn('error', result)

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_worker_stats_with_active_tasks(self, mock_inspect):
        """Test get_worker_stats with active tasks."""
        mock_inspector = Mock()
        mock_inspector.stats.return_value = {
            'worker1@host': {'pool': {'max-concurrency': 4}}
        }
        mock_inspector.active.return_value = {
            'worker1@host': [{'id': 'task-1', 'name': 'test.task'}]
        }
        mock_inspector.registered.return_value = {'worker1@host': ['task1']}
        mock_inspector.scheduled.return_value = {'worker1@host': []}
        mock_inspector.reserved.return_value = {'worker1@host': []}
        mock_inspector.revoked.return_value = {'worker1@host': []}
        mock_inspect.return_value = mock_inspector

        result = get_worker_stats()
        self.assertEqual(result['active_count'], 1)

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_worker_stats_exception(self, mock_inspect):
        """Test get_worker_stats when inspector raises an exception."""
        mock_inspector = Mock()
        mock_inspector.stats.side_effect = Exception('Connection refused')
        mock_inspect.return_value = mock_inspector

        result = get_worker_stats()
        self.assertIn('error', result)
        self.assertEqual(result['worker_count'], 0)


class GetQueueStatsTests(TestCase):
    """Tests for get_queue_stats function."""

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_queue_stats_no_inspector(self, mock_inspect):
        """Test get_queue_stats when no inspector is available."""
        mock_inspect.return_value = None
        result = get_queue_stats()
        self.assertEqual(result['scheduled'], 0)
        self.assertEqual(result['reserved'], 0)
        self.assertEqual(result['queues'], ['celery', 'default'])

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_queue_stats_with_scheduled(self, mock_inspect):
        """Test get_queue_stats with scheduled tasks."""
        mock_inspector = Mock()
        mock_inspector.scheduled.return_value = {
            'worker1@host': [{'task': 'task1'}, {'task': 'task2'}]
        }
        mock_inspector.reserved.return_value = {'worker1@host': []}
        mock_inspect.return_value = mock_inspector

        result = get_queue_stats()
        self.assertEqual(result['scheduled'], 2)
        self.assertEqual(result['reserved'], 0)

    @patch('geonode_project.monitoring.utils.celery_inspect')
    def test_get_queue_stats_with_reserved(self, mock_inspect):
        """Test get_queue_stats with reserved tasks."""
        mock_inspector = Mock()
        mock_inspector.scheduled.return_value = {'worker1@host': []}
        mock_inspector.reserved.return_value = {
            'worker1@host': [{'task': 'task1'}]
        }
        mock_inspect.return_value = mock_inspector

        result = get_queue_stats()
        self.assertEqual(result['scheduled'], 0)
        self.assertEqual(result['reserved'], 1)


class GetTaskInfoTests(TestCase):
    """Tests for get_task_info function."""

    @patch('geonode_project.monitoring.utils.AsyncResult')
    def test_get_task_info_pending(self, mock_async_result):
        """Test get_task_info for a pending task."""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_result.ready.return_value = False
        mock_result.result = None
        mock_result.traceback = None
        mock_result.date_done = None
        mock_async_result.return_value = mock_result

        result = get_task_info('task-id-123')
        self.assertEqual(result['id'], 'task-id-123')
        self.assertEqual(result['state'], 'PENDING')
        self.assertIsNone(result['result'])

    @patch('geonode_project.monitoring.utils.AsyncResult')
    def test_get_task_info_success(self, mock_async_result):
        """Test get_task_info for a successful task."""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.ready.return_value = True
        mock_result.result = {'key': 'value'}
        mock_result.failed.return_value = False
        mock_result.traceback = None
        mock_result.date_done = '2024-01-01 00:00:00'
        mock_async_result.return_value = mock_result

        result = get_task_info('task-id-123')
        self.assertEqual(result['state'], 'SUCCESS')
        self.assertEqual(result['result'], {'key': 'value'})

    @patch('geonode_project.monitoring.utils.AsyncResult')
    def test_get_task_info_failure(self, mock_async_result):
        """Test get_task_info for a failed task."""
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.ready.return_value = True
        mock_result.result = None
        mock_result.failed.return_value = True
        mock_result.traceback = 'Traceback error'
        mock_result.date_done = '2024-01-01 00:00:00'
        mock_async_result.return_value = mock_result

        result = get_task_info('task-id-123')
        self.assertEqual(result['state'], 'FAILURE')
        self.assertEqual(result['traceback'], 'Traceback error')


class RetryTaskTests(TestCase):
    """Tests for retry_task function."""

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_retry_task(self, mock_get_app):
        """Test retry_task sends a task."""
        mock_app = Mock()
        mock_task = Mock()
        mock_task.id = 'new-task-id-123'
        mock_app.send_task.return_value = mock_task
        mock_get_app.return_value = mock_app

        result = retry_task('test.task', args=[1, 2], kwargs={'key': 'value'})
        self.assertEqual(result, 'new-task-id-123')
        mock_app.send_task.assert_called_once_with(
            'test.task', args=[1, 2], kwargs={'key': 'value'}
        )

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_retry_task_with_defaults(self, mock_get_app):
        """Test retry_task with default args and kwargs."""
        mock_app = Mock()
        mock_task = Mock()
        mock_task.id = 'new-task-id'
        mock_app.send_task.return_value = mock_task
        mock_get_app.return_value = mock_app

        result = retry_task('test.task')
        mock_app.send_task.assert_called_once_with(
            'test.task', args=[], kwargs={}
        )


class PurgeQueueTests(TestCase):
    """Tests for purge_queue function."""

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_purge_queue_success(self, mock_get_app):
        """Test purge_queue success."""
        mock_app = Mock()
        mock_app.control.purge.return_value = 5
        mock_get_app.return_value = mock_app

        result = purge_queue('celery')
        self.assertTrue(result['success'])
        self.assertIn('message', result)

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_purge_queue_failure(self, mock_get_app):
        """Test purge_queue failure."""
        mock_app = Mock()
        mock_app.control.purge.side_effect = Exception('Purge failed')
        mock_get_app.return_value = mock_app

        result = purge_queue('celery')
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class SetTaskRateLimitTests(TestCase):
    """Tests for set_task_rate_limit function."""

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_set_task_rate_limit_success(self, mock_get_app):
        """Test set_task_rate_limit success."""
        mock_app = Mock()
        mock_get_app.return_value = mock_app

        result = set_task_rate_limit('test.task', '10/m')
        self.assertTrue(result['success'])
        self.assertIn('10/m', result['message'])
        mock_app.control.rate_limit.assert_called_once_with('test.task', '10/m')

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_set_task_rate_limit_failure(self, mock_get_app):
        """Test set_task_rate_limit failure."""
        mock_app = Mock()
        mock_app.control.rate_limit.side_effect = Exception('Rate limit failed')
        mock_get_app.return_value = mock_app

        result = set_task_rate_limit('test.task', '10/m')
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class RevokeTaskTests(TestCase):
    """Tests for revoke_task function."""

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_revoke_task_success(self, mock_get_app):
        """Test revoke_task success."""
        mock_app = Mock()
        mock_get_app.return_value = mock_app

        result = revoke_task('task-id-123')
        self.assertTrue(result['success'])
        mock_app.control.revoke.assert_called_once_with('task-id-123')

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_revoke_task_with_terminate(self, mock_get_app):
        """Test revoke_task with terminate=True."""
        mock_app = Mock()
        mock_get_app.return_value = mock_app

        result = revoke_task('task-id-123', terminate=True)
        self.assertTrue(result['success'])
        mock_app.control.revoke.assert_called_once_with(
            'task-id-123', terminate=True
        )

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_revoke_task_with_signal(self, mock_get_app):
        """Test revoke_task with custom signal."""
        mock_app = Mock()
        mock_get_app.return_value = mock_app

        result = revoke_task('task-id-123', terminate=True, signal='SIGKILL')
        self.assertTrue(result['success'])
        mock_app.control.revoke.assert_called_once_with(
            'task-id-123', terminate=True, signal='SIGKILL'
        )

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_revoke_task_failure(self, mock_get_app):
        """Test revoke_task failure."""
        mock_app = Mock()
        mock_app.control.revoke.side_effect = Exception('Revoke failed')
        mock_get_app.return_value = mock_app

        result = revoke_task('task-id-123')
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class TriggerTaskTests(TestCase):
    """Tests for trigger_task function."""

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_trigger_task_success(self, mock_get_app):
        """Test trigger_task success."""
        mock_app = Mock()
        mock_result = Mock()
        mock_result.id = 'new-task-id-456'
        mock_app.send_task.return_value = mock_result
        mock_get_app.return_value = mock_app

        result = trigger_task('test.task', args=[1, 2], kwargs={'key': 'value'})
        self.assertEqual(result, 'new-task-id-456')
        mock_app.send_task.assert_called_once_with(
            'test.task', args=[1, 2], kwargs={'key': 'value'}, queue='default'
        )

    @patch('geonode_project.monitoring.utils.get_celery_app')
    def test_trigger_task_with_defaults(self, mock_get_app):
        """Test trigger_task with default args and kwargs."""
        mock_app = Mock()
        mock_result = Mock()
        mock_result.id = 'new-task-id'
        mock_app.send_task.return_value = mock_result
        mock_get_app.return_value = mock_app

        result = trigger_task('test.task')
        mock_app.send_task.assert_called_once_with(
            'test.task', args=[], kwargs={}, queue='default'
        )
