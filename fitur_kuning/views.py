from django.shortcuts import render
from django.db import connection

# Fungsi untuk nampilin Venue
def venue_list(request):
    with connection.cursor() as cursor:
        # Kita set search_path dulu supaya Django nyari tabel di dalam schema Taktiktuk
        cursor.execute("SET search_path TO Taktiktuk;")
        
        # Ambil data dari tabel VENUE yang ada di Supabase
        cursor.execute("SELECT venue_id, venue_name, address, city, capacity, is_reserved FROM VENUE;")
        
        columns = [col[0] for col in cursor.description]
        venues_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, 'venue.html', {'venues': venues_data})

# Fungsi untuk nampilin Event (BIAR ERROR-NYA HILANG)
def event_list(request):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO Taktiktuk;")
        
        # Ambil data dari tabel EVENT yang ada di Supabase
        cursor.execute("SELECT event_id, event_title, event_datetime, description FROM EVENT;")
        
        columns = [col[0] for col in cursor.description]
        events_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Pastikan kamu punya file event.html di folder templates ya!
    return render(request, 'event.html', {'events': events_data})