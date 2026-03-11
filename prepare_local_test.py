import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_project.settings')
django.setup()

from subscriptions.models import Profile

# Create or Update User Profile locally
telegram_id = 6616646849
profile, created = Profile.objects.get_or_create(
    telegram_id=telegram_id,
    defaults={
        'username': 'Admin_Local',
        'is_active_subscriber': True,
        'has_used_trial': True
    }
)

if not created:
    profile.is_active_subscriber = True
    profile.save()

print(f"Profile for {telegram_id} is ready locally.")
