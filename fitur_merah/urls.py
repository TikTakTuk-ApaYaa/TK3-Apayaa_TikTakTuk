from django.urls import path
from . import views

urlpatterns = [
    path('seats/', views.seat_management, name='seat_management'),
    path('tickets/', views.ticket_management, name='ticket_management'),
    path('api/merah/seats/', views.api_seats, name='api_seats'),
    path('api/merah/seats/<uuid:seat_id>/', views.api_seat_detail, name='api_seat_detail'),
    path('api/merah/tickets/', views.api_tickets, name='api_tickets'),
    path('api/merah/tickets/<uuid:ticket_id>/', views.api_ticket_detail, name='api_ticket_detail'),
    path('api/merah/ticket-options/', views.api_ticket_options, name='api_ticket_options'),
]
