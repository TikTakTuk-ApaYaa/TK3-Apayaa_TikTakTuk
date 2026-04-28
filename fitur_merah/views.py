from django.shortcuts import render

# Create your views here.

def seat_management(request):
    # Mock data - replace with actual database queries
    context = {
        'total_seat': 36,
        'total_available': 24,
        'total_filled': 12,
        'venues': [
            {'id': 1, 'name': 'Stadion Gelora Bung Karno'},
            {'id': 2, 'name': 'Jakarta Convention Center'},
        ],
        'seats': [
            {'section': 'VIP', 'row': 'A', 'number': '1', 'venue_name': 'Stadion Gelora Bung Karno', 'is_assigned': False},
            {'section': 'VIP', 'row': 'A', 'number': '2', 'venue_name': 'Stadion Gelora Bung Karno', 'is_assigned': True},
            # Add more mock data
        ]
    }
    return render(request, 'seat-main.html', context)

def ticket_management(request):
    # Mock data - replace with actual database queries
    context = {
        'is_admin': True,  # For operator role
        'total_ticket': 30,
        'total_valid': 25,
        'total_used': 5,
        'tickets': [
            # Empty for now
        ]
    }
    return render(request, 'ticket-main.html', context)
