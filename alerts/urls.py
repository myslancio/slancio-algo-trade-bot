from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.signal_webhook, name='signal_webhook'),
]
