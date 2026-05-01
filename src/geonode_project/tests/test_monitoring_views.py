"""
Unit tests for geonode_project.monitoring.views module.
"""
import os
import django
import json
from unittest.mock import Mock, patch, MagicMock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode_project.test_settings')
django.setup()

from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from geonode_project.monitoring.models import TaskTriggerHistory
from geonode_project.monitoring.views import (
    MonitoringDashboardView,
    api_worker_stats,
    api_task_info,
    api_retry_task,
    api_purge_queue,
    api_set_rate_limit,
    api_revoke_task,
    api_trigger_task,
    api_task_history,
    api_delete_task,
    api_clear_history,
    api_cleanup_completed,
)


User = get_user_model()


class MonitoringDashboardViewTests(TestCase):
    """Tests for MonitoringDashboardView."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpass123',
            is_staff=False
        )

    @patch('geonode_project.monitoring.views.get_worker_stats')
    @patch('geonode_project.monitoring.views.get_queue_stats')
    def test_dashboard_accessible_to_staff(self, mock_queue_stats, mock_worker_stats):
        """Test that staff users can access the dashboard."""
        mock_worker_stats.return_value = {
            'workers': [], 'worker_count': 0, 'active_count': 0
        }
        mock_queue_stats.return_value = {
            'scheduled': 0, 'reserved': 0, 'queues': ['celery']
        }
        request = self.factory.get('/monitoring/')
        request.user = self.staff_user
        response = MonitoringDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_denies_non_staff(self):
        """Test that non-staff users are denied access."""
        request = self.factory.get('/monitoring/')
        request.user = self.regular_user
        with self.assertRaises(PermissionDenied):
            MonitoringDashboardView.as_view()(request)

    def test_dashboard_denies_anonymous(self):
        """Test that anonymous users are redirected to login."""
        request = self.factory.get('/monitoring/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        response = MonitoringDashboardView.as_view()(request)
        # login_required redirects anonymous users to login page
        self.assertEqual(response.status_code, 302)

    @patch('geonode_project.monitoring.views.get_worker_stats')
    @patch('geonode_project.monitoring.views.get_queue_stats')
    def test_dashboard_context_data(self, mock_queue_stats, mock_worker_stats):
        """Test that dashboard context contains expected data."""
        mock_worker_stats.return_value = {
            'workers': [{'name': 'worker1'}],
            'worker_count': 1,
            'active_count': 2
        }
        mock_queue_stats.return_value = {
            'scheduled': 3,
            'reserved': 4,
            'queues': ['celery', 'default']
        }
        request = self.factory.get('/monitoring/')
        request.user = self.staff_user
        response = MonitoringDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        # Context data is set in the template response
        self.assertIn('page_title', response.context_data)
        self.assertEqual(response.context_data['page_title'], 'Celery Monitoring Dashboard')
        self.assertEqual(response.context_data['worker_count'], 1)
        self.assertEqual(response.context_data['active_tasks'], 2)
        self.assertEqual(response.context_data['scheduled_tasks'], 3)
        self.assertEqual(response.context_data['reserved_tasks'], 4)

    @patch('geonode_project.monitoring.views.AsyncResult')
    @patch('geonode_project.monitoring.views.get_worker_stats')
    @patch('geonode_project.monitoring.views.get_queue_stats')
    def test_dashboard_updates_pending_tasks(self, mock_queue_stats, mock_worker_stats, mock_async_result):
        """Test that dashboard updates pending task statuses."""
        mock_worker_stats.return_value = {
            'workers': [], 'worker_count': 0, 'active_count': 0
        }
        mock_queue_stats.return_value = {
            'scheduled': 0, 'reserved': 0, 'queues': ['celery']
        }
        # Create a pending task
        task = TaskTriggerHistory.objects.create(
            task_id='pending-task-1',
            task_name='test.task',
            status='PENDING'
        )
        # Mock AsyncResult as ready and successful
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = 'Done'
        mock_async_result.return_value = mock_result

        request = self.factory.get('/monitoring/')
        request.user = self.staff_user
        MonitoringDashboardView.as_view()(request)

        task.refresh_from_db()
        self.assertEqual(task.status, 'SUCCESS')
        self.assertEqual(task.result, 'Done')


class APIWorkerStatsTests(TestCase):
    """Tests for api_worker_stats view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpass123',
            is_staff=False
        )

    @patch('geonode_project.monitoring.views.get_worker_stats')
    def test_api_worker_stats_get(self, mock_get_stats):
        """Test GET request to api_worker_stats."""
        mock_get_stats.return_value = {'workers': [], 'worker_count': 0}
        request = self.factory.get('/monitoring/api/workers/')
        request.user = self.staff_user
        response = api_worker_stats(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('workers', data)

    def test_api_worker_stats_denies_non_staff(self):
        """Test that non-staff users are denied."""
        request = self.factory.get('/monitoring/api/workers/')
        request.user = self.regular_user
        with self.assertRaises(PermissionDenied):
            api_worker_stats(request)

    def test_api_worker_stats_requires_get(self):
        """Test that only GET is allowed."""
        request = self.factory.post('/monitoring/api/workers/')
        request.user = self.staff_user
        response = api_worker_stats(request)
        self.assertEqual(response.status_code, 405)


class APITaskInfoTests(TestCase):
    """Tests for api_task_info view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.get_task_info')
    def test_api_task_info_get(self, mock_get_info):
        """Test GET request to api_task_info."""
        mock_get_info.return_value = {
            'id': 'task-1', 'state': 'SUCCESS', 'result': 'Done'
        }
        request = self.factory.get('/monitoring/api/task/task-1/')
        request.user = self.staff_user
        response = api_task_info(request, 'task-1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['state'], 'SUCCESS')


class APIRetryTaskTests(TestCase):
    """Tests for api_retry_task view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.retry_task')
    def test_api_retry_task_post(self, mock_retry):
        """Test POST request to retry a task."""
        mock_retry.return_value = 'new-task-id'
        request = self.factory.post(
            '/monitoring/api/retry/',
            data=json.dumps({'task_name': 'test.task'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_retry_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], 'new-task-id')

    def test_api_retry_task_missing_task_name(self):
        """Test retry without task name returns error."""
        request = self.factory.post(
            '/monitoring/api/retry/',
            data=json.dumps({}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_retry_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_api_retry_task_invalid_json(self):
        """Test retry with invalid JSON returns error."""
        request = self.factory.post(
            '/monitoring/api/retry/',
            data='not-json',
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_retry_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class APIPurgeQueueTests(TestCase):
    """Tests for api_purge_queue view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.purge_queue')
    def test_api_purge_queue_post(self, mock_purge):
        """Test POST request to purge queue."""
        mock_purge.return_value = {'success': True, 'message': 'Purged'}
        request = self.factory.post(
            '/monitoring/api/purge/',
            data=json.dumps({'queue_name': 'celery'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_purge_queue(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])


class APISetRateLimitTests(TestCase):
    """Tests for api_set_rate_limit view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.set_task_rate_limit')
    def test_api_set_rate_limit_post(self, mock_set_rate):
        """Test POST request to set rate limit."""
        mock_set_rate.return_value = {'success': True, 'message': 'Rate set'}
        request = self.factory.post(
            '/monitoring/api/rate-limit/',
            data=json.dumps({'task_name': 'test.task', 'rate': '10/m'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_set_rate_limit(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_api_set_rate_limit_missing_params(self):
        """Test set rate limit without required params."""
        request = self.factory.post(
            '/monitoring/api/rate-limit/',
            data=json.dumps({'task_name': 'test.task'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_set_rate_limit(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class APIRevokeTaskTests(TestCase):
    """Tests for api_revoke_task view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.revoke_task')
    def test_api_revoke_task_post(self, mock_revoke):
        """Test POST request to revoke task."""
        mock_revoke.return_value = {'success': True, 'message': 'Revoked'}
        request = self.factory.post(
            '/monitoring/api/revoke/',
            data=json.dumps({'task_id': 'task-1'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_revoke_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_api_revoke_task_updates_history(self):
        """Test that revoking updates task history."""
        task = TaskTriggerHistory.objects.create(
            task_id='task-to-revoke',
            task_name='test.task',
            status='PENDING'
        )
        request = self.factory.post(
            '/monitoring/api/revoke/',
            data=json.dumps({'task_id': 'task-to-revoke'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_revoke_task(request)
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, 'REVOKED')
        self.assertIsNotNone(task.completed_at)

    def test_api_revoke_task_missing_task_id(self):
        """Test revoke without task ID returns error."""
        request = self.factory.post(
            '/monitoring/api/revoke/',
            data=json.dumps({}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_revoke_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class APITriggerTaskTests(TestCase):
    """Tests for api_trigger_task view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.trigger_task')
    def test_api_trigger_task_post(self, mock_trigger):
        """Test POST request to trigger task."""
        mock_trigger.return_value = 'new-task-id'
        request = self.factory.post(
            '/monitoring/api/trigger/',
            data=json.dumps({'task_name': 'test.task', 'args': [1, 2]}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_trigger_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], 'new-task-id')
        self.assertEqual(data['task_name'], 'test.task')

    def test_api_trigger_task_creates_history(self):
        """Test that triggering creates a history entry."""
        with patch('geonode_project.monitoring.views.trigger_task') as mock_trigger:
            mock_trigger.return_value = 'history-task-id'
            request = self.factory.post(
                '/monitoring/api/trigger/',
                data=json.dumps({'task_name': 'test.task', 'args': [1, 2]}),
                content_type='application/json'
            )
            request.user = self.staff_user
            response = api_trigger_task(request)

        history = TaskTriggerHistory.objects.get(task_id='history-task-id')
        self.assertEqual(history.task_name, 'test.task')
        self.assertEqual(history.args, [1, 2])
        self.assertEqual(history.status, 'PENDING')
        self.assertEqual(history.triggered_by, self.staff_user)

    def test_api_trigger_task_missing_task_name(self):
        """Test trigger without task name returns error."""
        request = self.factory.post(
            '/monitoring/api/trigger/',
            data=json.dumps({}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_trigger_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_api_trigger_task_invalid_args_type(self):
        """Test trigger with non-list args returns error."""
        request = self.factory.post(
            '/monitoring/api/trigger/',
            data=json.dumps({'task_name': 'test.task', 'args': 'not-a-list'}),
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_trigger_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Arguments must be a JSON array', data['error'])

    def test_api_trigger_task_invalid_json(self):
        """Test trigger with invalid JSON returns error."""
        request = self.factory.post(
            '/monitoring/api/trigger/',
            data='not-json',
            content_type='application/json'
        )
        request.user = self.staff_user
        response = api_trigger_task(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Invalid JSON', data['error'])


class APITaskHistoryTests(TestCase):
    """Tests for api_task_history view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    @patch('geonode_project.monitoring.views.AsyncResult')
    def test_api_task_history_get(self, mock_async_result):
        """Test GET request to task history."""
        mock_result = Mock()
        mock_result.ready.return_value = False
        mock_async_result.return_value = mock_result

        request = self.factory.get('/monitoring/api/history/')
        request.user = self.staff_user
        response = api_task_history(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('history', data)

    def test_api_task_history_updates_statuses(self):
        """Test that task history updates pending statuses."""
        task = TaskTriggerHistory.objects.create(
            task_id='pending-task',
            task_name='test.task',
            status='PENDING'
        )
        with patch('geonode_project.monitoring.views.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_result.result = 'Done'
            mock_async_result.return_value = mock_result

            request = self.factory.get('/monitoring/api/history/')
            request.user = self.staff_user
            response = api_task_history(request)

        task.refresh_from_db()
        self.assertEqual(task.status, 'SUCCESS')


class APIDeleteTaskTests(TestCase):
    """Tests for api_delete_task view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    def test_api_delete_task_post(self):
        """Test POST request to delete task from history."""
        task = TaskTriggerHistory.objects.create(
            task_id='delete-me',
            task_name='test.task'
        )
        request = self.factory.post('/monitoring/api/history/delete/delete-me/')
        request.user = self.staff_user
        response = api_delete_task(request, 'delete-me')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(TaskTriggerHistory.objects.filter(task_id='delete-me').exists())

    def test_api_delete_task_not_found(self):
        """Test deleting a non-existent task."""
        request = self.factory.post('/monitoring/api/history/delete/nonexistent/')
        request.user = self.staff_user
        response = api_delete_task(request, 'nonexistent')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])


class APIClearHistoryTests(TestCase):
    """Tests for api_clear_history view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    def test_api_clear_history_post(self):
        """Test POST request to clear all history."""
        TaskTriggerHistory.objects.create(task_id='task-1', task_name='test.task')
        TaskTriggerHistory.objects.create(task_id='task-2', task_name='test.task')
        request = self.factory.post('/monitoring/api/history/clear/')
        request.user = self.staff_user
        response = api_clear_history(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(TaskTriggerHistory.objects.count(), 0)


class APICleanupCompletedTests(TestCase):
    """Tests for api_cleanup_completed view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    def test_api_cleanup_completed_post(self):
        """Test POST request to cleanup completed tasks."""
        TaskTriggerHistory.objects.create(task_id='task-1', task_name='test.task', status='SUCCESS')
        TaskTriggerHistory.objects.create(task_id='task-2', task_name='test.task', status='FAILURE')
        TaskTriggerHistory.objects.create(task_id='task-3', task_name='test.task', status='PENDING')
        request = self.factory.post('/monitoring/api/history/cleanup/')
        request.user = self.staff_user
        response = api_cleanup_completed(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(TaskTriggerHistory.objects.count(), 1)
        self.assertTrue(TaskTriggerHistory.objects.filter(task_id='task-3').exists())
