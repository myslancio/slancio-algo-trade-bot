from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .models import Transaction, Profile, SubscriptionPlan
from django.utils import timezone

def payment_status(request, tx_id):
    try:
        tx = Transaction.objects.get(id=tx_id)
        return JsonResponse({'status': tx.status})
    except:
        return JsonResponse({'error': 'Invalid Transaction'}, status=400)
