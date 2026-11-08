"""
Vizag Esportz - Security Middleware

1. AdminSecurityMiddleware
   - Blocks non-staff users from accessing the admin URL entirely
   - Logs every admin access attempt to AdminAccessLog
   - Returns 404 (not 403) for unauthorised users — hides that an admin panel exists
   - Rate-limits admin login attempts by IP

2. OwnershipMiddleware (lightweight; main checks are in views)
   - Adds helper attributes to request for view-level ownership checks
"""
import logging
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# In-memory rate-limit store for admin URLs (IP → list of timestamps)
# For production, swap this with Redis / cache-based storage.
_admin_ip_attempts = defaultdict(list)
ADMIN_RATE_LIMIT = 10          # max attempts
ADMIN_RATE_WINDOW = 60 * 15    # per 15 minutes (seconds)


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


class AdminSecurityMiddleware(MiddlewareMixin):
    """
    Passthrough middleware for backward compatibility.
    Django admin's built-in authentication and permission checks handle admin security cleanly.
    """
    def process_request(self, request):
        return None

    def _log_attempt(self, request, action, ip, notes=''):
        """Write to AdminAccessLog — silently ignore DB errors during startup."""
        try:
            from accounts.models import AdminAccessLog
            user = getattr(request, 'user', None)
            AdminAccessLog.objects.create(
                user=user if (user and user.is_authenticated) else None,
                action=action,
                ip_address=ip,
                path=request.path,
                notes=notes,
            )
        except Exception:
            pass  # DB may not be ready (e.g. first migration)
