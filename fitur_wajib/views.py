import json
import re
import uuid
from functools import wraps

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect


# ─── helpers ─────────────────────────────────────────────────────────────────

def _sc(cur):
    cur.execute("SET search_path TO tiktaktuk;")


def _login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('fitur_wajib:login')
        return fn(request, *args, **kwargs)
    return wrapper


def _fmt_rp(value):
    if not value:
        return "Rp 0"
    return f"Rp {float(value)/1_000_000:.1f}M"


def _clean_db_error(exc):
    for line in str(exc).splitlines():
        line = line.strip()
        if line and not line.startswith('LINE') and not line.startswith('^'):
            return line.removeprefix('ERROR:').strip()
    return str(exc).strip()


# ─── LOGIN / LOGOUT ───────────────────────────────────────────────────────────

@csrf_protect
def login(request):
    # Kalau sudah login, langsung ke dashboard
    if request.session.get('user_id'):
        return redirect('fitur_wajib:dashboard')

    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            error = 'Username dan password wajib diisi.'
        else:
            with connection.cursor() as cur:
                _sc(cur)

                # Cek user_account (case-insensitive username)
                cur.execute("""
                    SELECT user_id, username, password
                    FROM user_account
                    WHERE LOWER(username) = LOWER(%s)
                """, [username])
                user = cur.fetchone()

                if not user or user[2] != password:
                    error = 'Username atau password salah.'
                else:
                    user_id = str(user[0])
                    uname   = user[1]

                    # Ambil semua role user ini
                    cur.execute("""
                        SELECT r.role_name
                        FROM account_role ar
                        JOIN role r ON ar.role_id = r.role_id
                        WHERE ar.user_id = %s
                    """, [user_id])
                    roles = [row[0] for row in cur.fetchall()]

                    # Prioritas: administrator > organizer > customer
                    if 'administrator' in roles:
                        role = 'admin'
                    elif 'organizer' in roles:
                        role = 'organizer'
                    else:
                        role = 'customer'

                    # Set session dasar
                    request.session['user_id']  = user_id
                    request.session['username'] = uname
                    request.session['role']     = role

                    # Data tambahan per role
                    if role == 'organizer':
                        cur.execute("""
                            SELECT organizer_id, organizer_name
                            FROM organizer WHERE user_id = %s
                        """, [user_id])
                        org = cur.fetchone()
                        if org:
                            request.session['organizer_id']   = str(org[0])
                            request.session['organizer_name'] = org[1]

                    elif role == 'customer':
                        cur.execute("""
                            SELECT customer_id, full_name
                            FROM customer WHERE user_id = %s
                        """, [user_id])
                        cust = cur.fetchone()
                        if cust:
                            request.session['customer_id'] = str(cust[0])
                            request.session['full_name']   = cust[1]

                    return redirect('fitur_wajib:dashboard')

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    request.session.flush()
    return redirect('fitur_wajib:login')


# ─── REGISTER ────────────────────────────────────────────────────────────────

def pilih_role(request):
    return render(request, 'Cpengguna_pilihRole.html')

