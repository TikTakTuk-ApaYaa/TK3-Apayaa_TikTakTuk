from django.urls import path
from . import views

# app_name dihapus karena config/urls.py pakai path('', include(...))

urlpatterns = [
    # Halaman
    path('artists/', views.artist_page, name='artist_page'),
    path('ticket-categories/', views.ticket_category_page, name='ticket_category_page'),

    # API Artist 
    path('api/artists/', views.api_artists, name='api_artists'),
    path('api/artists/<str:artist_id>/', views.api_artist_detail, name='api_artist_detail'),

    # API Ticket Category 
    path('api/ticket-categories/', views.api_ticket_categories, name='api_ticket_categories'),
    path('api/ticket-categories/<str:category_id>/', views.api_ticket_category_detail, name='api_ticket_category_detail'),

    # API Events (untuk dropdown)
    path('api/events/', views.api_events, name='api_events'),
]