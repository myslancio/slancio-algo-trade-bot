from django.core.management.base import BaseCommand
from bot_app.bot_logic import run_bot
import traceback
import sys

class Command(BaseCommand):
    help = 'Starts the Slancio Executive Bot in long-polling mode'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Slancio Executive Bot (Polling Mode)...'))
        try:
            run_bot()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Bot crashed: {e}'))
            traceback.print_exc(file=sys.stderr)
