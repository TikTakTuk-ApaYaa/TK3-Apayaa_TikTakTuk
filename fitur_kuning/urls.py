from django.urls import path
from . import views

app_name = 'fitur_kuning'

urlpatterns = [
    # Routing untuk halaman venue
    path('venue/', views.venue_list, name='venue_list'),
    path('event/', views.event_list, name='event_list'),
]