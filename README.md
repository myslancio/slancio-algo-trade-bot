# Enterprise Telegram Bot (Zero-Cost Edition)

This is a professional-grade Telegram subscription and trade alert system optimized for **PythonAnywhere Free Tier**.

## Project Components
- **Bot**: Handles subscriptions, UPI links, and screenshot verification.
- **Admin Console**: Manage signals, verify payments, and monitor system health.
- **Structured Alerts**: Support for Nifty50, BankNifty, etc., with Entry, SL, and 3 Targets.

## Quick Setup on PythonAnywhere
1. **Upload** all files to your dashboard.
2. **Create Virtualenv**:
   ```bash
   mkvirtualenv enterprise-venv --python=python3.10
   pip install -r requirements.txt
   ```
3. **Database**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. **Configuration**: Update `TELEGRAM_BOT_TOKEN` and `UPI_MERCHANT_VPA` in `enterprise_project/settings.py`.
5. **Run Bot**:
   Add a scheduled task for `python manage.py run_bot`.

## Folder Structure
- `alerts/`: Trade signal models and admin logic.
- `subscriptions/`: Payment verification and user profiles.
- `bot_app/`: Telegram bot handlers.
- `core/`: Resilience middleware (Self-healing).
- `media/`: Stores user-uploaded payment screenshots.

---
*Created by Antigravity AI*
