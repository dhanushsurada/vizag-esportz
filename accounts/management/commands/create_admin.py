import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Create or update main super admin"

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default=None)
        parser.add_argument('--password', type=str, default=None)

    def handle(self, *args, **kwargs):
        email = (kwargs.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL') or 'admin@vizagesportz.com').lower().strip()
        password = kwargs.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD') or 'Admin@1234'

        user, created = User.objects.get_or_create(email=email)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.email_verified = True
        if not user.first_name:
            user.first_name = 'Arena'
            user.last_name = 'Admin'
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'{"Created" if created else "Updated"} super admin: {email}'
        ))
