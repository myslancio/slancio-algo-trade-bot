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

# --- HELPERS ---
def format_card(title, content):
    border = "────────────────────────────────"
    return f"🛡️ *{title}*\n{border}\n{content}\n{border}\n🌟 *Slancio Algo Trader*"

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
    ax.plot(df.index, df['Close'], color='#00d2ff', linewidth=1.5, label='Price Action')
    ax.axhline(y=float(entry), color='white', linestyle='--', alpha=0.6, label=f'Entry: {entry}')
    ax.axhline(y=float(stoploss), color='#ff4b2b', linestyle='-', linewidth=2, label=f'SL: {stoploss}')
    colors = ['#f9d423', '#e14eca', '#32ff7e']
    for idx, target in enumerate(targets):
        ax.axhline(y=float(target), color=colors[idx], linestyle='--', alpha=0.8, label=f'T1: {target}' if idx==0 else f'T{idx+1}: {target}')
    ax.set_title(f"🚀 {ticker} - Technical Analysis", fontsize=14, color='white', pad=20)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.3)
    ax.grid(color='grey', linestyle='-', linewidth=0.1, alpha=0.5)
    plt.xticks(rotation=45)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
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
        f"┌──────────────────────────────┐\n"
        f"  📊 *SLANCIO EXECUTIVE TERMINAL*\n"
        f"└──────────────────────────────┘\n"
        f"🔹 *INSTRUMENT:* {alert.instrument}\n"
        f"🔹 *ACTION:* {alert.side.upper()}\n"
        f"🔹 *TIMEFRAME:* {tf}\n"
        f"────────────────────────────────\n"
        f"💰 *ENTRY:* {alert.entry_price}\n"
        f"🛑 *STOP LOSS:* {alert.stoploss}\n\n"
        f"🎯 *TARGET 1:* {alert.target1}\n"
        f"🎯 *TARGET 2:* {alert.target2}\n"
        f"🎯 *TARGET 3:* {alert.target3}\n"
        f"────────────────────────────────\n"
        f"🛡️ *TRADE ACCURACY:* {alert.accuracy}\n"
        f"🌟 *POWERED BY SLANCIO ALGO*"
    )
    profiles_count = active_profiles.count()
    print(f"DEBUG: Found {profiles_count} active profiles for broadcast.")
    
    for p in active_profiles:
        try:
            print(f"DEBUG: Attempting broadcast to ID: {p.telegram_id}")
            if chart_buf:
                chart_buf.seek(0)
                await bot.send_photo(chat_id=p.telegram_id, photo=chart_buf, caption=card, parse_mode='Markdown', protect_content=True)
            else:
                await bot.send_message(chat_id=p.telegram_id, text=card, parse_mode='Markdown', protect_content=True)
            print(f"DEBUG: Successfully sent to {p.telegram_id}")
        except Exception as e:
            print(f"ERROR: Failed to send to {p.telegram_id}: {str(e)}")
            import traceback
            traceback.print_exc()

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
    card = format_card("SIGNAL UPDATE", content)
    for p in active_profiles:
        try: await bot.send_message(chat_id=p.telegram_id, text=card, parse_mode='Markdown', protect_content=True)
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
