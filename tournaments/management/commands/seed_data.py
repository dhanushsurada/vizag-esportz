"""
Management command: seed_data
Seeds the database with sample tournaments, players, and leaderboard data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
import datetime


class Command(BaseCommand):
    help = 'Seed database with sample data for Vizag Esportz'

    def handle(self, *args, **kwargs):
        self.stdout.write('🎮 Seeding Vizag Esportz database...')

        # Import models
        from accounts.models import NSRITUser
        from players.models import Player
        from tournaments.models import Tournament

        # ── CREATE SAMPLE TOURNAMENTS ──
        tournaments_data = [
            {
                'title': 'Vizag BGMI Championship Season 1',
                'game': 'BGMI',
                'mode': 'SQUAD',
                'entry_fee': 100,
                'max_players': 64,
                'prize_pool': 5000,
                'first_prize': 3000,
                'second_prize': 1500,
                'third_prize': 500,
                'description': 'The inaugural Vizag BGMI Championship. 64 squads battle for the grand prize of ₹5000!',
                'rules': '1. Fair play rules apply\n2. Team must have 4 members\n3. No hacks or mods\n4. Admin decision is final',
                'status': 'REGISTRATION_OPEN',
                'is_featured': True,
                'days_from_now': 7,
                'deadline_days': 5,
            },
            {
                'title': 'Valorant 5v5 Invitational',
                'game': 'VALORANT',
                'mode': 'TEAM5',
                'entry_fee': 150,
                'max_players': 32,
                'prize_pool': 8000,
                'first_prize': 5000,
                'second_prize': 2000,
                'third_prize': 1000,
                'description': 'Visakhapatnam\'s premier Valorant tournament. 5v5 team battle with ₹8000 prize pool!',
                'rules': '1. Standard Valorant tournament rules\n2. No smurfing\n3. 5 players per team minimum',
                'status': 'REGISTRATION_OPEN',
                'is_featured': True,
                'days_from_now': 14,
                'deadline_days': 10,
            },
            {
                'title': 'COD Mobile Solo Showdown',
                'game': 'COD',
                'mode': 'SOLO',
                'entry_fee': 50,
                'max_players': 100,
                'prize_pool': 2000,
                'first_prize': 1200,
                'second_prize': 500,
                'third_prize': 300,
                'description': 'Solo battle royale showdown! Top 100 players fight for glory.',
                'rules': '1. Solo players only\n2. Battle Royale mode\n3. Top scorer wins',
                'status': 'UPCOMING',
                'is_featured': False,
                'days_from_now': 21,
                'deadline_days': 18,
            },
            {
                'title': 'Free Fire Campus Cup',
                'game': 'FREE_FIRE',
                'mode': 'SQUAD',
                'entry_fee': 0,
                'max_players': 40,
                'prize_pool': 1000,
                'first_prize': 600,
                'second_prize': 250,
                'third_prize': 150,
                'description': 'FREE entry Free Fire tournament! Open to all Vizag players.',
                'rules': '1. Free Fire Squad mode\n2. Maximum 4 members\n3. Registration required',
                'status': 'REGISTRATION_OPEN',
                'is_featured': True,
                'days_from_now': 5,
                'deadline_days': 3,
            },
            {
                'title': 'CS2 Tactical Warfare',
                'game': 'CS2',
                'mode': 'TEAM5',
                'entry_fee': 200,
                'max_players': 16,
                'prize_pool': 10000,
                'first_prize': 6000,
                'second_prize': 2500,
                'third_prize': 1500,
                'description': 'Elite Counter-Strike 2 tournament for the best 5v5 teams in Vizag.',
                'rules': '1. CS2 competitive ruleset\n2. Anti-cheat mandatory\n3. 5 players per team',
                'status': 'UPCOMING',
                'is_featured': False,
                'days_from_now': 30,
                'deadline_days': 25,
            },
        ]

        created_count = 0
        for data in tournaments_data:
            slug = slugify(data['title'])
            if not Tournament.objects.filter(slug=slug).exists():
                Tournament.objects.create(
                    title=data['title'],
                    slug=slug,
                    game=data['game'],
                    mode=data['mode'],
                    entry_fee=data['entry_fee'],
                    max_players=data['max_players'],
                    prize_pool=data['prize_pool'],
                    first_prize=data['first_prize'],
                    second_prize=data['second_prize'],
                    third_prize=data['third_prize'],
                    description=data['description'],
                    rules=data['rules'],
                    status=data['status'],
                    is_featured=data['is_featured'],
                    is_active=True,
                    start_date=timezone.now().date() + datetime.timedelta(days=data['days_from_now']),
                    end_date=timezone.now().date() + datetime.timedelta(days=data['days_from_now'] + 2),
                    registration_deadline=timezone.now() + datetime.timedelta(days=data['deadline_days']),
                )
                created_count += 1
                self.stdout.write(f'  ✅ Created tournament: {data["title"]}')

        self.stdout.write(f'\n🏆 Created {created_count} tournaments')

        # ── CREATE SUPERUSER ──
        if not NSRITUser.objects.filter(email='admin@vizagesportz.com').exists():
            admin = NSRITUser.objects.create_superuser(
                email='admin@vizagesportz.com',
                password='vizag@admin2026',
                first_name='Arena',
                last_name='Admin',
            )
            self.stdout.write(f'\n👑 Superuser created: see seeded admin credentials above')
        else:
            self.stdout.write('\n👑 Superuser already exists')

        self.stdout.write('\n🎮 Database seeded successfully!')
        self.stdout.write('=' * 50)
        self.stdout.write('🌐 Start server: python manage.py runserver')
        self.stdout.write('🔑 Admin panel: http://127.0.0.1:8000/admin/')
        self.stdout.write('👤 Admin: see seeded admin credentials above')
        self.stdout.write('=' * 50)
