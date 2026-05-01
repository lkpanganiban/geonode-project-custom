"""
Unit tests for geonode_project.monitoring.decorators module.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode_project.test_settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from geonode_project.monitoring.decorators import staff_required


User = get_user_model()


class StaffRequiredDecoratorTests(TestCase):
    """Tests for the staff_required decorator."""

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

    def test_staff_required_allows_staff(self):
        """Test that staff_required allows access to staff users."""
        @staff_required
        def dummy_view(request):
            return 'success'

        request = self.factory.get('/test/')
        request.user = self.staff_user
        result = dummy_view(request)
        self.assertEqual(result, 'success')

    def test_staff_required_denies_non_staff(self):
        """Test that staff_required denies access to non-staff users."""
        @staff_required
        def dummy_view(request):
            return 'success'

        request = self.factory.get('/test/')
        request.user = self.regular_user
        with self.assertRaises(PermissionDenied) as context:
            dummy_view(request)
        self.assertIn('Staff access required', str(context.exception))

    def test_staff_required_denies_anonymous(self):
        """Test that staff_required denies access to anonymous users."""
        @staff_required
        def dummy_view(request):
            return 'success'

        request = self.factory.get('/test/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            dummy_view(request)

    def test_staff_required_preserves_function_name(self):
        """Test that the decorator preserves the wrapped function's name."""
        @staff_required
        def my_view(request):
            """My view docstring."""
            return 'success'

        self.assertEqual(my_view.__name__, 'my_view')

    def test_staff_required_passes_args_and_kwargs(self):
        """Test that the decorator passes args and kwargs correctly."""
        @staff_required
        def dummy_view(request, arg1, arg2, kwarg1=None):
            return (arg1, arg2, kwarg1)

        request = self.factory.get('/test/')
        request.user = self.staff_user
        result = dummy_view(request, 'a', 'b', kwarg1='c')
        self.assertEqual(result, ('a', 'b', 'c'))

    def test_staff_required_with_multiple_decorators(self):
        """Test that staff_required works with other decorators."""
        def another_decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        @another_decorator
        @staff_required
        def dummy_view(request):
            return 'success'

        request = self.factory.get('/test/')
        request.user = self.staff_user
        result = dummy_view(request)
        self.assertEqual(result, 'success')
