from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Create main super admin"

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='admin@vizagesportz.com')
        parser.add_argument('--password', type=str, default='Admin@1234')

    def handle(self, *args, **kwargs):
        email = kwargs['email'].lower()
        user, created = User.objects.get_or_create(email=email)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.email_verified = True
        user.set_password(kwargs['password'])  # change later
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'{"Created" if created else "Updated"} super admin: {email}'
        ))
