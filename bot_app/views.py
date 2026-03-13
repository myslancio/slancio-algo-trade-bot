import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update
from .bot_logic import get_application
import asyncio

# Global application instance
bot_app = get_application()
initialized = False

@csrf_exempt
async def telegram_webhook(request):
    global initialized
    if request.method == "POST":
        try:
            if not initialized:
                await bot_app.initialize()
                initialized = True
            
            payload = json.loads(request.body)
            update = Update.de_json(payload, bot_app.bot)
            await bot_app.process_update(update)
            return HttpResponse("OK")
        except Exception as e:
            print(f"Webhook Error: {e}")
            return HttpResponse("Error", status=500)
    return HttpResponse("Slancio Executive Webhook Active")
