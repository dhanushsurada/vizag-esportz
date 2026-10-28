"""
Players App - Player Profile Model
"""
from django.db import models
from django.conf import settings
from django.db.models import Sum, Count


class Player(models.Model):
    """Extended player profile linked to a user account."""

    GAME_CHOICES = [
        ('BGMI', 'BGMI (Battlegrounds Mobile India)'),
        ('VALORANT', 'Valorant'),
        ('COD', 'Call of Duty Mobile'),
        ('FREE_FIRE', 'Free Fire'),
        ('CS2', 'Counter-Strike 2'),
        ('FIFA', 'FIFA / EA FC'),
        ('CHESS', 'Chess Online'),
        ('POKEMON', 'Pokemon Unite'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='player_profile'
    )
    ign = models.CharField(
        max_length=50,
        verbose_name='In-Game Name',
        help_text='Your display name in the game'
    )
    game_id = models.CharField(
        max_length=100,
        verbose_name='Game ID / UID',
        help_text='Your unique game ID or UID'
    )
    primary_game = models.CharField(
        max_length=20,
        choices=GAME_CHOICES,
        default='BGMI'
    )
    secondary_game = models.CharField(
        max_length=20,
        choices=GAME_CHOICES,
        blank=True,
        null=True
    )
    bio = models.TextField(max_length=500, blank=True)
    discord_id = models.CharField(max_length=100, blank=True)
    instagram_handle = models.CharField(max_length=100, blank=True)

    # Statistics
    total_kills = models.IntegerField(default=0)
    total_wins = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    tournament_wins = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Rank
    rank_points = models.IntegerField(default=0)
    tier = models.CharField(max_length=20, default='Recruit', choices=[
        ('Recruit', '🎖 Recruit'),
        ('Bronze', '🥉 Bronze'),
        ('Silver', '🥈 Silver'),
        ('Gold', '🥇 Gold'),
        ('Platinum', '💎 Platinum'),
        ('Diamond', '💠 Diamond'),
        ('Master', '👑 Master'),
        ('Legend', '🏆 Legend'),
    ])

    is_available = models.BooleanField(default=True, help_text='Available for team recruitment')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'players'
        ordering = ['-rank_points']
        verbose_name = 'Player Profile'
        verbose_name_plural = 'Player Profiles'

    def __str__(self):
        return f"{self.ign} ({self.user.email})"

    @property
    def kd_ratio(self):
        if self.total_matches > 0:
            return round(self.total_kills / self.total_matches, 2)
        return 0.00

    @property
    def win_rate(self):
        if self.total_matches > 0:
            return round((self.total_wins / self.total_matches) * 100, 1)
        return 0.0

    def update_tier(self):
        """Automatically update tier based on rank points."""
        tiers = [
            (0, 'Recruit'), (100, 'Bronze'), (300, 'Silver'),
            (600, 'Gold'), (1000, 'Platinum'), (1500, 'Diamond'),
            (2200, 'Master'), (3000, 'Legend')
        ]
        for threshold, tier_name in reversed(tiers):
            if self.rank_points >= threshold:
                self.tier = tier_name
                break
        self.save(update_fields=['tier'])
