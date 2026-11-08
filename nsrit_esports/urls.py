"""
Vizag Esportz - Main URL Configuration
Admin URL is read from settings (configurable via .env for security).
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


# Clean admin url path
_custom_admin_raw = getattr(settings, 'ADMIN_URL', 'admin/').strip('/')
_custom_admin_path = f"{_custom_admin_raw}/" if _custom_admin_raw else 'admin/'

urlpatterns = [
    # ── Standard Django Admin (always active at /admin/) ──
    path('admin/', admin.site.urls),
]

if _custom_admin_path != 'admin/':
    urlpatterns.insert(0, path(_custom_admin_path, admin.site.urls))

urlpatterns += [
    # ── Home page ────────────────────────────────────────────────────────────
    path('', include('tournaments.urls_home')),

    # ── Authentication + Email Verification + Password Reset ─────────────────
    path('accounts/', include('accounts.urls')),

    # ── Player profiles ───────────────────────────────────────────────────────
    path('players/', include('players.urls')),

    # ── Tournaments ───────────────────────────────────────────────────────────
    path('tournaments/', include('tournaments.urls')),

    # ── Teams ─────────────────────────────────────────────────────────────────
    path('teams/', include('teams.urls')),

    # ── Payments ──────────────────────────────────────────────────────────────
    path('payments/', include('payments.urls')),

    # ── Leaderboard ───────────────────────────────────────────────────────────
    path('leaderboard/', include('leaderboard.urls')),

    # ── Moderator Dashboard ───────────────────────────────────────────────────
    path('moderator/', include('moderator.urls')),

    # ── Matches / Brackets ────────────────────────────────────────────────────
    path('matches/', include('matches.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ── Admin site branding ───────────────────────────────────────────────────────
admin.site.site_header = "Vizag Esportz — Control Panel"
admin.site.site_title = "Vizag Esportz"
admin.site.index_title = "Vizag Esportz Administration"
