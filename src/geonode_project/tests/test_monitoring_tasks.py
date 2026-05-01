"""
Unit tests for geonode_project.monitoring.tasks module.
"""
import os
import django
from unittest.mock import patch, Mock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode_project.test_settings')
django.setup()

from django.test import TestCase
from geonode_project.monitoring.tasks import sample_task, hello_world, calculate_sum


class SampleTaskTests(TestCase):
    """Tests for the sample_task Celery task."""

    @patch('geonode_project.monitoring.tasks.time.sleep')
    @patch('geonode_project.monitoring.tasks.random.choice')
    def test_sample_task_success(self, mock_random_choice, mock_sleep):
        """Test sample_task completes successfully."""
        mock_random_choice.return_value = False  # Don't fail randomly
        with patch.object(sample_task, 'update_state') as mock_update:
            result = sample_task(duration=2, should_succeed=True)

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['duration'], 2)
        self.assertEqual(result['task_name'], 'sample_task')
        self.assertIn('completed successfully', result['message'])
        self.assertTrue(mock_update.called)

    @patch('geonode_project.monitoring.tasks.time.sleep')
    def test_sample_task_updates_progress(self, mock_sleep):
        """Test that sample_task updates progress state."""
        with patch.object(sample_task, 'update_state') as mock_update:
            sample_task(duration=3, should_succeed=True)

        # Should call update_state for each second of duration
        self.assertEqual(mock_update.call_count, 3)
        # Check first progress update
        first_call = mock_update.call_args_list[0]
        self.assertEqual(first_call[1]['state'], 'PROGRESS')
        self.assertEqual(first_call[1]['meta']['current'], 1)
        self.assertEqual(first_call[1]['meta']['total'], 3)

    @patch('geonode_project.monitoring.tasks.time.sleep')
    @patch('geonode_project.monitoring.tasks.random.choice')
    def test_sample_task_random_failure(self, mock_random_choice, mock_sleep):
        """Test sample_task can fail randomly when should_succeed=False."""
        mock_random_choice.return_value = True  # Force failure
        with patch.object(sample_task, 'update_state'):
            with self.assertRaises(Exception) as context:
                sample_task(duration=1, should_succeed=False)
        self.assertIn('failed randomly', str(context.exception))

    @patch('geonode_project.monitoring.tasks.time.sleep')
    def test_sample_task_zero_duration(self, mock_sleep):
        """Test sample_task with zero duration."""
        result = sample_task(duration=0, should_succeed=True)
        self.assertEqual(result['status'], 'completed')
        mock_sleep.assert_not_called()


class HelloWorldTaskTests(TestCase):
    """Tests for the hello_world Celery task."""

    def test_hello_world_default(self):
        """Test hello_world with default name."""
        result = hello_world()
        self.assertEqual(result, 'Hello, World!')

    def test_hello_world_custom_name(self):
        """Test hello_world with custom name."""
        result = hello_world(name='Alice')
        self.assertEqual(result, 'Hello, Alice!')

    def test_hello_world_empty_name(self):
        """Test hello_world with empty name."""
        result = hello_world(name='')
        self.assertEqual(result, 'Hello, !')


class CalculateSumTaskTests(TestCase):
    """Tests for the calculate_sum Celery task."""

    def test_calculate_sum_basic(self):
        """Test calculate_sum with a basic list of numbers."""
        result = calculate_sum([1, 2, 3, 4, 5])
        self.assertEqual(result['sum'], 15)
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['numbers'], [1, 2, 3, 4, 5])

    def test_calculate_sum_empty_list(self):
        """Test calculate_sum with empty list."""
        result = calculate_sum([])
        self.assertEqual(result['sum'], 0)
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['numbers'], [])

    def test_calculate_sum_negative_numbers(self):
        """Test calculate_sum with negative numbers."""
        result = calculate_sum([-1, -2, 3])
        self.assertEqual(result['sum'], 0)
        self.assertEqual(result['count'], 3)

    def test_calculate_sum_floats(self):
        """Test calculate_sum with floating point numbers."""
        result = calculate_sum([1.5, 2.5, 3.0])
        self.assertEqual(result['sum'], 7.0)
        self.assertEqual(result['count'], 3)

    def test_calculate_sum_single_element(self):
        """Test calculate_sum with single element."""
        result = calculate_sum([42])
        self.assertEqual(result['sum'], 42)
        self.assertEqual(result['count'], 1)

    def test_calculate_sum_large_numbers(self):
        """Test calculate_sum with large numbers."""
        result = calculate_sum([1000000, 2000000, 3000000])
        self.assertEqual(result['sum'], 6000000)
        self.assertEqual(result['count'], 3)
