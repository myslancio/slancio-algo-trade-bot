from django.urls import path
from . import views

urlpatterns = [
    path('status/<int:tx_id>/', views.payment_status, name='payment_status'),
]
