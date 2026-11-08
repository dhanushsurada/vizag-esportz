from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            # 1. Main Official Super Admin
            if not User.objects.filter(email="admin@vizagesportz.com").exists():
                admin_main = User.objects.create_superuser(
                    email="admin@vizagesportz.com",
                    password="Admin@1234",
                    first_name="Arena",
                    last_name="Admin"
                )
            else:
                admin_main = User.objects.get(email="admin@vizagesportz.com")
                admin_main.is_staff = True
                admin_main.is_superuser = True
                admin_main.is_active = True
                admin_main.email_verified = True
                admin_main.save()

            # 2. Secondary Admin
            if not User.objects.filter(email="admin@gmail.com").exists():
                User.objects.create_superuser(
                    email="admin@gmail.com",
                    password="admin123",
                    first_name="System",
                    last_name="Admin"
                )
            else:
                admin_sec = User.objects.get(email="admin@gmail.com")
                admin_sec.is_staff = True
                admin_sec.is_superuser = True
                admin_sec.is_active = True
                admin_sec.email_verified = True
                admin_sec.save()
        except Exception:
            pass