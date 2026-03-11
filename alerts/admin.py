from django.contrib import admin
from .models import TradeAlert
from subscriptions.models import Profile
from django.conf import settings
import asyncio
from telegram import Bot
from django.utils import timezone

@admin.action(description='Broadcast structured signal to all active subscribers')
def broadcast_structured_signal(modeladmin, request, queryset):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    active_profiles = Profile.objects.filter(is_active_subscriber=True)
    
    for alert in queryset:
        if not alert.is_sent:
            # Build professional message template
            message = (
                f"🛡️ *{alert.instrument}* {alert.side} SIGNAL 🛡️\n\n"
                f"📝 *Contract:* {alert.contract}\n"
                f"📅 *Expiry:* {alert.expiry}\n\n"
                f"💰 *Buy Price:* {alert.entry_price}\n"
                f"🛑 *Stoploss:* {alert.stoploss}\n\n"
                f"🎯 *Target 1:* {alert.target1}\n"
                f"🎯 *Target 2:* {alert.target2}\n"
                f"🎯 *Target 3:* {alert.target3}\n\n"
                f"📉 *Premium Decay:* {alert.premium_decay}\n"
                f"✅ *Trade Accuracy:* {alert.accuracy}\n\n"
                f"🚀 *Gamma Velocity:* {alert.gamma_velocity}\n"
                f"📊 *OI Momentum:* {alert.oi_momentum_score}\n"
                f"📈 *Intraday Momentum Index:* {alert.imi_score}\n\n"
                f"🔄 *Status:* {alert.status}\n"
                f"💎 *Premium LTP:* {alert.premium_ltp}\n"
                f"📍 *Spot Price:* {alert.spot_price}\n\n"
                f"🌟 *Powered By Slancio Algo Trader*"
            )

            for profile in active_profiles:
                try:
                    asyncio.run(bot.send_message(
                        chat_id=profile.telegram_id,
                        text=message,
                        parse_mode='Markdown',
                        protect_content=True
                    ))
                except Exception as e:
                    print(f"Failed to send to {profile.telegram_id}: {e}")
            
            alert.is_sent = True
            alert.sent_at = timezone.now()
            alert.save()

@admin.register(TradeAlert)
class TradeAlertAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'side', 'entry_price', 'status', 'is_sent')
    list_filter = ('instrument', 'side', 'status', 'is_sent')
    actions = [broadcast_structured_signal]
    
    fieldsets = (
        ('Signal Core', {
            'fields': ('instrument', 'side', 'entry_price', 'stoploss', 'status')
        }),
        ('Contract Details', {
            'fields': ('contract', 'expiry', 'premium_ltp', 'spot_price')
        }),
        ('Advanced Metrics', {
            'fields': ('gamma_velocity', 'oi_momentum_score', 'imi_score')
        }),
        ('Targets', {
            'fields': ('target1', 'target2', 'target3')
        }),
        ('Performance', {
            'fields': ('accuracy', 'premium_decay')
        }),
        ('System Info', {
            'fields': ('is_sent', 'sent_at', 'additional_notes')
        }),
    )
    readonly_fields = ('sent_at',)


