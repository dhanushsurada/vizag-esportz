from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import F
from players.models import Player


class Tournament(models.Model):

    GAME_CHOICES = [
        ('BGMI', 'BGMI'),
        ('VALORANT', 'Valorant'),
        ('COD', 'Call of Duty Mobile'),
        ('FREE_FIRE', 'Free Fire'),
        ('CS2', 'Counter-Strike 2'),
        ('FIFA', 'FIFA / EA FC'),
        ('CHESS', 'Chess Online'),
    ]

    MODE_CHOICES = [
        ('SOLO', 'Solo'),
        ('DUO', 'Duo'),
        ('SQUAD', 'Squad (4 players)'),
        ('TEAM5', 'Team (5 players)'),
    ]

    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('REGISTRATION_OPEN', 'Registration Open'),
        ('REGISTRATION_CLOSED', 'Registration Closed'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='SOLO')

    description = models.TextField()
    rules = models.TextField(blank=True)

    banner = models.ImageField(upload_to='tournament_banners/', blank=True, null=True)

    entry_fee = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    max_players = models.PositiveIntegerField(default=64, validators=[MinValueValidator(1)])

    registration_deadline = models.DateTimeField()

    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    match_time = models.TimeField(blank=True, null=True)

    prize_pool = models.PositiveIntegerField(default=0)
    first_prize = models.PositiveIntegerField(default=0)
    second_prize = models.PositiveIntegerField(default=0)
    third_prize = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='UPCOMING')

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tournaments'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tournaments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.game})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('tournaments:detail', kwargs={'slug': self.slug})

    @property
    def registered_count(self):
        return self.registrations.filter(status='CONFIRMED').count()

    @property
    def slots_remaining(self):
        return max(self.max_players - self.registered_count, 0)

    @property
    def fill_percentage(self):
        if self.max_players == 0:
            return 0
        return min(100, int((self.registered_count / self.max_players) * 100))

    @property
    def is_registration_open(self):
        return (
            self.status == 'REGISTRATION_OPEN'
            and self.registration_deadline > timezone.now()
            and self.slots_remaining > 0
            and self.is_active
        )

    def can_register(self):
        # kept for backward compatibility
        return self.is_registration_open


class Registration(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Payment Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('UPI', 'UPI'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='registrations')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='registrations')

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='UPI')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')

    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    notes = models.TextField(blank=True, default='')

    registered_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'registrations'
        ordering = ['registered_at']
        constraints = [
            models.UniqueConstraint(fields=['player', 'tournament'], name='unique_player_tournament')
        ]

    def __str__(self):
        return f"{self.player.ign} → {self.tournament.title}"

    def confirm(self, by_admin=False):
        with transaction.atomic():
            if by_admin:
                self.payment_status = 'SUCCESS'
            elif self.payment_status != 'SUCCESS' and self.tournament.entry_fee > 0:
                return False

            # Check status + deadline only — NOT slots_remaining,
            # because this registration IS the slot being filled
            t = self.tournament
            if not by_admin:
                if not (t.status == 'REGISTRATION_OPEN'
                        and t.registration_deadline > timezone.now()
                        and t.is_active):
                    return False

            self.status = 'CONFIRMED'
            self.confirmed_at = timezone.now()
            self.save()
            return True
