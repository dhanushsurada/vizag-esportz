"""
Teams App - Team Model, Captain/Member Management
"""
from django.db import models
from django.conf import settings
from players.models import Player


class Team(models.Model):
    GAME_CHOICES = [
        ('BGMI', 'BGMI'),
        ('VALORANT', 'Valorant'),
        ('COD', 'Call of Duty Mobile'),
        ('FREE_FIRE', 'Free Fire'),
        ('CS2', 'Counter-Strike 2'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    tag = models.CharField(max_length=10, help_text='Short team tag e.g. VZG')
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='team_banners/', blank=True, null=True)
    description = models.TextField(max_length=500, blank=True)

    captain = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        related_name='captained_team'
    )

    # Stats
    total_wins = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    rank_points = models.IntegerField(default=0)

    is_recruiting = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teams'
        ordering = ['-rank_points']
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def __str__(self):
        return f"[{self.tag}] {self.name}"

    @property
    def win_rate(self):
        if self.total_matches > 0:
            return round((self.total_wins / self.total_matches) * 100, 1)
        return 0.0

    @property
    def member_count(self):
        return self.members.count()

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('teams:detail', kwargs={'slug': self.slug})


class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('CAPTAIN', 'Captain'),
        ('IGL', 'In-Game Leader'),
        ('FRAGGER', 'Fragger'),
        ('SUPPORT', 'Support'),
        ('SCOUT', 'Scout'),
        ('SNIPER', 'Sniper'),
        ('SUBSTITUTE', 'Substitute'),
        ('MEMBER', 'Member'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='team_membership')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='MEMBER')
    jersey_number = models.IntegerField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'team_members'
        unique_together = [('team', 'player')]
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'

    def __str__(self):
        return f"{self.player.ign} @ {self.team.name} [{self.role}]"


class TeamInvite(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invites')
    invited_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='team_invites')
    invited_by = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='sent_invites')
    role = models.CharField(max_length=15, choices=TeamMember.ROLE_CHOICES, default='MEMBER')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    message = models.TextField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_invites'
        unique_together = [('team', 'invited_player')]

    def __str__(self):
        return f"Invite: {self.invited_player.ign} → {self.team.name}"


class TeamJoinRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='join_requests')
    role = models.CharField(max_length=15, choices=TeamMember.ROLE_CHOICES, default='MEMBER')
    message = models.TextField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_join_requests'
        unique_together = [('team', 'player')]

    def __str__(self):
        return f"Request: {self.player.ign} → {self.team.name} [{self.status}]"
