from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from django.conf import settings
from subscriptions.models import Profile, SubscriptionPlan, Transaction, SupportTicket, SecurityLog, HealthMonitor, Feedback, GlobalConfig
from alerts.models import TradeAlert
import os
import traceback
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg

# --- EXECUTIVE UI HELPERS ---
def format_card(title, content):
    """Generates a professional terminal-style card."""
    border = "────────────────────────────────"
    return f"🛡️ *{title}*\n{border}\n{content}\n{border}\n🌟 *Slancio Algo Trader*"

def is_admin(user_id):
    admin_ids = getattr(settings, 'ADMIN_TELEGRAM_IDS', [])
    return user_id in admin_ids

def log_security_breach(user, command):
    SecurityLog.objects.create(user_id=user.id, username=user.username, command_attempted=command)

async def update_heartbeat():
    HealthMonitor.objects.update_or_create(component='Bot', defaults={'status': 'Healthy'})

async def broadcast_error(bot, error_msg, user=None):
    admin_ids = getattr(settings, 'ADMIN_TELEGRAM_IDS', [])
    report = format_card("SYSTEM ALERT", f"🚨 *CRITICAL ERROR:*\n\n{error_msg}")
    for aid in admin_ids:
        try: await bot.send_message(chat_id=aid, text=report, parse_mode='Markdown')
        except: pass

# --- USER HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        user = update.effective_user
        profile, created = Profile.objects.get_or_create(telegram_id=user.id, defaults={'username': user.username})
        
        # Handle Referrals (Deep Linking)
        if created and context.args:
            try:
                referrer_id = int(context.args[0])
                referrer = Profile.objects.get(telegram_id=referrer_id)
                profile.referred_by = referrer
                
                # Grant 3-Day Trial
                if not profile.has_used_trial:
                    profile.has_used_trial = True
                    profile.is_active_subscriber = True
                    profile.trial_expiry = timezone.now() + timedelta(days=3)
                    profile.subscription_end_date = profile.trial_expiry
                    profile.save()
                    await update.message.reply_text(format_card("WELCOME GIFT", "🎁 You've received a *3-Day Premium Trial* via referral!"), parse_mode='Markdown')
            except: pass

        content = (
            "🏦 *Trading Console Active*\n\n"
            "1. /subscribe - Manage Membership\n"
            "2. /pnl - View Performance\n"
            "3. /support - Tech Assistance\n"
            "4. /invite - Get Free Trial for Friends\n"
            "5. /feedback - Share your experience\n"
        )
        if is_admin(user.id): content += "\n🛡️ /admin - Mobile Terminal"
        
        await update.message.reply_text(format_card("SLANCIO ALGOS", content), parse_mode='Markdown', protect_content=True)
    except Exception as e:
        await broadcast_error(context.bot, traceback.format_exc(), update.effective_user)

