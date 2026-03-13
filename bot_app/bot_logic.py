from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from django.conf import settings
from subscriptions.models import Profile, SubscriptionPlan, Transaction, SupportTicket, SecurityLog, HealthMonitor, Feedback, GlobalConfig
from alerts.models import TradeAlert
from core.ui import format_premium_card, escape_md, GOLD_SHIELD, BLUE_DIAMOND, SEPARATOR
import os
import traceback
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg

# Welcome Banner Path (for local reference, but bot uses actual file)
WELCOME_BANNER = os.path.join(settings.BASE_DIR, "assets", "welcome_banner.png")

def is_admin(user_id):
    admin_ids = getattr(settings, 'ADMIN_TELEGRAM_IDS', [])
    return user_id in admin_ids

def log_security_breach(user, command):
    SecurityLog.objects.create(user_id=user.id, username=user.username, command_attempted=command)

async def update_heartbeat():
    HealthMonitor.objects.update_or_create(component='Bot', defaults={'status': 'Healthy'})

async def broadcast_error(bot, error_msg, user=None):
    admin_ids = getattr(settings, 'ADMIN_TELEGRAM_IDS', [])
    report = format_premium_card("SYSTEM ALERT", f"🚨 *CRITICAL ERROR:*\n\n{escape_md(error_msg)}")
    for aid in admin_ids:
        try: await bot.send_message(chat_id=aid, text=report, parse_mode='MarkdownV2')
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
                    msg = escape_md("🎁 You've received a 3-Day Premium Trial via referral!")
                    await update.message.reply_text(format_premium_card("WELCOME GIFT", f"*{msg}*"), parse_mode='MarkdownV2')
            except: pass

        content = (
            f"{BLUE_DIAMOND} *Terminal:* `Active`\n"
            f"{BLUE_DIAMOND} *Security:* `Encrypted`\n\n"
            "Welcome to the **Slancio Executive Terminal**. Use the menu below or the navigation buttons to control your trading desk.\n\n"
            "1️⃣ /subscribe \\- Get Premium Signals\n"
            "2️⃣ /pnl \\- Performance Analytics\n"
            "3️⃣ /invite \\- Earn Rewards\n"
            "4️⃣ /support \\- Tech Assistance"
        )
        if is_admin(user.id): content += f"\n\n{GOLD_SHIELD} /admin \\- Mobile Terminal"
        
        # Send Welcome Banner if exists
        try:
            with open(WELCOME_BANNER, "rb") as photo:
                await update.message.reply_photo(photo=photo, caption=format_premium_card("EXECUTIVE ACCESS", content), parse_mode='MarkdownV2', protect_content=True)
        except:
            await update.message.reply_text(format_premium_card("EXECUTIVE ACCESS", content), parse_mode='MarkdownV2', protect_content=True)
            
    except Exception as e:
        await broadcast_error(context.bot, traceback.format_exc(), update.effective_user)

