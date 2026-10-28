"""
Accounts - Views: Registration, Login, Logout, Email Verification, Password Reset
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.utils.safestring import mark_safe
import uuid
import logging

from .forms import (
    RegistrationForm, EsportzLoginForm, ProfileUpdateForm,
    PasswordResetRequestForm, PasswordResetConfirmForm,
    ResendVerificationForm,
)
from .models import EmailVerificationToken, PasswordResetToken
from .utils import send_verification_email, send_password_reset_email, get_client_ip

User = get_user_model()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRATION
# ──────────────────────────────────────────────────────────────────────────────

class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('players:dashboard')
        form = RegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # 🔥 Auto-verify user (for launch)
            user.email_verified = True
            user.is_verified = True
            user.save(update_fields=['email_verified', 'is_verified'])

            messages.success(
                request,
                f'Welcome {user.first_name}! 🎮 Account created successfully. You can now log in!'
            )

            return redirect('accounts:login')   # ✅ INSIDE IF BLOCK

        return render(request, self.template_name, {'form': form})  # ✅ fallback


# ──────────────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION
# ──────────────────────────────────────────────────────────────────────────────

class VerificationSentView(View):
    template_name = 'accounts/email_verification_sent.html'

    def get(self, request):
        return render(request, self.template_name)


class VerifyEmailView(View):
    """Handles the token link from the verification email."""
    template_name = 'accounts/verify_email_result.html'

    def get(self, request, token):
        context = {}
        try:
            token_uuid = uuid.UUID(str(token))
            token_obj = EmailVerificationToken.objects.select_related('user').get(token=token_uuid)
        except (ValueError, EmailVerificationToken.DoesNotExist):
            context['status'] = 'invalid'
            context['message'] = 'This verification link is invalid or has been tampered with.'
            return render(request, self.template_name, context)

        if token_obj.is_used:
            context['status'] = 'already_used'
            context['message'] = 'This link has already been used. Your email may already be verified.'
            return render(request, self.template_name, context)

        if token_obj.is_expired:
            context['status'] = 'expired'
            context['message'] = 'This link has expired (24-hour limit). Please request a new one.'
            context['show_resend'] = True
            context['user_email'] = token_obj.user.email
            return render(request, self.template_name, context)

        # All good — verify the user's email
        user = token_obj.user
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        token_obj.mark_used()
        logger.info(f"Email verified for user {user.email}")

        context['status'] = 'success'
        context['user'] = user
        return render(request, self.template_name, context)


class ResendVerificationView(View):
    """Allow user to request a new verification email."""
    template_name = 'accounts/resend_verification.html'

    def get(self, request):
        form = ResendVerificationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email, is_active=True).first()
            # Anti-enumeration: always show same message
            if user and not user.email_verified:
                # Invalidate old tokens
                EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
                token_obj = EmailVerificationToken.objects.create(user=user)
                send_verification_email(request, user, token_obj)

            messages.success(
                request,
                'If that email exists and is unverified, a new link has been sent. Check your inbox!'
            )
            return redirect('accounts:verification_sent')
        return render(request, self.template_name, {'form': form})


# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────

@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('players:dashboard')
        form = EsportzLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = EsportzLoginForm(request, data=request.POST)
        # Lookup by email
        email_input = request.POST.get('username', '').lower().strip()

        # Lookup user to check lock status before authenticate()
        try:
            user_obj = User.objects.get(email=email_input)
            if user_obj.is_account_locked:
                messages.error(
                    request,
                    '🔒 Your account is temporarily locked due to too many failed attempts. '
                    'Try again in 15 minutes or reset your password.'
                )
                return render(request, self.template_name, {'form': form})
        except User.DoesNotExist:
            user_obj = None

        if form.is_valid():
            user = form.get_user()

            # Check email verification
            # 🔥 Skip verification check (since we auto-verified)
            # if not user.email_verified:
            #     resend_url = reverse('accounts:resend_verification')
            #     messages.warning(
            #         request,
            #         mark_safe(
            #             f'📧 Please verify your email first. Check your inbox at '
            #             f'{user.email} or <a href="{resend_url}" '
            #             f'class="text-cyan text-decoration-none">resend the verification email</a>.'
            #         )
            #     )
            #     return render(request, self.template_name, {'form': form})

            user.reset_failed_login()
            login(request, user)
            logger.info(f"Successful login: {user.email} from {get_client_ip(request)}")
            messages.success(request, f'Welcome back, {user.first_name}! Ready to battle? ⚔️')
            next_url = request.GET.get('next') or reverse('players:dashboard')
            return redirect(next_url)

        # Failed login — record the attempt
        if user_obj:
            user_obj.record_failed_login()
            remaining = max(0, 5 - user_obj.failed_login_attempts)
            logger.warning(
                f"Failed login attempt for {email_input} from {get_client_ip(request)}"
            )
            if remaining > 0:
                messages.error(
                    request,
                    f'Invalid credentials. {remaining} attempt(s) remaining before account lock.'
                )
            else:
                messages.error(
                    request,
                    '🔒 Account locked for 15 minutes due to too many failed attempts.'
                )
        else:
            messages.error(request, 'Invalid email or password.')

        return render(request, self.template_name, {'form': form})


# ──────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out. See you on the battlefield! 👋')
    return redirect('home')


# ──────────────────────────────────────────────────────────────────────────────
# PROFILE UPDATE
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def profile_update_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('players:dashboard')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile_update.html', {'form': form})


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — STEP 1: REQUEST FORM
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetRequestView(View):
    template_name = 'accounts/password_reset_request.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('players:dashboard')
        form = PasswordResetRequestForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                # Invalidate all previous unused tokens
                PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
                # Create fresh token
                token_obj = PasswordResetToken.objects.create(
                    user=user,
                    ip_address=get_client_ip(request)
                )
                send_password_reset_email(request, user, token_obj)
                logger.info(
                    f"Password reset requested for {user.email} from {get_client_ip(request)}"
                )
            # Always redirect to same page (anti-enumeration)
            return redirect('accounts:password_reset_sent')
        return render(request, self.template_name, {'form': form})


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — SENT CONFIRMATION PAGE
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetSentView(View):
    template_name = 'accounts/password_reset_sent.html'

    def get(self, request):
        return render(request, self.template_name)


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — STEP 2: CONFIRM + SET NEW PASSWORD
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetConfirmView(View):
    template_name = 'accounts/password_reset_confirm.html'

    def _get_token(self, token_str):
        """Validate and return the token object, or None."""
        try:
            token_uuid = uuid.UUID(str(token_str))
            return PasswordResetToken.objects.select_related('user').get(token=token_uuid)
        except (ValueError, PasswordResetToken.DoesNotExist):
            return None

    def get(self, request, token):
        token_obj = self._get_token(token)
        context = {'token': token}

        if not token_obj:
            context['error'] = 'invalid'
            return render(request, self.template_name, context)
        if token_obj.is_used:
            context['error'] = 'used'
            return render(request, self.template_name, context)
        if token_obj.is_expired:
            context['error'] = 'expired'
            return render(request, self.template_name, context)

        form = PasswordResetConfirmForm()
        context['form'] = form
        context['user'] = token_obj.user
        return render(request, self.template_name, context)

    def post(self, request, token):
        token_obj = self._get_token(token)
        context = {'token': token}

        if not token_obj or not token_obj.is_valid:
            context['error'] = 'invalid'
            return render(request, self.template_name, context)

        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user = token_obj.user
            user.set_password(form.cleaned_data['new_password'])
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.save(update_fields=['password', 'failed_login_attempts', 'account_locked_until'])
            token_obj.mark_used()
            logger.info(f"Password reset completed for {user.email}")
            messages.success(
                request,
                '✅ Password reset successful! You can now log in with your new password.'
            )
            return redirect('accounts:password_reset_done')

        context['form'] = form
        context['user'] = token_obj.user
        return render(request, self.template_name, context)


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — DONE PAGE
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetDoneView(View):
    template_name = 'accounts/password_reset_done.html'

    def get(self, request):
        return render(request, self.template_name)
