"""
Unit tests for geonode_project.views module.
"""
import os
import django
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode_project.test_settings')
django.setup()

from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from geonode_project.views import map_app_view


User = get_user_model()


class MapAppViewTests(TestCase):
    """Tests for the map_app_view function."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('geonode_project.views.render')
    def test_map_app_view_renders_correct_template(self, mock_render):
        """Test that map_app_view renders the correct template."""
        from django.http import HttpResponse
        mock_render.return_value = HttpResponse(status=200)
        request = self.factory.get('/map-app/')
        request.user = self.user
        response = map_app_view(request)
        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        self.assertEqual(args[1], 'geonode_project/map_app.html')

    @patch('geonode_project.views.render')
    def test_map_app_view_uses_correct_template_name(self, mock_render):
        """Test that the view uses geonode_project/map_app.html template."""
        from django.http import HttpResponse
        mock_render.return_value = HttpResponse(status=200)
        request = self.factory.get('/map-app/')
        request.user = self.user
        map_app_view(request)
        args, kwargs = mock_render.call_args
        self.assertEqual(args[1], 'geonode_project/map_app.html')

    @patch('geonode_project.views.render')
    def test_map_app_view_via_url(self, mock_render):
        """Test that the map_app view is accessible via URL."""
        from django.http import HttpResponse
        mock_render.return_value = HttpResponse(status=200)
        client = Client()
        response = client.get('/map-app/')
        self.assertEqual(response.status_code, 200)

    @patch('geonode_project.views.render')
    def test_map_app_view_renders_without_user(self, mock_render):
        """Test that map_app_view works with anonymous user."""
        from django.http import HttpResponse
        mock_render.return_value = HttpResponse(status=200)
        request = self.factory.get('/map-app/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        response = map_app_view(request)
        self.assertEqual(response.status_code, 200)

    @patch('geonode_project.views.render')
    def test_map_app_view_returns_render_response(self, mock_render):
        """Test that map_app_view returns a valid HttpResponse."""
        from django.http import HttpResponse
        mock_render.return_value = HttpResponse(status=200)
        request = self.factory.get('/map-app/')
        request.user = self.user
        response = map_app_view(request)
        self.assertIsNotNone(response)
        self.assertTrue(hasattr(response, 'status_code'))
