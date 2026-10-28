from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0002_registration_payment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
