import os
import django
import asyncio
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_project.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from alerts.models import TradeAlert
from strategy_engine import broadcast_executive_signal

async def run_demo():
    print("Initializing Slancio Executive Demo...")
    
    # Create a High-Quality Mock Signal
    demo_alert = TradeAlert.objects.create(
        instrument="NIFTY 50",
        side="CALL",
        entry_price=22150.00,
        stoploss=22080.00,
        target1=22230.00,
        target2=22300.00,
        target3=22400.00,
        contract="MAR 22150 CE",
        expiry="28-MAR-2024",
        accuracy="96%",
        premium_decay="Very Low",
        status="Active",
        is_sent=True,
        sent_at=timezone.now(),
        gamma_velocity="High (0.045)",
        oi_momentum_score="Bullish (+12%)",
        imi_score=68.5
    )
    
    # Override instrument for chart fetching (use Nifty Index ticker)
    demo_alert.instrument = "^NSEI" 
    
    print(f"Broadcasting Executive Signal for {demo_alert.instrument}...")
    await broadcast_executive_signal(demo_alert)
    print("Demo Signal Sent Successfully!")

if __name__ == "__main__":
    asyncio.run(run_demo())
