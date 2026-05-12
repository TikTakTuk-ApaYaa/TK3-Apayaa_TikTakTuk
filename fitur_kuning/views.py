import json
import uuid
from functools import wraps

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


# ─── helpers ────────────────────────────────────────────────────────────────

def _login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('fitur_wajib:login')
        return fn(request, *args, **kwargs)
    return wrapper


def _schema(cursor):
    cursor.execute("SET search_path TO taktiktuk;")


def _clean_db_error(exc):
    """Return the first meaningful line from a DB exception message."""
    for line in str(exc).splitlines():
        line = line.strip()
        if line and not line.startswith('LINE') and not line.startswith('^'):
            return line.removeprefix('ERROR:').strip()
    return str(exc).strip()


# ─── VENUE ──────────────────────────────────────────────────────────────────

@_login_required
def venue_list(request):
    role = request.session.get('role', 'guest')

    with connection.cursor() as cur:
        _schema(cur)
        cur.execute("""
            SELECT venue_id, venue_name, address, city, capacity, is_reserved
            FROM venue
            ORDER BY venue_name
        """)
        cols = [c[0] for c in cur.description]
        raw  = [dict(zip(cols, row)) for row in cur.fetchall()]

    venues = [
        {
            'id':       str(v['venue_id']),
            'name':     v['venue_name'],
            'address':  v['address'],
            'city':     v['city'],
            'capacity': v['capacity'],
            'reserved': v['is_reserved'],
        }
        for v in raw
    ]

    return render(request, 'venue.html', {
        'venues_json': json.dumps(venues, default=str),
        'role': role,
    })


