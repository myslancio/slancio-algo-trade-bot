from django.core.management.base import BaseCommand
from strategy_engine import run_engine

class Command(BaseCommand):
    help = 'Runs the Slancio Strategy Engine to fetch live NSE data and alert subscribers'

    def handle(self, *args, **options):
        import asyncio
        self.stdout.write(self.style.SUCCESS('Starting Slancio Strategy Engine (Executive Mode)...'))
        asyncio.run(run_engine())