@csrf_protect
def registrasi_customer(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()

        if not all([username, password, full_name]):
            error = "Username, Password, dan Nama Lengkap wajib diisi!"
        else:
            try:
                with connection.cursor() as cur:
                    _sc(cur)
                    u_id = str(uuid.uuid4())
                    # 1. Insert ke USER_ACCOUNT
                    cur.execute("INSERT INTO USER_ACCOUNT (user_id, username, password) VALUES (%s, %s, %s)", [u_id, username, password])
                    # 2. Ambil role_id untuk customer
                    cur.execute("SELECT role_id FROM ROLE WHERE LOWER(role_name) = 'customer'")
                    r_id = cur.fetchone()[0]
                    # 3. Insert ke ACCOUNT_ROLE
                    cur.execute("INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s)", [r_id, u_id])
                    # 4. Insert ke CUSTOMER
                    cur.execute("INSERT INTO CUSTOMER (customer_id, full_name, phone_number, user_id) VALUES (%s, %s, %s, %s)", 
                                [str(uuid.uuid4()), full_name, phone, u_id])
                return redirect('fitur_wajib:login')
            except Exception as e:
                error = _clean_db_error(e)
    return render(request, 'Cpengguna_registCust.html', {'error': error})

@csrf_protect
def registrasi_organizer(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        org_name = request.POST.get('organizer_name', '').strip()
        email = request.POST.get('contact_email', '').strip()

        if not all([username, password, org_name]):
            error = "Username, Password, dan Nama Organizer wajib diisi!"
        else:
            try:
                with connection.cursor() as cur:
                    _sc(cur)
                    u_id = str(uuid.uuid4())
                    cur.execute("INSERT INTO USER_ACCOUNT (user_id, username, password) VALUES (%s, %s, %s)", [u_id, username, password])
                    cur.execute("SELECT role_id FROM ROLE WHERE LOWER(role_name) = 'organizer'")
                    r_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s)", [r_id, u_id])
                    cur.execute("INSERT INTO ORGANIZER (organizer_id, organizer_name, contact_email, user_id) VALUES (%s, %s, %s, %s)", 
                                [str(uuid.uuid4()), org_name, email, u_id])
                return redirect('fitur_wajib:login')
            except Exception as e:
                error = _clean_db_error(e)
    return render(request, 'Cpengguna_registOrganizer.html', {'error': error})

@csrf_protect
def registrasi_administrator(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not all([username, password]):
            error = "Username dan Password wajib diisi!"
        else:
            try:
                with connection.cursor() as cur:
                    _sc(cur)
                    u_id = str(uuid.uuid4())
                    cur.execute("INSERT INTO USER_ACCOUNT (user_id, username, password) VALUES (%s, %s, %s)", [u_id, username, password])
                    cur.execute("SELECT role_id FROM ROLE WHERE LOWER(role_name) = 'administrator'")
                    r_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s)", [r_id, u_id])
                return redirect('fitur_wajib:login')
            except Exception as e:
                error = _clean_db_error(e)
    return render(request, 'Cpengguna_registAdministrator.html', {'error': error})

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@_login_required
def dashboard(request):
    role         = request.session.get('role', 'admin')
    organizer_id = request.session.get('organizer_id')
    customer_id  = request.session.get('customer_id')
    ctx          = {'role': role}

    with connection.cursor() as cur:
        _sc(cur)

        if role == 'admin':
            cur.execute("SELECT COUNT(*) FROM user_account")
            ctx['total_users'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM event")
            ctx['total_events'] = cur.fetchone()[0]

            cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0) FROM "ORDER"
                WHERE payment_status = 'PAID'
            """)
            ctx['total_revenue'] = _fmt_rp(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM promotion")
            ctx['total_promos'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM venue")
            ctx['total_venues'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM venue WHERE is_reserved = TRUE")
            ctx['reserved_venues'] = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(MAX(capacity), 0) FROM venue")
            cap = cur.fetchone()[0]
            ctx['max_capacity'] = f"{cap:,}".replace(',', '.')

            cur.execute("SELECT COUNT(*) FROM promotion WHERE discount_type = 'PERCENTAGE'")
            ctx['promo_percentage'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM promotion WHERE discount_type = 'NOMINAL'")
            ctx['promo_nominal'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM order_promotion")
            ctx['promo_usage'] = cur.fetchone()[0]

        elif role == 'organizer' and organizer_id:
            ctx['organizer_name'] = request.session.get('organizer_name', 'Organizer')

            cur.execute("""
                SELECT COUNT(*) FROM event
                WHERE organizer_id = %s AND event_datetime >= NOW()
            """, [str(organizer_id)])
            ctx['active_events'] = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(t.ticket_id)
                FROM ticket t
                JOIN ticket_category tc ON t.tcategory_id = tc.category_id
                JOIN event e ON tc.tevent_id = e.event_id
                WHERE e.organizer_id = %s
            """, [str(organizer_id)])
            ctx['tickets_sold'] = cur.fetchone()[0]

            cur.execute("""
                SELECT COALESCE(SUM(o.total_amount), 0)
                FROM "ORDER" o
                JOIN ticket t ON t.torder_id = o.order_id
                JOIN ticket_category tc ON t.tcategory_id = tc.category_id
                JOIN event e ON tc.tevent_id = e.event_id
                WHERE e.organizer_id = %s AND o.payment_status = 'PAID'
            """, [str(organizer_id)])
            ctx['revenue'] = _fmt_rp(cur.fetchone()[0])

            cur.execute("""
                SELECT COUNT(DISTINCT e.venue_id) FROM event e
                WHERE e.organizer_id = %s
            """, [str(organizer_id)])
            ctx['venue_count'] = cur.fetchone()[0]

            cur.execute("""
                SELECT e.event_id, e.event_title, v.venue_name,
                       COUNT(t.ticket_id) AS sold
                FROM event e
                JOIN venue v ON e.venue_id = v.venue_id
                LEFT JOIN ticket_category tc ON tc.tevent_id = e.event_id
                LEFT JOIN ticket t ON t.tcategory_id = tc.category_id
                WHERE e.organizer_id = %s
                GROUP BY e.event_id, e.event_title, v.venue_name
                ORDER BY e.event_datetime
            """, [str(organizer_id)])
            ecols = [c[0] for c in cur.description]
            perf  = [dict(zip(ecols, r)) for r in cur.fetchall()]
            for ep in perf:
                ep['event_id'] = str(ep['event_id'])
            ctx['events_performance'] = perf

        elif role == 'customer' and customer_id:
            ctx['full_name'] = request.session.get('full_name', 'Customer')

            cur.execute("""
                SELECT COUNT(*) FROM ticket t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                WHERE o.customer_id = %s AND o.payment_status = 'PAID'
            """, [str(customer_id)])
            ctx['active_tickets'] = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(DISTINCT tc.tevent_id)
                FROM ticket t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                JOIN ticket_category tc ON t.tcategory_id = tc.category_id
                WHERE o.customer_id = %s AND o.payment_status = 'PAID'
            """, [str(customer_id)])
            ctx['events_attended'] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM promotion")
            ctx['available_promos'] = cur.fetchone()[0]

            cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0) FROM "ORDER"
                WHERE customer_id = %s AND payment_status = 'PAID'
            """, [str(customer_id)])
            ctx['total_spending'] = _fmt_rp(cur.fetchone()[0])

            cur.execute("""
                SELECT t.ticket_code, e.event_title, e.event_datetime,
                       v.venue_name, tc.category_name
                FROM ticket t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                JOIN ticket_category tc ON t.tcategory_id = tc.category_id
                JOIN event e ON tc.tevent_id = e.event_id
                JOIN venue v ON e.venue_id = v.venue_id
                WHERE o.customer_id = %s AND e.event_datetime >= NOW()
                ORDER BY e.event_datetime
                LIMIT 5
            """, [str(customer_id)])
            tcols   = [c[0] for c in cur.description]
            tickets = [dict(zip(tcols, r)) for r in cur.fetchall()]
            for t in tickets:
                dt = t['event_datetime']
                if dt:
                    t['date_str'] = dt.strftime('%d %b %Y')
                    t['time_str'] = dt.strftime('%H:%M')
                del t['event_datetime']
            ctx['upcoming_tickets'] = tickets

    return render(request, 'dashboard.html', ctx)


