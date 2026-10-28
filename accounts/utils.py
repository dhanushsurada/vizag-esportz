"""
Accounts - Email Utilities
Sends verification and password reset emails with Vizag Esportz styling.
Falls back to console backend in development.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract real client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def send_verification_email(request, user, token_obj):
    """
    Send the email-verification link to the user's email address.
    """
    verify_url = request.build_absolute_uri(
        f'/accounts/verify-email/{token_obj.token}/'
    )
    context = {
        'user': user,
        'verify_url': verify_url,
        'token': token_obj,
        'site_name': 'Vizag Esportz',
        'expires_hours': 24,
    }
    html_body = render_to_string('accounts/emails/verification_email.html', context)
    text_body = strip_tags(html_body)

    try:
        msg = EmailMultiAlternatives(
            subject='🎮 Verify Your Vizag Esportz Email',
            body=text_body,
            from_email=f'Vizag Esportz <{settings.EMAIL_HOST_USER or "noreply@vizagesportz.com"}>',
            to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


def send_password_reset_email(request, user, token_obj):
    """
    Send the password-reset link with a 30-minute expiry warning.
    """
    reset_url = request.build_absolute_uri(
        f'/accounts/password-reset/confirm/{token_obj.token}/'
    )
    context = {
        'user': user,
        'reset_url': reset_url,
        'token': token_obj,
        'site_name': 'Vizag Esportz',
        'expires_minutes': 30,
    }
    html_body = render_to_string('accounts/emails/password_reset_email.html', context)
    text_body = strip_tags(html_body)

    try:
        msg = EmailMultiAlternatives(
            subject='🔑 Reset Your Vizag Esportz Password',
            body=text_body,
            from_email=f'Vizag Esportz <{settings.EMAIL_HOST_USER or "noreply@vizagesportz.com"}>',
            to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {e}")
        return False
