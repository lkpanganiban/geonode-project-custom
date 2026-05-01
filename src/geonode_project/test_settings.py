"""
Test settings for geonode_project.

This settings module is used for running unit tests. It imports from
geonode_project.settings but overrides values as needed for testing.
"""
import os

# Import base settings from geonode_project
from geonode_project.settings import *  # noqa: F401,F403

# Override database to use in-memory SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use a fast password hasher for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable CSRF for tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery settings for testing - run tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Monitoring settings
CELERY_MONITORING_TASK_HISTORY_LIMIT = 50
CELERY_MONITORING_REFRESH_INTERVAL = 0
CELERY_MONITORING_QUEUES = ['celery', 'default']

# Test-specific paths
TEST_ROOT = os.path.dirname(os.path.abspath(__file__))

# Ensure templates can be found during tests
TEMPLATES[0]['DIRS'] = [os.path.join(TEST_ROOT, 'templates')]

# Speed up tests
DEBUG = False
TEMPLATE_DEBUG = False

# Logging - reduce noise during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'WARNING',
    },
}
