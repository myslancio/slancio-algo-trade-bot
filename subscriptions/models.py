from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    is_active_subscriber = models.BooleanField(default=False)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Growth & Marketing (NEW)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    has_used_trial = models.BooleanField(default=False)
    trial_expiry = models.DateTimeField(null=True, blank=True)
    marketing_alert_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username or self.telegram_id} - {'Active' if self.is_active_subscriber else 'Inactive'}"

class Feedback(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user.telegram_id}"

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price_in_paise = models.IntegerField()
    duration_days = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return self.name

class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount = models.IntegerField()
    screenshot = models.ImageField(upload_to='payment_proofs/', null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.telegram_id} - {self.amount} - {self.status}"

class SupportTicket(models.Model):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('RESOLVED', 'Resolved'),
    )
    QUERY_CHOICES = (
        ('PAYMENT', 'Payment not reflected'),
        ('SIGNALS', 'How to use signals'),
        ('TECHNICAL', 'Technical Issue'),
        ('OTHER', 'Other / General Query'),
    )
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    query_type = models.CharField(max_length=20, choices=QUERY_CHOICES)
    message = models.TextField()
    admin_reply = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket from {self.user.telegram_id} - {self.query_type}"


class SecurityLog(models.Model):
    user_id = models.BigIntegerField()
    username = models.CharField(max_length=255, null=True, blank=True)
    command_attempted = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"Unauthorized {self.command_attempted} by {self.user_id}"

class HealthMonitor(models.Model):
    component = models.CharField(max_length=50, unique=True) # 'Bot' or 'Engine'
    last_heartbeat = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='Healthy')
    error_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.component} - {self.status}"

class GlobalConfig(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=100)

    @classmethod
    def get_value(cls, key, default=None):
        try: return cls.objects.get(key=key).value
        except: return default

    def __str__(self):
        return f"{self.key}: {self.value}"
