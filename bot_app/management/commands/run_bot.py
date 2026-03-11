from django.core.management.base import BaseCommand
from bot_app.bot_logic import run_bot

class Command(BaseCommand):
    help = 'Runs the Telegram Bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Enterprise Telegram Bot (Zero-Cost Mode)...'))
        run_bot()
