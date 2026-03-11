from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.conf import settings
from .models import Transaction, Profile, SubscriptionPlan
import json
from datetime import timedelta
from django.utils import timezone

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_order(request):
    if request.method == "POST":
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        telegram_id = data.get('telegram_id')
        
        plan = SubscriptionPlan.objects.get(id=plan_id)
        profile, _ = Profile.objects.get_or_create(telegram_id=telegram_id)
        
        order_data = {
            'amount': plan.price_in_paise,
            'currency': 'INR',
            'payment_capture': '1'
        }
        
        razorpay_order = client.order.create(data=order_data)
        
        Transaction.objects.create(
            profile=profile,
            plan=plan,
            razorpay_order_id=razorpay_order['id'],
            amount=plan.price_in_paise,
            status='pending'
        )
        
        return JsonResponse(razorpay_order)

@csrf_exempt
def razorpay_webhook(request):
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    webhook_secret = "YOUR_WEBHOOK_SECRET" # Should be in settings
    
    try:
        client.utility.verify_webhook_signature(request.body.decode(), webhook_signature, webhook_secret)
        data = json.loads(request.body)
        
        if data['event'] == 'payment.captured':
            payment_id = data['payload']['payment']['entity']['id']
            order_id = data['payload']['payment']['entity']['order_id']
            
            transaction = Transaction.objects.get(razorpay_order_id=order_id)
            transaction.razorpay_payment_id = payment_id
            transaction.status = 'success'
            transaction.save()
            
            # Activate subscription
            profile = transaction.profile
            profile.is_active_subscriber = True
            
            # Update end date
            days = transaction.plan.duration_days
            profile.subscription_end_date = timezone.now() + timedelta(days=days)
            profile.save()
            
            # Here you would trigger a Telegram message to the user
            # via a bot service
            
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(status=400)
