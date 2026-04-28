from django.urls import path
from . import views

urlpatterns = [
    path('seats/', views.seat_management, name='seat_management'),
    path('tickets/', views.ticket_management, name='ticket_management'),
]