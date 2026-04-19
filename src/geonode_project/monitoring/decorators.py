from django.core.exceptions import PermissionDenied
from functools import wraps


def staff_required(view_func):
    """Decorator to check if user is staff"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff access required")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
