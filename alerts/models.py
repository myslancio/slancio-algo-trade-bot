from django.db import models

class TradeAlert(models.Model):
    INSTRUMENT_CHOICES = (
        ('NIFTY50', 'Nifty 50'),
        ('BANKNIFTY', 'Bank Nifty'),
        ('BANKEX', 'Bankex'),
        ('SENSEX', 'Sensex'),
        ('MIDCAPNIFTY', 'Midcap Nifty'),
        ('FINNIFTY', 'Finnifty'),
    )
    SIDE_CHOICES = (
        ('CALL', 'CALL'),
        ('PUT', 'PUT'),
    )

    instrument = models.CharField(max_length=50, choices=INSTRUMENT_CHOICES)
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    stoploss = models.DecimalField(max_digits=10, decimal_places=2)
    target1 = models.DecimalField(max_digits=10, decimal_places=2)
    target2 = models.DecimalField(max_digits=10, decimal_places=2)
    target3 = models.DecimalField(max_digits=10, decimal_places=2)
    
    # New Detailed Fields
    contract = models.CharField(max_length=100, null=True, blank=True)
    expiry = models.CharField(max_length=50, null=True, blank=True)
    accuracy = models.CharField(max_length=20, default="94%")
    premium_decay = models.CharField(max_length=20, default="Low")
    status = models.CharField(max_length=20, default="Active")
    premium_ltp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    spot_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Advanced Metrics
    gamma_velocity = models.CharField(max_length=50, null=True, blank=True)
    oi_momentum_score = models.CharField(max_length=50, null=True, blank=True)
    imi_score = models.FloatField(null=True, blank=True)
    
    # Live Tracking Status
    t1_hit = models.BooleanField(default=False)
    t2_hit = models.BooleanField(default=False)
    t3_hit = models.BooleanField(default=False)
    sl_hit = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    additional_notes = models.TextField(null=True, blank=True)


    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.instrument} {self.side} @ {self.entry_price}"

class ArchitectureError(models.Model):
    error_message = models.TextField()
    traceback = models.TextField()
    component = models.CharField(max_length=100)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error in {self.component} at {self.created_at}"
