from django.urls import path
from . import views

app_name = 'fitur_kuning'

urlpatterns = [
    # Venue
    path('venue/',                              views.venue_list,    name='venue_list'),
    path('venue/create/',                       views.venue_create,  name='venue_create'),
    path('venue/update/<uuid:venue_id>/',       views.venue_update,  name='venue_update'),
    path('venue/delete/<uuid:venue_id>/',       views.venue_delete,  name='venue_delete'),

    # Event
    path('event/',                              views.event_list,    name='event_list'),
    path('event/create/',                       views.event_create,  name='event_create'),
    path('event/update/<uuid:event_id>/',       views.event_update,  name='event_update'),
]