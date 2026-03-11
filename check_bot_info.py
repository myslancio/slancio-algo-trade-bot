import asyncio
from telegram import Bot
from django.conf import settings
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_project.settings')
django.setup()

async def get_bot_info():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    me = await bot.get_me()
    print(f"BOT_USERNAME: @{me.username}")
    print(f"BOT_NAME: {me.first_name}")

if __name__ == "__main__":
    asyncio.run(get_bot_info())
