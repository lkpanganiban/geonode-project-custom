"""
Unit tests for geonode_project.monitoring.models module.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode_project.test_settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from geonode_project.monitoring.models import TaskTriggerHistory


User = get_user_model()


class TaskTriggerHistoryModelTests(TestCase):
    """Tests for the TaskTriggerHistory model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        self.task_history = TaskTriggerHistory.objects.create(
            task_id='test-task-id-12345',
            task_name='test_task',
            args=[1, 2, 3],
            kwargs={'key': 'value'},
            triggered_by=self.user,
            status='PENDING'
        )

    def test_task_trigger_history_creation(self):
        """Test that a TaskTriggerHistory instance can be created."""
        self.assertIsNotNone(self.task_history.id)
        self.assertEqual(self.task_history.task_id, 'test-task-id-12345')
        self.assertEqual(self.task_history.task_name, 'test_task')

    def test_task_trigger_history_str_representation(self):
        """Test the string representation of TaskTriggerHistory."""
        expected = f"{self.task_history.task_name} ({self.task_history.task_id[:8]}) - {self.task_history.status}"
        self.assertEqual(str(self.task_history), expected)

    def test_default_status_is_pending(self):
        """Test that default status is PENDING."""
        new_task = TaskTriggerHistory.objects.create(
            task_id='new-task-id',
            task_name='new_task'
        )
        self.assertEqual(new_task.status, 'PENDING')

    def test_status_choices(self):
        """Test that valid status choices are accepted."""
        valid_statuses = ['PENDING', 'SUCCESS', 'FAILURE', 'RETRY', 'REVOKED']
        for status in valid_statuses:
            task = TaskTriggerHistory.objects.create(
                task_id=f'task-{status}',
                task_name=f'task_{status.lower()}',
                status=status
            )
            self.assertEqual(task.status, status)

    def test_task_id_unique_constraint(self):
        """Test that task_id must be unique."""
        with self.assertRaises(Exception):
            TaskTriggerHistory.objects.create(
                task_id='test-task-id-12345',
                task_name='duplicate_task'
            )

    def test_triggered_by_can_be_null(self):
        """Test that triggered_by can be null."""
        task = TaskTriggerHistory.objects.create(
            task_id='no-user-task',
            task_name='no_user_task',
            triggered_by=None
        )
        self.assertIsNone(task.triggered_by)

    def test_args_default_empty_list(self):
        """Test that args defaults to empty list."""
        task = TaskTriggerHistory.objects.create(
            task_id='empty-args-task',
            task_name='empty_args_task'
        )
        self.assertEqual(task.args, [])

    def test_kwargs_default_empty_dict(self):
        """Test that kwargs defaults to empty dict."""
        task = TaskTriggerHistory.objects.create(
            task_id='empty-kwargs-task',
            task_name='empty_kwargs_task'
        )
        self.assertEqual(task.kwargs, {})

    def test_result_can_be_blank(self):
        """Test that result can be blank/null."""
        task = TaskTriggerHistory.objects.create(
            task_id='no-result-task',
            task_name='no_result_task',
            result=None
        )
        self.assertIsNone(task.result)

    def test_completed_at_can_be_null(self):
        """Test that completed_at can be null."""
        task = TaskTriggerHistory.objects.create(
            task_id='incomplete-task',
            task_name='incomplete_task',
            completed_at=None
        )
        self.assertIsNone(task.completed_at)

    def test_ordering_by_triggered_at_desc(self):
        """Test that tasks are ordered by triggered_at descending."""
        # Create another task
        task2 = TaskTriggerHistory.objects.create(
            task_id='task-2',
            task_name='task_2'
        )
        tasks = list(TaskTriggerHistory.objects.all())
        # The newest task should be first
        self.assertEqual(tasks[0], task2)

    def test_meta_verbose_name(self):
        """Test model meta options."""
        self.assertEqual(TaskTriggerHistory._meta.verbose_name, 'Task Trigger History')
        self.assertEqual(TaskTriggerHistory._meta.verbose_name_plural, 'Task Trigger Histories')

    def test_triggered_at_auto_now_add(self):
        """Test that triggered_at is set automatically."""
        self.assertIsNotNone(self.task_history.triggered_at)
        self.assertLessEqual(self.task_history.triggered_at, timezone.now())

    def test_related_name_triggered_tasks(self):
        """Test the related_name for triggered_by."""
        self.assertIn(self.task_history, self.user.triggered_tasks.all())
