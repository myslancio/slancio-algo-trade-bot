from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import TradeAlert
from subscriptions.models import Profile
from django.utils import timezone
import json
import asyncio
from telegram import Bot
import hmac
import hashlib

async def send_telegram_broadcast(message):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    active_profiles = Profile.objects.filter(is_active_subscriber=True)
    
    for profile in active_profiles:
        try:
            await bot.send_message(
                chat_id=profile.telegram_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to send to {profile.telegram_id}: {e}")

@csrf_exempt
def signal_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    # Basic security check (Token based)
    # In a real app, use a secret token from settings
    received_token = request.headers.get('Authorization')
    expected_token = getattr(settings, 'STRATEGY_SECRET_TOKEN', 'SECRET_SIGNAL_TOKEN')
    
    if received_token != expected_token:
        return JsonResponse({"status": "unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        
        # Create TradeAlert object
        alert = TradeAlert.objects.create(
            instrument=data.get('instrument'),
            side=data.get('side'),
            entry_price=data.get('entry_price'),
            stoploss=data.get('stoploss'),
            target1=data.get('target1'),
            target2=data.get('target2'),
            target3=data.get('target3'),
            additional_notes=data.get('notes', 'Automated Signal')
        )

        # Build message
        message = (
            f"🚀 *AUTOMATED TRADE ALERT* 🚀\n\n"
            f"📊 *Instrument:* {alert.get_instrument_display()}\n"
            f"⚡ *Type:* {alert.side}\n\n"
            f"✅ *Entry:* {alert.entry_price}\n"
            f"🛑 *Stoploss:* {alert.stoploss}\n\n"
            f"🎯 *Target 1:* {alert.target1}\n"
            f"🎯 *Target 2:* {alert.target2}\n"
            f"🎯 *Target 3:* {alert.target3}\n\n"
        )
        
        if alert.additional_notes:
            message += f"📝 *Notes:* {alert.additional_notes}\n\n"
        
        message += "⚠️ _Trade responsibly. Automated signal._"

        # Broadcast asynchronously
        asyncio.run(send_telegram_broadcast(message))
        
        alert.is_sent = True
        alert.sent_at = timezone.now()
        alert.save()

        return JsonResponse({"status": "success", "alert_id": alert.id})

    except Exception as e:
        from .models import ArchitectureError
        import traceback
        ArchitectureError.objects.create(
            error_message=str(e),
            traceback=traceback.format_exc(),
            component='Signal Webhook'
        )
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
