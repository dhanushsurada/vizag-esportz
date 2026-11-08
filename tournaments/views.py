"""
Tournaments - Views (Cleaned & Fixed)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from .models import Tournament, Registration
from players.models import Player
from payments.models import Payment


# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
def home(request):
    featured = Tournament.objects.filter(
        is_featured=True,
        is_active=True
    ).order_by('-created_at')[:3]

    open_tournaments = Tournament.objects.filter(
        status='REGISTRATION_OPEN',
        is_active=True
    ).order_by('registration_deadline')[:6]

    from leaderboard.models import LeaderboardEntry
    top_players = LeaderboardEntry.objects.select_related(
        'player__user'
    ).order_by('rank')[:5]

    return render(request, 'home.html', {
        'featured_tournaments': featured,
        'open_tournaments': open_tournaments,
        'top_players': top_players,
    })


# ─────────────────────────────────────────────
# TOURNAMENT LIST
# ─────────────────────────────────────────────
def tournament_list(request):
    tournaments = Tournament.objects.filter(is_active=True)

    game = request.GET.get('game', '')
    mode = request.GET.get('mode', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')

    if game:
        tournaments = tournaments.filter(game=game)
    if mode:
        tournaments = tournaments.filter(mode=mode)
    if status:
        tournaments = tournaments.filter(status=status)
    if search:
        tournaments = tournaments.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    return render(request, 'tournaments/list.html', {
        'tournaments': tournaments,
        'game_choices': Tournament.GAME_CHOICES,
        'mode_choices': Tournament.MODE_CHOICES,
        'status_choices': Tournament.STATUS_CHOICES,
        'filters': {
            'game': game,
            'mode': mode,
            'status': status,
            'search': search
        },
    })


# ─────────────────────────────────────────────
# TOURNAMENT DETAIL
# ─────────────────────────────────────────────
def tournament_detail(request, slug):
    tournament = get_object_or_404(
        Tournament,
        slug=slug,
        is_active=True
    )

    registered_players = Registration.objects.filter(
        tournament=tournament,
        status='CONFIRMED'
    ).select_related('player__user').order_by('registered_at')

    user_registration = None

    if request.user.is_authenticated:
        try:
            player = Player.objects.get(user=request.user)
            user_registration = Registration.objects.filter(
                player=player,
                tournament=tournament
            ).first()
        except Player.DoesNotExist:
            pass

    return render(request, 'tournaments/detail.html', {
        'tournament': tournament,
        'registered_players': registered_players,
        'user_registration': user_registration,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    })


# ─────────────────────────────────────────────
# REGISTER TOURNAMENT
# ─────────────────────────────────────────────
@login_required
def register_tournament(request, slug):
    tournament = get_object_or_404(
        Tournament,
        slug=slug,
        is_active=True
    )

    try:
        player = Player.objects.get(user=request.user)
    except Player.DoesNotExist:
        messages.error(request, 'Create your player profile first!')
        return redirect('players:create_profile')

    existing_reg = Registration.objects.filter(
        player=player,
        tournament=tournament
    ).first()

    if existing_reg:
        if existing_reg.status == 'CONFIRMED':
            messages.warning(request, '⚠️ You are already registered for this tournament!')
            return redirect('tournaments:detail', slug=slug)
        elif existing_reg.status == 'PENDING':
            if tournament.entry_fee > 0:
                return redirect('payments:initiate', slug=slug)
            else:
                existing_reg.confirm(by_admin=True)
                messages.success(request, f'✅ Registered for {tournament.title}!')
                return redirect('tournaments:detail', slug=slug)
        elif existing_reg.status == 'CANCELLED':
            # Reset cancelled registration to allow re-registering
            if not tournament.is_registration_open:
                messages.error(request, 'Registration is closed.')
                return redirect('tournaments:detail', slug=slug)
            if tournament.entry_fee == 0:
                existing_reg.confirm(by_admin=True)
                messages.success(request, f'✅ Registered for {tournament.title}!')
                return redirect('tournaments:detail', slug=slug)
            else:
                existing_reg.status = 'PENDING'
                existing_reg.save(update_fields=['status'])
                return redirect('payments:initiate', slug=slug)

    if not tournament.is_registration_open:
        messages.error(request, 'Registration is closed.')
        return redirect('tournaments:detail', slug=slug)

    # FREE TOURNAMENT
    if tournament.entry_fee == 0:
        try:
            with transaction.atomic():
                Registration.objects.create(
                    player=player,
                    tournament=tournament,
                    status='CONFIRMED',
                    payment_status='SUCCESS'
                )
            if tournament.mode in ['SQUAD', 'TEAM5', 'DUO']:
                mode_label = {'SQUAD': 'squad of 4', 'TEAM5': 'team of 5', 'DUO': 'duo'}.get(tournament.mode, 'team')
                messages.success(request,
                    f'✅ Registered for {tournament.title}! '
                    f'This is a {mode_label} tournament — go to Teams section to create your {mode_label} and invite your teammates. '
                    f'Share the tournament details with them so they can register too.'
                )
            else:
                messages.success(request, f'✅ Registered for {tournament.title}! Good luck!')
        except IntegrityError:
            messages.error(request, '⚠️ Registration failed.')

        return redirect('tournaments:detail', slug=slug)

    # PAID TOURNAMENT
    return redirect('payments:initiate', slug=slug)


# ─────────────────────────────────────────────
# MY REGISTRATIONS
# ─────────────────────────────────────────────
@login_required
def my_registrations(request):
    try:
        player = Player.objects.get(user=request.user)
    except Player.DoesNotExist:
        messages.error(request, "Create your player profile first!")
        return redirect('players:create_profile')

    registrations = Registration.objects.filter(
        player=player
    ).select_related('tournament').order_by('-registered_at')

    return render(request, 'tournaments/my_registrations.html', {
        'registrations': registrations
    })


# ─────────────────────────────────────────────
# ADMIN: APPROVE REGISTRATION
# ─────────────────────────────────────────────
@staff_member_required
def approve_registration(request, reg_id):
    if request.method != "POST":
        return redirect('moderator:dashboard')

    reg = get_object_or_404(Registration, id=reg_id)

    if reg.status != 'CONFIRMED':
        success = reg.confirm(by_admin=True)
        if success:
            Payment.objects.filter(player=reg.player, tournament=reg.tournament).update(status='SUCCESS')
            messages.success(request, f"✅ Registration for {reg.player.ign} approved.")
        else:
            messages.error(request, f"⚠️ Could not approve registration for {reg.player.ign}.")
    else:
        messages.info(request, "Already confirmed.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('tournaments:detail', slug=reg.tournament.slug)


# ─────────────────────────────────────────────
# ADMIN: REJECT REGISTRATION
# ─────────────────────────────────────────────
@staff_member_required
def reject_registration(request, reg_id):
    if request.method != "POST":
        return redirect('moderator:dashboard')

    reg = get_object_or_404(Registration, id=reg_id)

    reg.status = 'CANCELLED'
    reg.save(update_fields=['status'])
    Payment.objects.filter(player=reg.player, tournament=reg.tournament, status='PENDING').update(
        status='FAILED', failure_reason='Rejected by moderator'
    )

    messages.warning(request, f"Registration for {reg.player.ign} rejected.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('tournaments:detail', slug=reg.tournament.slug)