# ─── PROFILE ─────────────────────────────────────────────────────────────────

@_login_required
def profile_view(request):
    role    = request.session.get('role', 'admin')
    user_id = request.session.get('user_id')
    ctx     = {'role': role}

    with connection.cursor() as cur:
        _sc(cur)
        cur.execute("SELECT username FROM user_account WHERE user_id = %s", [user_id])
        row = cur.fetchone()
        ctx['username'] = row[0] if row else ''

        if role == 'customer':
            cur.execute("""
                SELECT full_name, phone_number FROM customer WHERE user_id = %s
            """, [user_id])
            row = cur.fetchone()
            if row:
                ctx['full_name']    = row[0] or ''
                ctx['phone_number'] = row[1] or ''

        elif role == 'organizer':
            cur.execute("""
                SELECT organizer_name, contact_email FROM organizer WHERE user_id = %s
            """, [user_id])
            row = cur.fetchone()
            if row:
                ctx['organizer_name'] = row[0] or ''
                ctx['contact_email']  = row[1] or ''

    return render(request, 'profile.html', ctx)


@_login_required
def profile_update(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)
    try:
        data    = json.loads(request.body)
        role    = request.session.get('role')
        user_id = request.session.get('user_id')

        with connection.cursor() as cur:
            _sc(cur)
            if role == 'customer':
                full_name    = data.get('full_name', '').strip()
                phone_number = data.get('phone_number', '').strip()
                if not full_name:
                    return JsonResponse({'success': False, 'error': 'Nama lengkap wajib diisi!'})
                cur.execute("""
                    UPDATE customer SET full_name=%s, phone_number=%s WHERE user_id=%s
                """, [full_name, phone_number, user_id])
                request.session['full_name'] = full_name

            elif role == 'organizer':
                organizer_name = data.get('organizer_name', '').strip()
                contact_email  = data.get('contact_email', '').strip()
                if not organizer_name:
                    return JsonResponse({'success': False, 'error': 'Nama organizer wajib diisi!'})
                cur.execute("""
                    UPDATE organizer SET organizer_name=%s, contact_email=%s WHERE user_id=%s
                """, [organizer_name, contact_email, user_id])
                request.session['organizer_name'] = organizer_name

            else:
                return JsonResponse({'success': False, 'error': 'Admin tidak dapat mengubah profil.'})

        return JsonResponse({'success': True, 'message': 'Profil berhasil diperbarui!'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@_login_required
def profile_update_password(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak diizinkan.'}, status=405)
    try:
        data    = json.loads(request.body)
        user_id = request.session.get('user_id')
        old_pw  = data.get('old_password', '')
        new_pw  = data.get('new_password', '')
        confirm = data.get('confirm_password', '')

        if not all([old_pw, new_pw, confirm]):
            return JsonResponse({'success': False, 'error': 'Semua field password wajib diisi!'})
        if len(new_pw) < 6:
            return JsonResponse({'success': False, 'error': 'Password baru minimal 6 karakter!'})
        if new_pw != confirm:
            return JsonResponse({'success': False, 'error': 'Password baru dan konfirmasi tidak cocok!'})

        with connection.cursor() as cur:
            _sc(cur)
            cur.execute("SELECT password FROM user_account WHERE user_id = %s", [user_id])
            row = cur.fetchone()
            if not row or row[0] != old_pw:
                return JsonResponse({'success': False, 'error': 'Password lama tidak sesuai!'})
            cur.execute("UPDATE user_account SET password=%s WHERE user_id=%s", [new_pw, user_id])

        return JsonResponse({'success': True, 'message': 'Password berhasil diperbarui!'})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})