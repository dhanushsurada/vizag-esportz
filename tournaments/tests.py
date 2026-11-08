from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import NSRITUser
from players.models import Player
from tournaments.models import Tournament, Registration
from payments.models import Payment


class UserJourneyAndPaymentApprovalTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Admin / Moderator user
        self.admin_user = NSRITUser.objects.create_superuser(
            email='admin@vizagesportz.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User',
        )

        # Free tournament
        self.free_tournament = Tournament.objects.create(
            title='Vizag Free Fire Clash',
            slug='vizag-free-fire-clash',
            game='FREE_FIRE',
            mode='SOLO',
            entry_fee=0,
            prize_pool=5000,
            max_players=32,
            registration_deadline=timezone.now() + timedelta(days=5),
            start_date=timezone.now() + timedelta(days=7),
            status='REGISTRATION_OPEN',
            is_active=True,
            created_by=self.admin_user,
        )

        # Paid tournament
        self.paid_tournament = Tournament.objects.create(
            title='Vizag BGMI Pro Championship',
            slug='vizag-bgmi-pro-championship',
            game='BGMI',
            mode='SOLO',
            entry_fee=100,
            prize_pool=25000,
            max_players=32,
            registration_deadline=timezone.now() + timedelta(days=5),
            start_date=timezone.now() + timedelta(days=7),
            status='REGISTRATION_OPEN',
            is_active=True,
            created_by=self.admin_user,
        )

    def test_complete_user_journey_and_approval(self):
        # 1. Register new account
        register_url = reverse('accounts:register')
        reg_response = self.client.post(register_url, {
            'first_name': 'Player',
            'last_name': 'One',
            'email': 'player1@vizagesportz.com',
            'phone': '9876543210',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(reg_response.status_code, 302)
        user = NSRITUser.objects.get(email='player1@vizagesportz.com')
        self.assertIsNotNone(user)

        # 2. Login
        login_url = reverse('accounts:login')
        login_response = self.client.post(login_url, {
            'username': 'player1@vizagesportz.com',
            'password': 'StrongPassword123!',
        })
        self.assertEqual(login_response.status_code, 302)

        # 3. Create Player Profile
        profile_create_url = reverse('players:create_profile')
        profile_response = self.client.post(profile_create_url, {
            'ign': 'VizagSniper',
            'game_id': 'UID_100234',
            'primary_game': 'BGMI',
            'secondary_game': 'FREE_FIRE',
            'bio': 'Vizag competitive sniper',
            'is_available': True,
        })
        self.assertEqual(profile_response.status_code, 302)
        player = Player.objects.get(user=user)
        self.assertEqual(player.ign, 'VizagSniper')

        # 4. Register for FREE Tournament
        free_reg_url = reverse('tournaments:register', kwargs={'slug': self.free_tournament.slug})
        free_resp = self.client.post(free_reg_url)
        self.assertEqual(free_resp.status_code, 302)

        # Check free registration is instantly confirmed
        free_reg = Registration.objects.get(player=player, tournament=self.free_tournament)
        self.assertEqual(free_reg.status, 'CONFIRMED')
        self.assertEqual(free_reg.payment_status, 'SUCCESS')
        self.assertEqual(self.free_tournament.registered_count, 1)

        # 5. Register for PAID Tournament
        paid_reg_url = reverse('tournaments:register', kwargs={'slug': self.paid_tournament.slug})
        paid_resp = self.client.post(paid_reg_url)
        # Should redirect to payment initiation
        self.assertEqual(paid_resp.status_code, 302)
        self.assertIn(reverse('payments:initiate', kwargs={'slug': self.paid_tournament.slug}), paid_resp.url)

        # 6. Access payment page
        payment_page_url = reverse('payments:initiate', kwargs={'slug': self.paid_tournament.slug})
        payment_page_resp = self.client.get(payment_page_url)
        self.assertEqual(payment_page_resp.status_code, 200)
        self.assertContains(payment_page_resp, 'Pay via UPI')
        self.assertContains(payment_page_resp, 'upi-qr-img')
        self.assertContains(payment_page_resp, 'transaction_id')
        self.assertContains(payment_page_resp, 'payment_screenshot')
        self.assertContains(payment_page_resp, 'Submit Payment Proof')

        # 7. Submit UPI Payment
        upi_submit_url = reverse('payments:upi_submit', kwargs={'slug': self.paid_tournament.slug})
        upi_resp = self.client.post(upi_submit_url, {
            'transaction_id': 'UPI123456789012',
            'upi_app': 'PhonePe',
        })
        self.assertEqual(upi_resp.status_code, 302)

        # Check registration and payment are created with PENDING status
        paid_reg = Registration.objects.get(player=player, tournament=self.paid_tournament)
        self.assertEqual(paid_reg.status, 'PENDING')
        self.assertEqual(paid_reg.payment_status, 'PENDING')
        self.assertEqual(paid_reg.transaction_id, 'UPI123456789012')

        payment_record = Payment.objects.get(player=player, tournament=self.paid_tournament)
        self.assertEqual(payment_record.status, 'PENDING')
        self.assertEqual(payment_record.amount, 10000)  # 100 INR = 10000 paise

        # Check tournament detail page displays pending verification alert
        detail_resp = self.client.get(reverse('tournaments:detail', kwargs={'slug': self.paid_tournament.slug}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, 'Verification Pending')
        self.assertContains(detail_resp, 'UPI123456789012')

        # Check "My Registrations" page
        my_regs_resp = self.client.get(reverse('tournaments:my_registrations'))
        self.assertEqual(my_regs_resp.status_code, 200)
        self.assertContains(my_regs_resp, 'Pay Now')

        # 8. Moderator Logs In and Approves the Registration
        self.client.login(email='admin@vizagesportz.com', password='AdminPassword123!')

        # Moderator checks registrations page
        mod_regs_url = reverse('moderator:registrations')
        mod_regs_resp = self.client.get(mod_regs_url)
        self.assertEqual(mod_regs_resp.status_code, 200)
        self.assertContains(mod_regs_resp, 'UPI123456789012')
        self.assertContains(mod_regs_resp, 'VizagSniper')

        # Moderator approves registration
        approve_url = reverse('moderator:approve_registration', kwargs={'reg_id': paid_reg.id})
        approve_resp = self.client.get(approve_url)
        self.assertEqual(approve_resp.status_code, 302)

        # Refresh from database and verify approval
        paid_reg.refresh_from_db()
        payment_record.refresh_from_db()
        self.assertEqual(paid_reg.status, 'CONFIRMED')
        self.assertEqual(paid_reg.payment_status, 'SUCCESS')
        self.assertEqual(payment_record.status, 'SUCCESS')

        # Verify tournament registered count updated
        self.assertEqual(self.paid_tournament.registered_count, 1)

        # Switch back to player1 to view confirmed registration status
        self.client.force_login(user)
        detail_resp_confirmed = self.client.get(reverse('tournaments:detail', kwargs={'slug': self.paid_tournament.slug}))
        self.assertContains(detail_resp_confirmed, 'Registered & Confirmed')

        # 9. Verify duplicate registration prevention
        dup_resp = self.client.post(paid_reg_url)
        self.assertEqual(dup_resp.status_code, 302)
        # Should stay confirmed, count remains 1
        self.assertEqual(Registration.objects.filter(player=player, tournament=self.paid_tournament).count(), 1)

    def test_rejection_and_detail_page_staff_actions(self):
        # Create user and player
        user = NSRITUser.objects.create_user(
            email='player2@vizagesportz.com',
            password='Password123!',
            first_name='Player',
            last_name='Two',
        )
        player = Player.objects.create(
            user=user,
            ign='VizagNinja',
            game_id='UID_2001',
            primary_game='BGMI',
        )

        # Register for paid tournament via UPI
        self.client.force_login(user)
        self.client.post(reverse('payments:upi_submit', kwargs={'slug': self.paid_tournament.slug}), {
            'transaction_id': 'FAKE_TXN_000',
            'upi_app': 'GPay',
        })
        reg = Registration.objects.get(player=player, tournament=self.paid_tournament)
        self.assertEqual(reg.status, 'PENDING')

        # Staff rejects from tournament detail page
        self.client.force_login(self.admin_user)
        reject_url = reverse('tournaments:reject_registration', kwargs={'reg_id': reg.id})
        reject_resp = self.client.post(reject_url, HTTP_REFERER=reverse('tournaments:detail', kwargs={'slug': self.paid_tournament.slug}))
        self.assertEqual(reject_resp.status_code, 302)

        reg.refresh_from_db()
        self.assertEqual(reg.status, 'CANCELLED')

        # Staff approves from tournament detail page
        approve_url = reverse('tournaments:approve_registration', kwargs={'reg_id': reg.id})
        approve_resp = self.client.post(approve_url, HTTP_REFERER=reverse('tournaments:detail', kwargs={'slug': self.paid_tournament.slug}))
        self.assertEqual(approve_resp.status_code, 302)

        reg.refresh_from_db()
        self.assertEqual(reg.status, 'CONFIRMED')
        self.assertEqual(reg.payment_status, 'SUCCESS')

    def test_bracket_generation_post(self):
        # Create two players confirmed in free tournament
        u1 = NSRITUser.objects.create_user(email='b1@vizagesportz.com', password='Password123!', first_name='A', last_name='1')
        p1 = Player.objects.create(user=u1, ign='Alpha', game_id='G1')
        Registration.objects.create(player=p1, tournament=self.free_tournament, status='CONFIRMED', payment_status='SUCCESS')

        u2 = NSRITUser.objects.create_user(email='b2@vizagesportz.com', password='Password123!', first_name='B', last_name='2')
        p2 = Player.objects.create(user=u2, ign='Bravo', game_id='G2')
        Registration.objects.create(player=p2, tournament=self.free_tournament, status='CONFIRMED', payment_status='SUCCESS')

        self.client.force_login(self.admin_user)
        gen_url = reverse('matches:generate_bracket', kwargs={'slug': self.free_tournament.slug})
        resp = self.client.post(gen_url)
        self.assertEqual(resp.status_code, 302)

        from matches.models import Match
        matches = Match.objects.filter(tournament=self.free_tournament)
        self.assertTrue(matches.exists())
