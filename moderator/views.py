"""
Moderator Dashboard Views
Accessible to: is_staff (Moderator) and is_superuser (Super Admin)
Features: Dashboard stats, registrations, payments, reports
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q

from .decorators import moderator_required
from accounts.models import NSRITUser
from players.models import Player
from tournaments.models import Tournament, Registration
from payments.models import Payment


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@moderator_required
def dashboard(request):
    """Moderator dashboard — overview stats."""
    now = timezone.now()

    total_users     = NSRITUser.objects.filter(is_active=True, is_staff=False, is_superuser=False).count()
    total_players   = Player.objects.count()
    total_tournaments = Tournament.objects.filter(is_active=True).count()
    open_tournaments  = Tournament.objects.filter(status='REGISTRATION_OPEN', is_active=True).count()

    pending_payments = Payment.objects.filter(status='PENDING').count()
    failed_payments  = Payment.objects.filter(status='FAILED').count()
    success_payments = Payment.objects.filter(status='SUCCESS').count()

    total_revenue = Payment.objects.filter(status='SUCCESS').aggregate(
        total=Sum('amount')
    )['total'] or 0

    pending_registrations = Registration.objects.filter(status='PENDING').count()
    confirmed_registrations = Registration.objects.filter(status='CONFIRMED').count()

    locked_accounts = NSRITUser.objects.filter(
        account_locked_until__gt=now
    ).count()

    unverified_emails = NSRITUser.objects.filter(email_verified=False, is_active=True).count()

    recent_registrations = Registration.objects.select_related(
        'player__user', 'tournament'
    ).order_by('-registered_at')[:8]

    recent_payments = Payment.objects.select_related(
        'player__user', 'tournament'
    ).order_by('-created_at')[:8]

    context = {
        'total_users': total_users,
        'total_players': total_players,
        'total_tournaments': total_tournaments,
        'open_tournaments': open_tournaments,
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'success_payments': success_payments,
        'total_revenue_inr': total_revenue / 100,
        'pending_registrations': pending_registrations,
        'confirmed_registrations': confirmed_registrations,
        'locked_accounts': locked_accounts,
        'unverified_emails': unverified_emails,
        'recent_registrations': recent_registrations,
        'recent_payments': recent_payments,
    }
    return render(request, 'moderator/dashboard.html', context)


# ── REGISTRATIONS ─────────────────────────────────────────────────────────────

@moderator_required
def registrations(request):
    """View and manage all tournament registrations."""
    regs = Registration.objects.select_related(
        'player__user', 'tournament'
    ).order_by('-registered_at')

    status_filter = request.GET.get('status', '')
    tournament_filter = request.GET.get('tournament', '')

    if status_filter:
        regs = regs.filter(status=status_filter)
    if tournament_filter:
        regs = regs.filter(tournament__id=tournament_filter)

    tournaments = Tournament.objects.filter(is_active=True)

    context = {
        'registrations': regs,
        'tournaments': tournaments,
        'status_filter': status_filter,
        'tournament_filter': tournament_filter,
        'status_choices': Registration.STATUS_CHOICES,
    }
    return render(request, 'moderator/registrations.html', context)


@moderator_required
def approve_registration(request, reg_id):
    """Confirm a pending registration."""
    reg = get_object_or_404(Registration, id=reg_id)
    reg.confirm()
    messages.success(request, f'✅ Registration for {reg.player.ign} confirmed.')
    return redirect('moderator:registrations')


@moderator_required
def reject_registration(request, reg_id):
    """Cancel a registration."""
    reg = get_object_or_404(Registration, id=reg_id)
    reg.status = 'CANCELLED'
    reg.save()
    messages.warning(request, f'Registration for {reg.player.ign} cancelled.')
    return redirect('moderator:registrations')


# ── PAYMENTS ─────────────────────────────────────────────────────────────────

@moderator_required
def payments(request):
    """View all payments with status filtering."""
    all_payments = Payment.objects.select_related(
        'player__user', 'tournament'
    ).order_by('-created_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        all_payments = all_payments.filter(status=status_filter)

    # Summary counts
    summary = {
        'pending': Payment.objects.filter(status='PENDING').count(),
        'success': Payment.objects.filter(status='SUCCESS').count(),
        'failed':  Payment.objects.filter(status='FAILED').count(),
        'refunded': Payment.objects.filter(status='REFUNDED').count(),
        'total_revenue': (Payment.objects.filter(status='SUCCESS').aggregate(
            t=Sum('amount'))['t'] or 0) / 100,
    }

    context = {
        'payments': all_payments,
        'status_filter': status_filter,
        'status_choices': Payment.STATUS_CHOICES,
        'summary': summary,
    }
    return render(request, 'moderator/payments.html', context)


@moderator_required
def mark_payment_failed(request, payment_id):
    """Manually mark a payment as failed (e.g. disputed)."""
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = 'FAILED'
    payment.save()
    messages.warning(request, f'Payment #{payment.id} marked as FAILED.')
    return redirect('moderator:payments')


# ── PLAYERS ───────────────────────────────────────────────────────────────────

@moderator_required
def players(request):
    """View all registered players."""
    all_players = Player.objects.select_related('user').order_by('-rank_points')

    search = request.GET.get('search', '')
    if search:
        all_players = all_players.filter(
            Q(ign__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__email__icontains=search)
        )

    context = {
        'players': all_players,
        'search': search,
    }
    return render(request, 'moderator/players.html', context)


# ── LOCKED ACCOUNTS ───────────────────────────────────────────────────────────

@moderator_required
def locked_accounts(request):
    """View and unlock locked accounts."""
    now = timezone.now()
    locked = NSRITUser.objects.filter(account_locked_until__gt=now).order_by('account_locked_until')
    return render(request, 'moderator/locked_accounts.html', {'locked': locked})


@moderator_required
def unlock_account(request, user_id):
    """Unlock a specific account."""
    user = get_object_or_404(NSRITUser, id=user_id)
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
    messages.success(request, f'🔓 Account for {user.email} unlocked.')
    return redirect('moderator:locked_accounts')
