from django.contrib import admin
from .models import Transaction, Profile, SubscriptionPlan, SupportTicket
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
# from telegram import Bot - Moved to local imports to prevent ModuleNotFoundError
import asyncio

@admin.action(description='Approve selected transactions and activate subscriptions')
def approve_transactions(modeladmin, request, queryset):
    from telegram import Bot
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    for transaction in queryset:
        if transaction.status == 'pending':
            transaction.status = 'success'
            transaction.save()
            
            profile = transaction.profile
            profile.is_active_subscriber = True
            
            days = transaction.plan.duration_days
            if profile.subscription_end_date and profile.subscription_end_date > timezone.now():
                profile.subscription_end_date += timedelta(days=days)
            else:
                profile.subscription_end_date = timezone.now() + timedelta(days=days)
            profile.save()
            
            # Notify user
            message = (
                f"✅ *Subscription Activated!* ✅\n\n"
                f"Plan: {transaction.plan.name}\n"
                f"Expires on: {profile.subscription_end_date.strftime('%d-%b-%Y')}\n\n"
                f"You will now receive all premium signals automatically. Happy Trading! 🚀"
            )
            try:
                asyncio.run(bot.send_message(chat_id=profile.telegram_id, text=message, parse_mode='Markdown'))
            except Exception as e:
                print(f"Error notifying {profile.telegram_id}: {e}")

@admin.action(description='Send Reply to Selected Tickets')
def send_support_reply(modeladmin, request, queryset):
    from telegram import Bot
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    for ticket in queryset:
        if ticket.admin_reply:
            message = (
                f"✉️ *Support Reply* ✉️\n\n"
                f"🔖 *Your Query:* {ticket.get_query_type_display()}\n"
                f"📝 *Message:* {ticket.message}\n\n"
                f"✅ *Admin Response:* {ticket.admin_reply}\n\n"
                f"🌟 *Slancio Algo Trader Support*"
            )
            try:
                asyncio.run(bot.send_message(chat_id=ticket.user.telegram_id, text=message, parse_mode='Markdown'))
                ticket.status = 'RESOLVED'
                ticket.replied_at = timezone.now()
                ticket.save()
            except Exception as e:
                print(f"Failed to reply to {ticket.user.telegram_id}: {e}")

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'plan', 'amount', 'status', 'created_at')
    list_filter = ('status', 'plan')
    actions = [approve_transactions]
    readonly_fields = ('screenshot_display',)

    def screenshot_display(self, obj):
        from django.utils.html import format_html
        if obj.screenshot:
            return format_html('<img src="{}" width="300" />', obj.screenshot.url)
        return "No screenshot uploaded"
    
    screenshot_display.short_description = "Payment Proof"

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'query_type', 'status', 'created_at')
    list_filter = ('status', 'query_type')
    actions = [send_support_reply]
    readonly_fields = ('created_at', 'replied_at')
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'query_type', 'message')
        }),
        ('Response', {
            'fields': ('admin_reply', 'status', 'replied_at')
        }),
    )

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_in_paise', 'duration_days')
