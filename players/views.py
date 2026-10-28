"""
Players - Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Q
from .models import Player
from .forms import PlayerProfileForm
from tournaments.models import Registration, Tournament
from teams.models import Team, TeamMember
from payments.models import Payment


@login_required
def create_profile(request):
    """Create player profile after registration."""
    if hasattr(request.user, 'player_profile'):
        return redirect('players:dashboard')

    if request.method == 'POST':
        form = PlayerProfileForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)
            player.user = request.user
            player.save()
            messages.success(request, '🎮 Player profile created! Welcome to the Arena!')
            return redirect('players:dashboard')
    else:
        form = PlayerProfileForm()

    return render(request, 'players/create_profile.html', {'form': form})


@login_required
def dashboard(request):
    """Main player dashboard - HUD style."""
    try:
        player = request.user.player_profile
    except Player.DoesNotExist:
        return redirect('players:create_profile')

    # My registrations
    my_registrations = Registration.objects.filter(
        player=player
    ).select_related('tournament').order_by('-registered_at')[:5]

    # My team
    team_membership = TeamMember.objects.filter(player=player).first()
    my_team = team_membership.team if team_membership else None

    # Upcoming tournaments
    from django.utils import timezone
    upcoming = Tournament.objects.filter(
        start_date__gte=timezone.now().date(),
        is_active=True
    ).order_by('start_date')[:4]

    # Payment status
    recent_payments = Payment.objects.filter(
        player=player
    ).order_by('-created_at')[:3]

    # Pending team invites (for this player)
    from teams.models import TeamInvite, TeamJoinRequest
    pending_invites = TeamInvite.objects.filter(
        invited_player=player,
        status='PENDING'
    ).select_related('team').order_by('-created_at')

    # Pending join requests (for captain)
    pending_join_requests = TeamJoinRequest.objects.filter(
        team__captain=player,
        status='PENDING'
    ).select_related('team', 'player__user').order_by('-created_at')

    # Stats for HUD
    context = {
        'player': player,
        'my_registrations': my_registrations,
        'my_team': my_team,
        'upcoming_tournaments': upcoming,
        'recent_payments': recent_payments,
        'total_registrations': Registration.objects.filter(player=player).count(),
        'pending_invites': pending_invites,
        'pending_join_requests': pending_join_requests,
    }
    return render(request, 'players/dashboard.html', context)


@login_required
def player_profile(request, player_id=None):
    """View a player's public profile."""
    if player_id:
        player = get_object_or_404(Player, id=player_id)
    else:
        player = get_object_or_404(Player, user=request.user)

    return render(request, 'players/profile.html', {'player': player})


@login_required
def edit_profile(request):
    """Edit player profile."""
    player = get_object_or_404(Player, user=request.user)

    if request.method == 'POST':
        form = PlayerProfileForm(request.POST, instance=player)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated! ✅')
            return redirect('players:dashboard')
    else:
        form = PlayerProfileForm(instance=player)

    return render(request, 'players/edit_profile.html', {'form': form})


def player_list(request):
    """Browse all players with filtering."""
    players = Player.objects.select_related('user').all()

    # Filters
    game = request.GET.get('game', '')
    search = request.GET.get('search', '')

    if game:
        players = players.filter(primary_game=game)
    if search:
        players = players.filter(
            Q(ign__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )

    context = {
        'players': players,
        'game_choices': Player.GAME_CHOICES,
        'filters': {'game': game, 'search': search},
    }
    return render(request, 'players/player_list.html', context)
