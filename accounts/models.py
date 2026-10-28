"""
Accounts App - Custom User Model for Vizag Esportz players
Includes: Email Verification Tokens, Password Reset Tokens
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings
import uuid
from datetime import timedelta


class NSRITUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        # Email is the primary identifier
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Superuser created by email only
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, password, **extra_fields)


class NSRITUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Vizag Esportz community players.
    Uses email as the primary identifier.
    """
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)   # admin-approved
    email_verified = models.BooleanField(default=False)  # email link verified
    date_joined = models.DateTimeField(default=timezone.now)

    # Track failed login attempts for rate limiting
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    objects = NSRITUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Player Account'
        verbose_name_plural = 'Player Accounts'
        db_table = 'users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name

    @property
    def display_name(self):
        return self.get_full_name()

    @property
    def is_account_locked(self):
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            return True
        return False

    def record_failed_login(self):
        """Track failed login and lock after 5 attempts."""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=15)
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])

    def reset_failed_login(self):
        """Clear failed login counters on successful login."""
        if self.failed_login_attempts > 0 or self.account_locked_until:
            self.failed_login_attempts = 0
            self.account_locked_until = None
            self.save(update_fields=['failed_login_attempts', 'account_locked_until'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION TOKEN
# ──────────────────────────────────────────────────────────────────────────────

def email_token_expiry():
    return timezone.now() + timedelta(hours=24)


class EmailVerificationToken(models.Model):
    """
    One-time token sent to the user's email to verify ownership.
    Token is UUID-based, expires in 24 hours, and is invalidated after use.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=email_token_expiry)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_verification_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"EmailVerify({self.user.email}) — {'used' if self.is_used else 'pending'}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET TOKEN
# ──────────────────────────────────────────────────────────────────────────────

def reset_token_expiry():
    return timezone.now() + timedelta(minutes=30)


class PasswordResetToken(models.Model):
    """
    One-time token for password reset.
    UUID-based, expires in 30 minutes, single-use only.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=reset_token_expiry)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"PasswordReset({self.user.email}) — {'used' if self.is_used else 'pending'}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN ACCESS LOG
# ──────────────────────────────────────────────────────────────────────────────

class AdminAccessLog(models.Model):
    """
    Logs every access attempt to the admin panel.
    """
    ACTION_CHOICES = [
        ('ACCESS', 'Admin Accessed'),
        ('DENIED', 'Access Denied'),
        ('LOGIN', 'Admin Login'),
        ('LOGOUT', 'Admin Logout'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='admin_access_logs'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'admin_access_logs'
        ordering = ['-timestamp']

    def __str__(self):
        user_str = self.user.email if self.user else 'Anonymous'
        return f"[{self.action}] {user_str} @ {self.timestamp:%Y-%m-%d %H:%M}"
