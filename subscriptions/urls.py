from django.urls import path
from . import views

urlpatterns = [
    path('create-order/', views.create_order, name='create_order'),
    path('razorpay-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
]
