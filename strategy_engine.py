import os
import django
import pandas as pd
import numpy as np
import yfinance as yf
import time
import traceback
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_project.settings')
django.setup()

from subscriptions.models import Profile, HealthMonitor, GlobalConfig
from alerts.models import TradeAlert
from django.conf import settings
from telegram import Bot
import asyncio
from core.ui import format_premium_card, escape_md, SEPARATOR, BLUE_DIAMOND

# --- HELPERS ---
def format_card(title, content):
    return format_premium_card(title, content)

def get_current_timeframe():
    return GlobalConfig.get_value('active_timeframe', '15m')

def update_heartbeat(status='Healthy', error_count=0):
    HealthMonitor.objects.update_or_create(
        component='Engine', 
        defaults={'status': status, 'error_count': HealthMonitor.objects.get_or_create(component='Engine')[0].error_count + error_count}
    )

async def notify_admin_error(error_msg):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    admin_ids = getattr(settings, 'ADMIN_TELEGRAM_IDS', [])
    for aid in admin_ids:
        try: await bot.send_message(chat_id=aid, text=f"🚨 *Engine Alert:* {error_msg}", parse_mode='Markdown')
        except: pass

def generate_technical_chart(df, ticker, entry, targets, stoploss):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df.index, df['Close'], color='#00d2ff', linewidth=2, label='Price Action')
    ax.fill_between(df.index, df['Close'].min(), df['Close'], color='#00d2ff', alpha=0.1) # Glow effect
    
    ax.axhline(y=float(entry), color='white', linestyle='--', alpha=0.8, label=f'Entry: {entry}')
    ax.axhline(y=float(stoploss), color='#ff4b2b', linestyle='-', linewidth=2.5, label=f'SL: {stoploss}')
    
    colors = ['#f9d423', '#e14eca', '#32ff7e']
    for idx, target in enumerate(targets):
        ax.axhline(y=float(target), color=colors[idx], linestyle='--', alpha=0.9, linewidth=1.5, label=f'T{idx+1}: {target}')
    
    ax.set_title(f"🚀 {ticker} - PREMIUM ANALYSIS", fontsize=14, color='white', fontweight='bold', pad=20)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.2, facecolor='black', edgecolor='white')
    ax.grid(color='grey', linestyle='-', linewidth=0.1, alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.xticks(rotation=45)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', transparent=True)
    buf.seek(0)
    plt.close()
    return buf

# --- ALERT BROADCASTERS ---
async def broadcast_executive_signal(alert):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    active_profiles = Profile.objects.filter(is_active_subscriber=True)
    try:
        tf = get_current_timeframe()
        df = yf.download(alert.instrument, period="5d", interval=tf if tf != '1m' else '1m', progress=False)
        chart_buf = generate_technical_chart(df.tail(40), alert.instrument, alert.entry_price, [alert.target1, alert.target2, alert.target3], alert.stoploss)
    except: chart_buf = None

    card = (
        f"📊 *TERMINAL:* `{escape_md(alert.instrument)}`\n"
        f"⚡ *ACTION:* {escape_md(alert.side.upper())}\n"
        f"⏱️ *INTERVAL:* `{escape_md(tf)}`\n"
        f"{SEPARATOR}\n"
        f"💰 *ENTRY:* `{alert.entry_price}`\n"
        f"🛑 *STOP LOSS:* `{alert.stoploss}`\n\n"
        f"🎯 *T1:* `{alert.target1}`\n"
        f"🎯 *T2:* `{alert.target2}`\n"
        f"🎯 *T3:* `{alert.target3}`\n"
        f"{SEPARATOR}\n"
        f"🛡️ *CONFIDENCE:* {escape_md(alert.accuracy)}"
    )
    card_formatted = format_premium_card("ELITE SIGNAL BROADCAST", card)
    profiles_count = active_profiles.count()
    
    for p in active_profiles:
        try:
            if chart_buf:
                chart_buf.seek(0)
                await bot.send_photo(chat_id=p.telegram_id, photo=chart_buf, caption=card_formatted, parse_mode='MarkdownV2', protect_content=True)
            else:
                await bot.send_message(chat_id=p.telegram_id, text=card_formatted, parse_mode='MarkdownV2', protect_content=True)
        except Exception as e:
            print(f"ERROR: Failed to send to {p.telegram_id}: {str(e)}")

async def broadcast_hit_alert(alert, hit_type, current_price):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    active_profiles = Profile.objects.filter(is_active_subscriber=True)
    icons = {'T1': '🎯', 'T2': '🚀', 'T3': '💎', 'SL': '🛑'}
    titles = {'T1': 'TARGET 1 ACHIEVED', 'T2': 'TARGET 2 ACHIEVED', 'T3': 'FINAL TARGET HIT', 'SL': 'TRADE CLOSED (SL)'}
    
    content = (
        f"{icons.get(hit_type, '📍')} *TYPE:* {titles.get(hit_type)}\n"
        f"🔹 *INSTRUMENT:* {alert.instrument}\n"
        f"🔹 *SIDE:* {alert.side}\n"
        f"────────────────────────────────\n"
        f"💰 *HIT PRICE:* {current_price}\n"
        f"📊 *RESULT:* {'PROFIT' if hit_type != 'SL' else 'LOSS'}\n"
    )
    card = format_premium_card("SIGNAL UPDATE", content)
    for p in active_profiles:
        try: await bot.send_message(chat_id=p.telegram_id, text=card, parse_mode='MarkdownV2', protect_content=True)
        except: pass

# --- MONITORING LOOP ---
async def monitor_active_trades():
    active_trades = TradeAlert.objects.filter(is_closed=False, is_sent=True)
    active_profiles = Profile.objects.filter(is_active_subscriber=True)
    
    if not active_trades.exists() or not active_profiles.exists(): 
        return

    for trade in active_trades:
        try:
            data = yf.download(trade.instrument, period="1d", interval="1m", progress=False)
            if data.empty: continue
            
            # Ensure current_price is a scalar float
            current_price = float(data['Close'].iloc[-1])
            t1 = float(trade.target1)
            t2 = float(trade.target2)
            t3 = float(trade.target3)
            sl = float(trade.stoploss)
            
            side = trade.side.upper()
            if side == 'CALL':
                if not trade.t1_hit and current_price >= t1:
                    trade.t1_hit = True; await broadcast_hit_alert(trade, 'T1', current_price)
                if not trade.t2_hit and current_price >= t2:
                    trade.t2_hit = True; await broadcast_hit_alert(trade, 'T2', current_price)
                if not trade.t3_hit and current_price >= t3:
                    trade.t3_hit = True; trade.is_closed = True; trade.closed_at = timezone.now()
                    await broadcast_hit_alert(trade, 'T3', current_price)
                if current_price <= sl:
                    trade.sl_hit = True; trade.is_closed = True; trade.closed_at = timezone.now()
                    await broadcast_hit_alert(trade, 'SL', current_price)
            else: # PUT
                if not trade.t1_hit and current_price <= t1:
                    trade.t1_hit = True; await broadcast_hit_alert(trade, 'T1', current_price)
                if not trade.t2_hit and current_price <= t2:
                    trade.t2_hit = True; await broadcast_hit_alert(trade, 'T2', current_price)
                if not trade.t3_hit and current_price <= t3:
                    trade.t3_hit = True; trade.is_closed = True; trade.closed_at = timezone.now()
                    await broadcast_hit_alert(trade, 'T3', current_price)
                if current_price >= sl:
                    trade.sl_hit = True; trade.is_closed = True; trade.closed_at = timezone.now()
                    await broadcast_hit_alert(trade, 'SL', current_price)
            
            trade.save()
        except Exception as e: print(f"Monitor error: {e}")

async def run_marketing_automation():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    tomorrow = timezone.now() + timedelta(days=1)
    expiring = Profile.objects.filter(has_used_trial=True, subscription_end_date__lte=tomorrow, subscription_end_date__gt=timezone.now(), marketing_alert_sent=False)
    for p in expiring:
        try:
            content = "⚠️ *TRIAL EXPIRING*\n\nYour access ends in <24h. Upgrade now to keep premium signals!"
            await bot.send_message(chat_id=p.telegram_id, text=format_card("FINAL CALL", content), parse_mode='Markdown', protect_content=True)
            p.marketing_alert_sent = True; p.save()
        except: pass

async def run_engine():
    print("Executive Strategy Engine (Multi-TF) starting...")
    while True:
        try:
            await update_heartbeat()
            # 1. Marketing
            await run_marketing_automation()
            # 2. Monitoring
            await monitor_active_trades()
            # 3. Strategy Logic (using get_current_timeframe())
            # tf = get_current_timeframe()
            # scan_market(tf)
            
            await asyncio.sleep(60)
        except Exception as e:
            update_heartbeat(status='Error', error_count=1)
            await notify_admin_error(traceback.format_exc())
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_engine())