@_login_required
def venue_create(request):
    if request.session.get('role') not in ('admin', 'organizer'):
        return JsonResponse({'success': False, 'error': 'Akses ditolak.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)

    try:
        data     = json.loads(request.body)
        name     = data.get('name', '').strip()
        city     = data.get('city', '').strip()
        address  = data.get('address', '').strip()
        capacity = data.get('capacity')
        reserved = bool(data.get('reserved', False))

        if not all([name, city, address, capacity]):
            return JsonResponse({'success': False, 'error': 'Semua field wajib diisi!'})

        capacity = int(capacity)
        if capacity <= 0:
            return JsonResponse({'success': False, 'error': 'Kapasitas harus berupa angka positif!'})

        new_id = str(uuid.uuid4())

        with connection.cursor() as cur:
            _schema(cur)
            cur.execute("""
                INSERT INTO venue (venue_id, venue_name, capacity, address, city, is_reserved)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [new_id, name, capacity, address, city, reserved])

        return JsonResponse({'success': True, 'id': new_id, 'message': 'Venue berhasil ditambahkan!'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': _clean_db_error(exc)})


@_login_required
def venue_update(request, venue_id):
    if request.session.get('role') not in ('admin', 'organizer'):
        return JsonResponse({'success': False, 'error': 'Akses ditolak.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)

    try:
        data     = json.loads(request.body)
        name     = data.get('name', '').strip()
        city     = data.get('city', '').strip()
        address  = data.get('address', '').strip()
        capacity = data.get('capacity')
        reserved = bool(data.get('reserved', False))

        if not all([name, city, address, capacity]):
            return JsonResponse({'success': False, 'error': 'Semua field wajib diisi!'})

        capacity = int(capacity)
        if capacity <= 0:
            return JsonResponse({'success': False, 'error': 'Kapasitas harus berupa angka positif!'})

        with connection.cursor() as cur:
            _schema(cur)
            cur.execute("""
                UPDATE venue
                SET venue_name=%s, capacity=%s, address=%s, city=%s, is_reserved=%s
                WHERE venue_id=%s
            """, [name, capacity, address, city, reserved, str(venue_id)])

        return JsonResponse({'success': True, 'message': 'Venue berhasil diperbarui!'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': _clean_db_error(exc)})


@_login_required
def venue_delete(request, venue_id):
    if request.session.get('role') not in ('admin', 'organizer'):
        return JsonResponse({'success': False, 'error': 'Akses ditolak.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)

    try:
        with connection.cursor() as cur:
            _schema(cur)
            cur.execute("DELETE FROM venue WHERE venue_id = %s", [str(venue_id)])

        return JsonResponse({'success': True, 'message': 'Venue berhasil dihapus.'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': _clean_db_error(exc)})


# ─── EVENT ──────────────────────────────────────────────────────────────────

@_login_required
def event_list(request):
    role         = request.session.get('role', 'guest')
    organizer_id = request.session.get('organizer_id')

    with connection.cursor() as cur:
        _schema(cur)

        if role == 'organizer' and organizer_id:
            cur.execute("""
                SELECT e.event_id, e.event_title, e.event_datetime, e.description,
                       e.venue_id, e.organizer_id,
                       v.venue_name, v.city, v.capacity
                FROM event e
                JOIN venue v ON e.venue_id = v.venue_id
                WHERE e.organizer_id = %s
                ORDER BY e.event_datetime
            """, [str(organizer_id)])
        else:
            cur.execute("""
                SELECT e.event_id, e.event_title, e.event_datetime, e.description,
                       e.venue_id, e.organizer_id,
                       v.venue_name, v.city, v.capacity
                FROM event e
                JOIN venue v ON e.venue_id = v.venue_id
                ORDER BY e.event_datetime
            """)

        ecols  = [c[0] for c in cur.description]
        events = [dict(zip(ecols, row)) for row in cur.fetchall()]

        for ev in events:
            ev['event_id']     = str(ev['event_id'])
            ev['venue_id']     = str(ev['venue_id'])
            ev['organizer_id'] = str(ev['organizer_id'])

            dt = ev.get('event_datetime')
            if dt:
                ev['date'] = dt.strftime('%Y-%m-%d')
                ev['time'] = dt.strftime('%H:%M')
            del ev['event_datetime']

            # artists
            cur.execute("""
                SELECT a.name
                FROM event_artist ea JOIN artist a ON ea.artist_id = a.artist_id
                WHERE ea.event_id = %s
            """, [ev['event_id']])
            ev['artists'] = [r[0] for r in cur.fetchall()]

            # ticket categories
            cur.execute("""
                SELECT category_id, category_name, price, quota
                FROM ticket_category WHERE tevent_id = %s
            """, [ev['event_id']])
            ccols = [c[0] for c in cur.description]
            cats  = [dict(zip(ccols, r)) for r in cur.fetchall()]
            for c in cats:
                c['category_id'] = str(c['category_id'])
                c['price']       = float(c['price'])
            ev['cats'] = cats

        # venue list for dropdowns
        cur.execute("SELECT venue_id, venue_name, city, capacity FROM venue ORDER BY venue_name")
        vcols  = [c[0] for c in cur.description]
        venues = [dict(zip(vcols, r)) for r in cur.fetchall()]
        for v in venues:
            v['venue_id'] = str(v['venue_id'])

        # distinct artist names for filter
        cur.execute("SELECT DISTINCT name FROM artist ORDER BY name")
        all_artists = [r[0] for r in cur.fetchall()]

    return render(request, 'event.html', {
        'events_json':      json.dumps(events,      default=str),
        'venues_json':      json.dumps(venues,      default=str),
        'all_artists_json': json.dumps(all_artists, default=str),
        'role': role,
    })


@_login_required
def event_create(request):
    if request.session.get('role') not in ('admin', 'organizer'):
        return JsonResponse({'success': False, 'error': 'Akses ditolak.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)

    try:
        data     = json.loads(request.body)
        title    = data.get('title', '').strip()
        date     = data.get('date', '')
        time_str = data.get('time', '')
        venue_id = data.get('venueId', '')
        artists  = data.get('artists', [])
        cats     = data.get('cats', [])
        desc     = data.get('desc', '').strip()

        if not all([title, date, time_str, venue_id]):
            return JsonResponse({'success': False, 'error': 'Judul, tanggal, waktu, dan venue wajib diisi!'})
        if not cats:
            return JsonResponse({'success': False, 'error': 'Minimal 1 kategori tiket wajib diisi!'})

        role         = request.session.get('role')
        organizer_id = request.session.get('organizer_id')
        new_event_id = str(uuid.uuid4())
        event_dt     = f"{date} {time_str}:00"

        with connection.cursor() as cur:
            _schema(cur)

            # Admin: pakai organizer pertama kalau tidak ada organizer_id di session
            if role == 'admin' and not organizer_id:
                cur.execute("SELECT organizer_id FROM organizer LIMIT 1")
                row = cur.fetchone()
                organizer_id = str(row[0]) if row else None

            if not organizer_id:
                return JsonResponse({'success': False, 'error': 'Organizer tidak ditemukan di session.'})

            # Validasi total kuota vs kapasitas venue
            cur.execute("SELECT capacity FROM venue WHERE venue_id = %s", [venue_id])
            row = cur.fetchone()
            if row:
                total_q = sum(int(c.get('quota', 0)) for c in cats)
                if total_q > row[0]:
                    return JsonResponse({'success': False,
                        'error': f'Total kuota ({total_q}) melebihi kapasitas venue ({row[0]})!'})

            # Insert event
            cur.execute("""
                INSERT INTO event (event_id, event_datetime, event_title, description, venue_id, organizer_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [new_event_id, event_dt, title, desc, venue_id, str(organizer_id)])

            # Artists (find or create)
            for aname in artists:
                aname = aname.strip()
                if not aname:
                    continue
                cur.execute("SELECT artist_id FROM artist WHERE LOWER(name) = LOWER(%s)", [aname])
                row = cur.fetchone()
                if row:
                    artist_id = str(row[0])
                else:
                    artist_id = str(uuid.uuid4())
                    cur.execute("INSERT INTO artist (artist_id, name) VALUES (%s, %s)",
                                [artist_id, aname])
                cur.execute("""
                    INSERT INTO event_artist (event_id, artist_id, role)
                    VALUES (%s, %s, 'Performer')
                    ON CONFLICT DO NOTHING
                """, [new_event_id, artist_id])

            # Ticket categories
            for cat in cats:
                cur.execute("""
                    INSERT INTO ticket_category (category_id, category_name, quota, price, tevent_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, [str(uuid.uuid4()), cat['name'], int(cat['quota']),
                      float(cat['price']), new_event_id])

        return JsonResponse({'success': True, 'id': new_event_id, 'message': 'Acara berhasil dibuat!'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': _clean_db_error(exc)})


@_login_required
def event_update(request, event_id):
    if request.session.get('role') not in ('admin', 'organizer'):
        return JsonResponse({'success': False, 'error': 'Akses ditolak.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)

    try:
        data     = json.loads(request.body)
        title    = data.get('title', '').strip()
        date     = data.get('date', '')
        time_str = data.get('time', '')
        venue_id = data.get('venueId', '')
        artists  = data.get('artists', [])
        cats     = data.get('cats', [])
        desc     = data.get('desc', '').strip()

        if not all([title, date, time_str, venue_id]):
            return JsonResponse({'success': False, 'error': 'Judul, tanggal, waktu, dan venue wajib diisi!'})

        event_dt = f"{date} {time_str}:00"
        eid      = str(event_id)

        with connection.cursor() as cur:
            _schema(cur)

            # Validasi total kuota vs kapasitas
            cur.execute("SELECT capacity FROM venue WHERE venue_id = %s", [venue_id])
            row = cur.fetchone()
            if row and cats:
                total_q = sum(int(c.get('quota', 0)) for c in cats)
                if total_q > row[0]:
                    return JsonResponse({'success': False,
                        'error': f'Total kuota ({total_q}) melebihi kapasitas venue ({row[0]})!'})

            cur.execute("""
                UPDATE event
                SET event_title=%s, event_datetime=%s, description=%s, venue_id=%s
                WHERE event_id=%s
            """, [title, event_dt, desc, venue_id, eid])

            # Re-create artists
            cur.execute("DELETE FROM event_artist WHERE event_id = %s", [eid])
            for aname in artists:
                aname = aname.strip()
                if not aname:
                    continue
                cur.execute("SELECT artist_id FROM artist WHERE LOWER(name) = LOWER(%s)", [aname])
                row = cur.fetchone()
                if row:
                    artist_id = str(row[0])
                else:
                    artist_id = str(uuid.uuid4())
                    cur.execute("INSERT INTO artist (artist_id, name) VALUES (%s, %s)",
                                [artist_id, aname])
                cur.execute("""
                    INSERT INTO event_artist (event_id, artist_id, role)
                    VALUES (%s, %s, 'Performer')
                    ON CONFLICT DO NOTHING
                """, [eid, artist_id])

            # Re-create categories
            cur.execute("DELETE FROM ticket_category WHERE tevent_id = %s", [eid])
            for cat in cats:
                cur.execute("""
                    INSERT INTO ticket_category (category_id, category_name, quota, price, tevent_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, [str(uuid.uuid4()), cat['name'], int(cat['quota']),
                      float(cat['price']), eid])

        return JsonResponse({'success': True, 'message': 'Acara berhasil diperbarui!'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': _clean_db_error(exc)})