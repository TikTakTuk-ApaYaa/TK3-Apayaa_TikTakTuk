from django.shortcuts import render
from .models import DemoSeat, DemoTicket, DemoTicketCategory, DemoVenue


def ensure_demo_data():
    venue_data = [
        ('Stadion Gelora Bung Karno', 'Jakarta', 'Jl. Pintu Satu Senayan', 77193),
        ('Jakarta Convention Center', 'Jakarta', 'Jl. Gatot Subroto', 15000),
        ('The Kasablanka Hall', 'Jakarta', 'Kota Kasablanka', 5500),
    ]
    venues = {}
    for name, city, address, capacity in venue_data:
        venue, _ = DemoVenue.objects.get_or_create(
            name=name,
            defaults={'city': city, 'address': address, 'capacity': capacity},
        )
        venues[name] = venue

    category_data = [('VIP', 100, 500000), ('Regular', 250, 250000), ('Festival', 180, 350000)]
    categories = {}
    for name, quota, price in category_data:
        category, _ = DemoTicketCategory.objects.get_or_create(
            name=name,
            defaults={'quota': quota, 'price': price},
        )
        categories[name] = category

    seat_data = [
        ('Stadion Gelora Bung Karno', 'VIP', 'A', '1', False),
        ('Stadion Gelora Bung Karno', 'VIP', 'A', '2', True),
        ('Jakarta Convention Center', 'Festival', 'B', '7', False),
        ('The Kasablanka Hall', 'Tribune', 'C', '12', False),
    ]
    seats = {}
    for venue_name, section, row, number, assigned in seat_data:
        seat, _ = DemoSeat.objects.get_or_create(
            venue=venues[venue_name],
            section=section,
            row_number=row,
            seat_number=number,
            defaults={'is_assigned': assigned},
        )
        seats[f'{venue_name}:{section}:{row}:{number}'] = seat

    ticket_data = [
        ('TKT001', 'Concert A', '2024-12-01 20:00', 'Stadion Gelora Bung Karno', 'VIP', 'Stadion Gelora Bung Karno:VIP:A:1', 'ORD001', 'John Doe', 'current_customer', 'Valid'),
        ('TKT002', 'Concert B', '2024-12-08 19:30', 'Jakarta Convention Center', 'Regular', 'Jakarta Convention Center:Festival:B:7', 'ORD002', 'Jane Smith', 'other_customer', 'Terpakai'),
        ('TKT003', 'Indie Night', '2024-12-15 18:30', 'The Kasablanka Hall', 'Festival', 'The Kasablanka Hall:Tribune:C:12', 'ORD003', 'John Doe', 'current_customer', 'Valid'),
    ]
    for code, event, event_time, venue_name, category_name, seat_key, order_id, customer, owner, status in ticket_data:
        DemoTicket.objects.get_or_create(
            ticket_code=code,
            defaults={
                'event_name': event,
                'event_datetime': event_time,
                'venue': venues[venue_name],
                'category': categories[category_name],
                'seat': seats[seat_key],
                'order_id': order_id,
                'customer_name': customer,
                'owner_key': owner,
                'status': status,
            },
        )

def seat_management(request):
    ensure_demo_data()
    seat_rows = DemoSeat.objects.select_related('venue').order_by('venue__name', 'section', 'row_number', 'seat_number')
    venue_rows = DemoVenue.objects.order_by('name')

    context = {
        'total_seat': seat_rows.count(),
        'total_available': seat_rows.filter(is_assigned=False).count(),
        'total_filled': seat_rows.filter(is_assigned=True).count(),
        'venues': [{'id': venue.id, 'name': venue.name} for venue in venue_rows],
        'seats': [
            {
                'section': seat.section,
                'row': seat.row_number,
                'number': seat.seat_number,
                'venue_name': seat.venue.name,
                'is_assigned': seat.is_assigned,
            }
            for seat in seat_rows
        ]
    }
    return render(request, 'seat-main.html', context)

def ticket_management(request):
    ensure_demo_data()
    view_mode = request.GET.get('view') or request.GET.get('role')
    is_customer = view_mode == 'customer'

    ticket_rows = DemoTicket.objects.select_related('venue', 'category', 'seat').order_by('ticket_code')
    if is_customer:
        ticket_rows = ticket_rows.filter(owner_key='current_customer')

    tickets = [
        {
            'status': ticket.status,
            'category': ticket.category.name,
            'event_name': ticket.event_name,
            'ticket_code': ticket.ticket_code,
            'event_datetime': ticket.event_datetime,
            'venue': ticket.venue.name,
            'seat': f'{ticket.seat.row_number}{ticket.seat.seat_number}' if ticket.seat else '-',
            'price': ticket.category.price,
            'order_id': ticket.order_id,
            'customer_name': ticket.customer_name,
            'owner': ticket.owner_key,
        }
        for ticket in ticket_rows
    ]

    context = {
        'is_admin': not is_customer,
        'total_ticket': len(tickets),
        'total_valid': sum(1 for ticket in tickets if ticket['status'] == 'Valid'),
        'total_used': sum(1 for ticket in tickets if ticket['status'] == 'Terpakai'),
        'tickets': tickets,
    }
    return render(request, 'ticket-main.html', context)