async def pnl_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executive Performance Dashboard."""
    try:
        await update_heartbeat()
        signals = TradeAlert.objects.order_by('-sent_at')[:10]
        avg_acc = TradeAlert.objects.aggregate(Avg('accuracy'))['accuracy__avg'] or 0
        
        table = "```\nDATE       INST    SIDE   ACC\n"
        for s in signals:
            date_str = s.sent_at.strftime('%d/%m') if s.sent_at else "N/A"
            table += f"{date_str:<10} {s.instrument[:5]:<7} {s.side[:4]:<6} {s.accuracy}\n"
        table += "```"
        
        content = (
            f"📈 *TOTAL ACCURACY:* {avg_acc:.1f}%\n"
            f"📊 *LAST 10 SIGNALS:*\n{table}"
        )
        await update.message.reply_text(format_card("PERFORMANCE HUB", content), parse_mode='Markdown', protect_content=True)
    except Exception as e:
        await broadcast_error(context.bot, traceback.format_exc())

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates a deep-link invite for friends."""
    user = update.effective_user
    bot_username = (await context.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start={user.id}"
    
    content = (
        "🎁 *SHARE THE WEALTH*\n\n"
        "Invite your friends using your unique link. They will get a *3-Day FREE Trial* instantly!\n\n"
        f"🔗 *Invite Link:* `{invite_link}`"
    )
    await update.message.reply_text(format_card("VIRAL GROWTH", content), parse_mode='Markdown', protect_content=True)

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Requests feedback from user."""
    context.user_data['awaiting_feedback'] = True
    await update.message.reply_text(format_card("USER FEEDBACK", "We value your input! Please type your feedback or suggestions below:"), parse_mode='Markdown', protect_content=True)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        plans = SubscriptionPlan.objects.all()
        if not plans.exists():
            SubscriptionPlan.objects.get_or_create(name="7 Days Pro", price_in_paise=49900, duration_days=7)
            SubscriptionPlan.objects.get_or_create(name="1 Month Pro", price_in_paise=149900, duration_days=30)
            SubscriptionPlan.objects.get_or_create(name="2 Months Pro", price_in_paise=249900, duration_days=60)
            plans = SubscriptionPlan.objects.all()
        
        keyboard = [[InlineKeyboardButton(f"{p.name} - ₹{p.price_in_paise/100}", callback_data=f"buy_{p.id}")] for p in plans]
        await update.message.reply_text(format_card("MEMBERSHIP", "Select a plan to access premium signals:"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown', protect_content=True)
    except Exception as e:
        await broadcast_error(context.bot, traceback.format_exc())

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(l, callback_data=f"sup_{k}")] for k, l in SupportTicket.QUERY_CHOICES]
    await update.message.reply_text(format_card("SUPPORT HUB", "How can we assist you today?"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown', protect_content=True)

async def admin_console(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        log_security_breach(update.effective_user, "/admin")
        return await update.message.reply_text("❌ Access Denied.")
    
    kb = [
        [InlineKeyboardButton("💰 Pending Pay", callback_data="adm_pending_pay")],
        [InlineKeyboardButton("🎫 Open Tickets", callback_data="adm_tickets")],
        [InlineKeyboardButton("🔋 Health Status", callback_data="adm_health")],
        [InlineKeyboardButton("⏱️ Set Timeframe", callback_data="adm_timeframe")],
    ]
    await update.message.reply_text(format_card("ADMIN TERMINAL", "Mobile management active."), reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', protect_content=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        query = update.callback_query
        await query.answer()
        data, user_id = query.data, update.effective_user.id
        
        if data.startswith('buy_'):
            plan = SubscriptionPlan.objects.get(id=data.split('_')[1])
            vpa = getattr(settings, 'UPI_MERCHANT_VPA', 'slancio@jio')
            upi = f"upi://pay?pa={vpa}&pn=Slancio&am={plan.price_in_paise/100}&cu=INR"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⚡ PAY via UPI", url=upi)]])
            
            content = f"💠 *Plan:* {plan.name}\n💰 *Price:* ₹{plan.price_in_paise/100}\n🏦 *UPI ID:* `{vpa}`\n\n1️⃣ Click the button below to pay via any UPI app.\n2️⃣ **Take a screenshot** of the successful payment.\n3️⃣ **Upload the screenshot** here as proof.\n\n*Admin will verify and activate your signals within minutes!*"
            await query.edit_message_text(format_card("CHECKOUT", content), reply_markup=kb, parse_mode='Markdown')
            context.user_data['pending_plan_id'] = plan.id

        elif data == 'adm_health':
            if not is_admin(user_id): return
            ms = HealthMonitor.objects.all()
            content = ""
            for m in ms:
                content += f"{'🟢' if m.status == 'Healthy' else '🔴'} *{m.component}:* {m.status}\n🕒 last: {m.last_heartbeat.strftime('%H:%M:%S')}\n"
            await query.edit_message_text(format_card("SYSTEM HEALTH", content), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="adm_health")]]))

        elif data == 'adm_timeframe':
            if not is_admin(user_id): return
            current_tf = GlobalConfig.get_value('active_timeframe', '15m')
            tfs = ['1m', '5m', '15m', '30m', '1h']
            kb = [[InlineKeyboardButton(f"{'✅ ' if tf == current_tf else ''}{tf}", callback_data=f"set_tf_{tf}") for tf in tfs[i:i+3]] for i in range(0, len(tfs), 3)]
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="adm_back")])
            await query.edit_message_text(format_card("TIMEFRAME CONTROL", f"Active Interval: *{current_tf}*\n\nSelect a new timeframe for the strategy engine:"), reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

        elif data.startswith('set_tf_'):
            if not is_admin(user_id): return
            new_tf = data.split('_')[2]
            GlobalConfig.objects.update_or_create(key='active_timeframe', defaults={'value': new_tf})
            await query.edit_message_text(format_card("TIMEFRAME UPDATED", f"✅ Strategy engine now scanning on *{new_tf}* timeframe."), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="adm_back")]]))

        elif data == 'adm_back':
            await admin_console(update, context)

        elif data.startswith('sup_'):
            context.user_data['support_type'] = data.split('_')[1]
            await query.edit_message_text(format_card("SUPPORT", "Please type your detailed query below:"))

        elif data == 'adm_pending_pay':
            txs = Transaction.objects.filter(status='pending')
            if not txs.exists(): return await query.edit_message_text("No pending pay.")
            for tx in txs:
                kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{tx.id}")]]
                caption = f"👤 {tx.profile.telegram_id}\n📦 {tx.plan.name}\n💰 ₹{tx.amount/100}"
                if tx.screenshot: await query.message.reply_photo(photo=tx.screenshot, caption=caption, reply_markup=InlineKeyboardMarkup(kb), protect_content=True)
                else: await query.message.reply_text(text=caption, reply_markup=InlineKeyboardMarkup(kb), protect_content=True)

        elif data.startswith('approve_'):
            tx = Transaction.objects.get(id=data.split('_')[1])
            tx.status, p = 'success', tx.profile
            tx.save()
            p.is_active_subscriber = True
            p.subscription_end_date = (p.subscription_end_date or timezone.now()) + timedelta(days=tx.plan.duration_days)
            p.save()
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ APPROVED")
            await context.bot.send_message(chat_id=p.telegram_id, text=format_card("ACTIVE", f"Your subscription is active until {p.subscription_end_date.strftime('%d-%b-%Y')}!"), parse_mode='Markdown', protect_content=True)

    except Exception as e: await broadcast_error(context.bot, traceback.format_exc())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        user_id = update.effective_user.id
        
        # Feedback Handling
        if context.user_data.get('awaiting_feedback'):
            profile = Profile.objects.get(telegram_id=user_id)
            Feedback.objects.create(user=profile, message=update.message.text)
            del context.user_data['awaiting_feedback']
            await update.message.reply_text(format_card("THANK YOU", "Your feedback has been recorded. We appreciate your support!"), parse_mode='Markdown', protect_content=True)
            return

        # Photo processing
        if update.message.photo:
            p_id = context.user_data.get('pending_plan_id')
            if not p_id: return await update.message.reply_text("Process failed. Use /subscribe first.")
            profile = Profile.objects.get(telegram_id=user_id)
            plan = SubscriptionPlan.objects.get(id=p_id)
            tx = Transaction.objects.create(profile=profile, plan=plan, amount=plan.price_in_paise, status='pending')
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            tx.screenshot.save(f"proof_{tx.id}.jpg", ContentFile(await file.download_as_bytearray()))
            tx.save()
            await update.message.reply_text(format_card("STATUS", "Receipt received! Admin will verify soon."), parse_mode='Markdown', protect_content=True)
            del context.user_data['pending_plan_id']; return

        # Support type processing
        sup = context.user_data.get('support_type')
        if sup:
            profile = Profile.objects.get(telegram_id=user_id)
            SupportTicket.objects.create(user=profile, query_type=sup, message=update.message.text)
            await update.message.reply_text(format_card("STATUS", "Query sent! Admin will notify you."), parse_mode='Markdown', protect_content=True)
            del context.user_data['support_type']
        else:
            await update.message.reply_text("🤖 Unknown command. Use /start to see the menu.")

    except Exception as e: await broadcast_error(context.bot, traceback.format_exc())

def run_bot():
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start)); app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("pnl", pnl_report)); app.add_handler(CommandHandler("support", support))
    app.add_handler(CommandHandler("invite", invite)); app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("admin", admin_console)); app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & (~filters.COMMAND), handle_message))
    print("Growth-Hardened Bot starting..."); app.run_polling()