async def pnl_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        signals = TradeAlert.objects.order_by('-sent_at')[:10]
        avg_acc = TradeAlert.objects.aggregate(Avg('accuracy'))['accuracy__avg'] or 0
        
        table = "```\n"
        table += f"{escape_md('DATE       INST    SIDE   ACC')}\n"
        table += f"{escape_md(SEPARATOR[:25])}\n"
        for s in signals:
            date_str = s.sent_at.strftime('%d/%m') if s.sent_at else "N/A"
            line = f"{date_str:<10} {s.instrument[:5]:<7} {s.side[:4]:<6} {s.accuracy}"
            table += f"{escape_md(line)}\n"
        table += "```"
        
        content = (
            f"📈 *TOTAL ACCURACY:* `{avg_acc:.1f}%`\n\n"
            f"📊 *RECENT SIGNALS:*\n{table}"
        )
        await update.message.reply_text(format_premium_card("PERFORMANCE ANALYTICS", content), parse_mode='MarkdownV2', protect_content=True)
    except Exception as e:
        await broadcast_error(context.bot, traceback.format_exc())

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_username = (await context.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start={user.id}"
    
    content = (
        "💎 *ELITE REWARDS*\n\n"
        "Invite colleagues to use the terminal. They receive a *3\\-Day Premium Trial* immediately upon joining\\.\n\n"
        f"🔗 *Invite Link:* `{invite_link}`"
    )
    await update.message.reply_text(format_premium_card("PROPAGATION", content), parse_mode='MarkdownV2', protect_content=True)

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_feedback'] = True
    await update.message.reply_text(format_premium_card("EXECUTIVE FEEDBACK", "Share your experience or suggest optimizations for the Slancio Algos:"), parse_mode='MarkdownV2', protect_content=True)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        plans = SubscriptionPlan.objects.all()
        if not plans.exists():
            SubscriptionPlan.objects.get_or_create(name="Pro 7 Days", price_in_paise=49900, duration_days=7)
            SubscriptionPlan.objects.get_or_create(name="Pro 30 Days", price_in_paise=149900, duration_days=30)
            plans = SubscriptionPlan.objects.all()
        
        keyboard = [[InlineKeyboardButton(f"💎 {p.name} - ₹{p.price_in_paise/100}", callback_data=f"buy_{p.id}")] for p in plans]
        await update.message.reply_text(format_premium_card("MEMBERSHIP TIERS", "Select an executive access plan:"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2', protect_content=True)
    except Exception as e:
        await broadcast_error(context.bot, traceback.format_exc())

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(l, callback_data=f"sup_{k}")] for k, l in SupportTicket.QUERY_CHOICES]
    await update.message.reply_text(format_premium_card("TECH SUPPORT", "Our engineers are ready to assist. Select query type:"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2', protect_content=True)

async def admin_console(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        log_security_breach(update.effective_user, "/admin")
        return await update.message.reply_text("🛑 Access Denied.")
    
    kb = [
        [InlineKeyboardButton("💰 Pending Verifications", callback_data="adm_pending_pay")],
        [InlineKeyboardButton("🎫 Active Tickets", callback_data="adm_tickets")],
        [InlineKeyboardButton("🔋 Core Health", callback_data="adm_health")],
        [InlineKeyboardButton("⏱️ Global Timeframe", callback_data="adm_timeframe")],
    ]
    await update.message.reply_text(format_premium_card("ADMIN TERMINAL", "System core management active."), reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2', protect_content=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_heartbeat()
        query = update.callback_query
        await query.answer()
        data, user_id = query.data, update.effective_user.id
        
        if data.startswith('buy_'):
            plan = SubscriptionPlan.objects.get(id=data.split('_')[1])
            vpa = escape_md(getattr(settings, 'UPI_MERCHANT_VPA', 'myslancio@jio'))
            upi = f"upi://pay?pa={vpa}&pn=Slancio&am={plan.price_in_paise/100}&cu=INR"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⚡ PAY via UPI", url=upi)]])
            
            content = (
                f"💠 *Plan:* `{escape_md(plan.name)}`\n"
                f"💰 *Price:* `₹{plan.price_in_paise/100}`\n"
                f"🏦 *UPI ID:* `{vpa}`\n\n"
                "1️⃣ Click to pay via your preferred UPI app\\.\n"
                "2️⃣ **Take a screenshot** of the confirmation\\.\n"
                "3️⃣ **Upload image** here for verification\\.\n\n"
                "_Activation is usually processed within 15 minutes\\._"
            )
            await query.edit_message_text(format_premium_card("CHECKOUT", content), reply_markup=kb, parse_mode='MarkdownV2')
            context.user_data['pending_plan_id'] = plan.id

        elif data == 'adm_health':
            if not is_admin(user_id): return
            ms = HealthMonitor.objects.all()
            content = ""
            for m in ms:
                status_icon = "🟢" if m.status == 'Healthy' else "🔴"
                content += f"{status_icon} *{escape_md(m.component)}:* `{escape_md(m.status)}`\n🕝 _last:_ `{m.last_heartbeat.strftime('%H:%M:%S')}`\n\n"
            await query.edit_message_text(format_premium_card("CORE STATUS", content), parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="adm_health")]]))

        elif data == 'adm_timeframe':
            if not is_admin(user_id): return
            current_tf = GlobalConfig.get_value('active_timeframe', '15m')
            tfs = ['1m', '5m', '15m', '30m', '1h']
            kb = [[InlineKeyboardButton(f"{'✅ ' if tf == current_tf else ''}{tf}", callback_data=f"set_tf_{tf}") for tf in tfs[i:i+3]] for i in range(0, len(tfs), 3)]
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="adm_back")])
            await query.edit_message_text(format_premium_card("ENGINE CONTROL", f"Active Interval: `{current_tf}`\n\nConfigure global strategy scanning timeframe:"), reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

        elif data.startswith('set_tf_'):
            if not is_admin(user_id): return
            new_tf = data.split('_')[2]
            GlobalConfig.objects.update_or_create(key='active_timeframe', defaults={'value': new_tf})
            await query.edit_message_text(format_premium_card("SYSTEM UPDATED", f"✅ Strategy engine updated to `{new_tf}` interval\\."), parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="adm_back")]]))

        elif data == 'adm_back':
            await admin_console(update, context)

        elif data.startswith('sup_'):
            context.user_data['support_type'] = data.split('_')[1]
            await query.edit_message_text(format_premium_card("SUPPORT REQUEST", "Please provide detailed information regarding your query:"), parse_mode='MarkdownV2')

        elif data == 'adm_pending_pay':
            txs = Transaction.objects.filter(status='pending')
            if not txs.exists(): return await query.edit_message_text(format_premium_card("QUEUE", "No pending verifications found\\."), parse_mode='MarkdownV2')
            for tx in txs:
                kb = [[InlineKeyboardButton("✅ Approve Access", callback_data=f"approve_{tx.id}")]]
                caption = f"👤 `{tx.profile.telegram_id}`\n📦 `{escape_md(tx.plan.name)}`\n💰 `₹{tx.amount/100}`"
                if tx.screenshot: await query.message.reply_photo(photo=tx.screenshot, caption=format_premium_card("VERIFICATION", caption), reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2', protect_content=True)
                else: await query.message.reply_text(text=format_premium_card("VERIFICATION", caption), reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2', protect_content=True)

        elif data.startswith('approve_'):
            tx = Transaction.objects.get(id=data.split('_')[1])
            tx.status, p = 'success', tx.profile
            tx.save()
            p.is_active_subscriber = True
            p.subscription_end_date = (p.subscription_end_date or timezone.now()) + timedelta(days=tx.plan.duration_days)
            p.save()
            await query.edit_message_caption(caption=escape_md(query.message.caption) + "\n\n✅ *VERIFIED & APPROVED*", parse_mode='MarkdownV2')
            await context.bot.send_message(chat_id=p.telegram_id, text=format_premium_card("ACCESS GRANTED", f"Your executive access is now active until `{p.subscription_end_date.strftime('%d-%b-%Y')}`\\!"), parse_mode='MarkdownV2', protect_content=True)

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
            await update.message.reply_text(format_premium_card("THANK YOU", "Feedback recorded successfully\\. Transmission complete\\."), parse_mode='MarkdownV2', protect_content=True)
            return

        # Photo processing
        if update.message.photo:
            p_id = context.user_data.get('pending_plan_id')
            if not p_id: return await update.message.reply_text("🛑 session expired\\. Use /subscribe to begin\\.", parse_mode='MarkdownV2')
            profile = Profile.objects.get(telegram_id=user_id)
            plan = SubscriptionPlan.objects.get(id=p_id)
            tx = Transaction.objects.create(profile=profile, plan=plan, amount=plan.price_in_paise, status='pending')
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            tx.screenshot.save(f"proof_{tx.id}.jpg", ContentFile(await file.download_as_bytearray()))
            tx.save()
            await update.message.reply_text(format_premium_card("PENDING", "Receipt uploaded\\. Admin verification in progress\\."), parse_mode='MarkdownV2', protect_content=True)
            del context.user_data['pending_plan_id']; return

        # Support type processing
        sup = context.user_data.get('support_type')
        if sup:
            profile = Profile.objects.get(telegram_id=user_id)
            SupportTicket.objects.create(user=profile, query_type=sup, message=update.message.text)
            await update.message.reply_text(format_premium_card("TRANSMITTED", "Signal request sent to technical department\\."), parse_mode='MarkdownV2', protect_content=True)
            del context.user_data['support_type']
        else:
            await update.message.reply_text("🤖 Executive Terminal ready\\. Use `/start` for interaction\\.", parse_mode='MarkdownV2')

    except Exception as e: await broadcast_error(context.bot, traceback.format_exc())

def get_application():
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("pnl", pnl_report))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("admin", admin_console))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & (~filters.COMMAND), handle_message))
    return app
