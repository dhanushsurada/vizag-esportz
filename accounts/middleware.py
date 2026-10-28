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
    Protects the Django admin panel:

    • Non-staff requests → 404 (admin URL is completely hidden)
    • Staff requests    → allowed through + logged
    • IP rate-limit     → blocks brute-force on admin login
    • Logs every attempt in AdminAccessLog (if DB is ready)
    """

    def process_request(self, request):
        admin_url = getattr(settings, 'ADMIN_URL', 'admin/')
        # Normalise: strip leading slash
        admin_prefix = admin_url.lstrip('/')

        if not request.path.lstrip('/').startswith(admin_prefix):
            return None   # not an admin path — do nothing

        client_ip = _get_client_ip(request)

        # ── Rate limiting ─────────────────────────────────────────────────────
        now = timezone.now().timestamp()
        window_start = now - ADMIN_RATE_WINDOW
        attempts = [t for t in _admin_ip_attempts[client_ip] if t > window_start]
        attempts.append(now)
        _admin_ip_attempts[client_ip] = attempts

        if len(attempts) > ADMIN_RATE_LIMIT:
            logger.warning(f"Admin rate-limit exceeded for IP {client_ip}")
            self._log_attempt(request, 'DENIED', client_ip, 'Rate limit exceeded')
            raise Http404  # looks like a normal 404 to the attacker

        # ── Authentication check ──────────────────────────────────────────────
        user = getattr(request, 'user', None)
        is_authenticated = user is not None and user.is_authenticated
        is_staff = is_authenticated and user.is_staff
        is_superuser = is_authenticated and user.is_superuser

        if not is_staff:
            # Unauthenticated or regular user → 404 (hide admin existence)
            logger.warning(
                f"Unauthorised admin access attempt: "
                f"user={'anon' if not is_authenticated else (user.email)} "
                f"path={request.path} ip={client_ip}"
            )
            self._log_attempt(request, 'DENIED', client_ip, 'Not staff/superuser')
            raise Http404

        # ── Allowed — log the access ──────────────────────────────────────────
        self._log_attempt(request, 'ACCESS', client_ip, 'Permitted')
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
