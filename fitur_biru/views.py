import uuid
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.utils import timezone

# ============================================================
# HELPERS
# ============================================================
def _sp(cursor):
    """Set search_path ke schema tiktaktuk."""
    cursor.execute("SET search_path TO tiktaktuk, public")

def get_user_role(request):
    return request.session.get('role', None)

def get_customer_id(request):
    return request.session.get('customer_id', None)

def get_organizer_id(request):
    return request.session.get('organizer_id', None)

def extract_trigger_message(exc):
    """Membersihkan pesan error dari database/trigger."""
    msg = str(exc)
    if "ERROR:" in msg:
        return msg.split("ERROR:")[1].split("\n")[0].strip()
    return msg

# ============================================================
# 14 – R-ORDER (Customer)
# ============================================================
def read_order_customer(request):
    role = get_user_role(request)
    customer_id = get_customer_id(request)
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')
    if role != 'customer' or not customer_id:
        messages.error(request, "Akses ditolak. Khusus customer.")
        return redirect('fitur_wajib:dashboard')

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    with connection.cursor() as cur:
        _sp(cur)
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')      AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')    AS pending,
                COUNT(*) FILTER (WHERE payment_status = 'CANCELLED') AS dibatalkan
            FROM "ORDER" WHERE customer_id = %s
        """, [customer_id])
        stats = cur.fetchone()

        query = 'SELECT order_id, order_date, payment_status, total_amount FROM "ORDER" WHERE customer_id = %s'
        params = [customer_id]
        if search:
            query += " AND CAST(order_id AS TEXT) ILIKE %s"
            params.append(f'%{search}%')
        if status_filter != 'all':
            status_map = {'lunas': 'PAID', 'pending': 'UNPAID', 'dibatalkan': 'CANCELLED'}
            db_status = status_map.get(status_filter)
            if db_status:
                query += " AND payment_status = %s"
                params.append(db_status)
        query += " ORDER BY order_date DESC"
        cur.execute(query, params)
        orders = cur.fetchall()

    return render(request, 'read_order_cust.html', {
        'orders': orders, 'stats': stats,
        'search': search, 'status_filter': status_filter, 'role': role,
    })

# ============================================================
# 14 – R-ORDER (Organizer)
# ============================================================
def read_order_organizer(request):
    role = get_user_role(request)
    organizer_id = get_organizer_id(request)
    if not request.session.get('user_id') or role != 'organizer':
        messages.error(request, "Akses ditolak.")
        return redirect('fitur_wajib:dashboard')

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    with connection.cursor() as cur:
        _sp(cur)
        cur.execute("""
            SELECT
                COUNT(DISTINCT o.order_id) AS total,
                COUNT(DISTINCT o.order_id) FILTER (WHERE o.payment_status = 'PAID')   AS lunas,
                COUNT(DISTINCT o.order_id) FILTER (WHERE o.payment_status = 'UNPAID') AS pending,
                COALESCE(SUM(o.total_amount) FILTER (WHERE o.payment_status = 'PAID'), 0) AS revenue
            FROM "ORDER" o
            JOIN TICKET t ON t.torder_id = o.order_id
            JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
            JOIN EVENT e ON e.event_id = tc.tevent_id
            WHERE e.organizer_id = %s
        """, [organizer_id])
        stats = cur.fetchone()

        query = """
            SELECT DISTINCT o.order_id, c.full_name, o.order_date, o.payment_status, o.total_amount
            FROM "ORDER" o
            JOIN CUSTOMER c ON c.customer_id = o.customer_id
            JOIN TICKET t ON t.torder_id = o.order_id
            JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
            JOIN EVENT e ON e.event_id = tc.tevent_id
            WHERE e.organizer_id = %s
        """
        params = [organizer_id]
        if search:
            query += " AND (CAST(o.order_id AS TEXT) ILIKE %s OR c.full_name ILIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])
        if status_filter != 'all':
            status_map = {'lunas': 'PAID', 'pending': 'UNPAID', 'dibatalkan': 'CANCELLED'}
            db_status = status_map.get(status_filter)
            if db_status:
                query += " AND o.payment_status = %s"
                params.append(db_status)
        query += " ORDER BY o.order_date DESC"
        cur.execute(query, params)
        orders = cur.fetchall()

    return render(request, 'read_order_organizer.html', {
        'orders': orders, 'stats': stats,
        'search': search, 'status_filter': status_filter, 'role': role,
    })

# ============================================================
# 14/15 – R/UD-ORDER (Admin)
# ============================================================
def read_order_admin(request):
    if get_user_role(request) != 'admin':
        messages.error(request, "Akses ditolak. Admin only.")
        return redirect('fitur_wajib:dashboard')

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    with connection.cursor() as cur:
        _sp(cur)
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')      AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')    AS pending,
                COALESCE(SUM(total_amount) FILTER (WHERE payment_status = 'PAID'), 0) AS revenue
            FROM "ORDER"
        """)
        stats = cur.fetchone()

        query = """
            SELECT o.order_id, c.full_name, o.order_date, o.payment_status, o.total_amount
            FROM "ORDER" o
            JOIN CUSTOMER c ON c.customer_id = o.customer_id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (CAST(o.order_id AS TEXT) ILIKE %s OR c.full_name ILIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])
        if status_filter != 'all':
            status_map = {'lunas': 'PAID', 'pending': 'UNPAID', 'dibatalkan': 'CANCELLED'}
            db_status = status_map.get(status_filter)
            if db_status:
                query += " AND o.payment_status = %s"
                params.append(db_status)
        query += " ORDER BY o.order_date DESC"
        cur.execute(query, params)
        orders = cur.fetchall()

    return render(request, 'read_order_admin.html', {
        'orders': orders, 'stats': stats,
        'search': search, 'status_filter': status_filter, 'role': 'admin',
    })

def update_order_admin(request, order_id):
    if get_user_role(request) != 'admin': return redirect('fitur_wajib:dashboard')
    if request.method == 'POST':
        new_status = request.POST.get('payment_status')
        try:
            with connection.cursor() as cur:
                _sp(cur)
                cur.execute('UPDATE "ORDER" SET payment_status = %s WHERE order_id = %s', [new_status, order_id])
            messages.success(request, "Status order diperbarui.")
        except Exception as e:
            messages.error(request, f"Gagal update: {extract_trigger_message(e)}")
    return redirect('fitur_biru:read_order_admin')

def delete_order_admin(request, order_id):
    if get_user_role(request) != 'admin': return redirect('fitur_wajib:dashboard')
    if request.method == 'POST':
        try:
            with connection.cursor() as cur:
                _sp(cur)
                cur.execute('DELETE FROM ORDER_PROMOTION WHERE order_id = %s', [order_id])
                cur.execute('DELETE FROM TICKET WHERE torder_id = %s', [order_id])
                cur.execute('DELETE FROM "ORDER" WHERE order_id = %s', [order_id])
            messages.success(request, "Order dihapus.")
        except Exception as e:
            messages.error(request, f"Gagal hapus: {extract_trigger_message(e)}")
    return redirect('fitur_biru:read_order_admin')

# ============================================================
# 13 – C-ORDER (Customer) — Checkout
# ============================================================
def create_order(request, event_id):
    customer_id = get_customer_id(request)
    if get_user_role(request) != 'customer' or not customer_id:
        return redirect('fitur_kuning:event_list')

    with connection.cursor() as cur:
        _sp(cur)
        cur.execute("""
            SELECT e.event_id, e.event_title, v.venue_name, e.event_datetime, v.is_reserved
            FROM EVENT e JOIN VENUE v ON v.venue_id = e.venue_id WHERE e.event_id = %s
        """, [str(event_id)])
        event = cur.fetchone()

        cur.execute("SELECT category_id, category_name, price, remaining FROM sp_sisa_kuota_biru(%s::uuid)", [str(event_id)])
        categories = cur.fetchall()

        if request.method == 'POST':
            category_id = request.POST.get('category_id')
            qty = int(request.POST.get('qty', 1))
            promo_code = request.POST.get('promo_code', '').strip()

            try:
                # Logic kalkulasi harga simpel
                selected_cat = next((c for c in categories if str(c[0]) == category_id), None)
                total_amount = Decimal(str(selected_cat[2])) * qty
                promotion_id = None

                if promo_code:
                    cur.execute("SELECT promotion_id, discount_type, discount_value FROM PROMOTION WHERE promo_code = %s", [promo_code])
                    promo = cur.fetchone()
                    if promo:
                        promotion_id = promo[0]
                        disc_val = Decimal(str(promo[2]))
                        if promo[1] == 'PERCENTAGE':
                            total_amount -= total_amount * (disc_val / 100)
                        else:
                            total_amount = max(total_amount - disc_val, Decimal('0'))

                order_id = uuid.uuid4()
                cur.execute("""
                    INSERT INTO "ORDER" (order_id, order_date, payment_status, total_amount, customer_id)
                    VALUES (%s, NOW(), 'UNPAID', %s, %s)
                """, [str(order_id), total_amount, customer_id])

                if promotion_id:
                    cur.execute("INSERT INTO ORDER_PROMOTION (order_promotion_id, promotion_id, order_id) VALUES (%s, %s, %s)",
                                [str(uuid.uuid4()), str(promotion_id), str(order_id)])

                for i in range(qty):
                    cur.execute("INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id) VALUES (%s, %s, %s, %s)",
                                [str(uuid.uuid4()), f"TIX-{str(order_id)[:8].upper()}-{i}", category_id, str(order_id)])

                messages.success(request, "Pesanan berhasil!")
                return redirect('fitur_biru:read_order_customer')
            except Exception as e:
                messages.error(request, extract_trigger_message(e))

    return render(request, 'create_order.html', {'event': event, 'categories': categories, 'role': 'customer'})

# ============================================================
# 17 – R-PROMOTION (Semua role)
# ============================================================
def read_promotion(request):
    if not request.session.get('user_id'): return redirect('fitur_wajib:login')
    role = get_user_role(request)

    with connection.cursor() as cur:
        _sp(cur)
        cur.execute("SELECT promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit FROM PROMOTION")
        promotions = cur.fetchall()

    template = 'read_promo_cust.html'
    if role == 'admin': template = 'CRUD_promo_admin.html'
    elif role == 'organizer': template = 'read_promo_organizer.html'
    
    return render(request, template, {'promotions': promotions, 'role': role})

# ============================================================
# 16 – CUD-PROMOTION (Admin)
# ============================================================
def create_promotion(request):
    if get_user_role(request) != 'admin' or request.method != 'POST': return redirect('fitur_biru:read_promotion')
    data = request.POST
    try:
        with connection.cursor() as cur:
            _sp(cur)
            cur.execute("""
                INSERT INTO PROMOTION (promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [str(uuid.uuid4()), data['promo_code'], data['discount_type'].upper(), data['discount_value'], data['start_date'], data['end_date'], data['usage_limit']])
        messages.success(request, "Promo berhasil dibuat.")
    except Exception as e:
        messages.error(request, extract_trigger_message(e))
    return redirect('fitur_biru:read_promotion')

def delete_promotion(request, promotion_id):
    if get_user_role(request) != 'admin': return redirect('fitur_biru:read_promotion')
    try:
        with connection.cursor() as cur:
            _sp(cur)
            cur.execute('DELETE FROM PROMOTION WHERE promotion_id = %s', [promotion_id])
        messages.success(request, "Promo dihapus.")
    except Exception as e:
        messages.error(request, extract_trigger_message(e))
    return redirect('fitur_biru:read_promotion')

# ============================================================
# 15 – CONFIRM PAYMENT
# ============================================================
def confirm_payment(request, order_id):
    if not request.session.get('user_id'): return redirect('fitur_wajib:login')
    try:
        with connection.cursor() as cur:
            _sp(cur)
            cur.execute('SELECT payment_deadline, payment_status FROM "ORDER" WHERE order_id = %s', [order_id])
            order = cur.fetchone()
            if not order: return redirect('fitur_biru:read_order_customer')

            deadline = timezone.make_aware(order[0]) if timezone.is_naive(order[0]) else order[0]
            if order[1] == 'UNPAID':
                if timezone.now() > deadline:
                    cur.execute('UPDATE "ORDER" SET payment_status = \'CANCELLED\' WHERE order_id = %s', [order_id])
                    messages.error(request, "Waktu habis. Order dibatalkan.")
                else:
                    cur.execute('UPDATE "ORDER" SET payment_status = \'PAID\' WHERE order_id = %s', [order_id])
                    messages.success(request, "Pembayaran berhasil!")
            else:
                messages.info(request, f"Order sudah {order[1]}.")
    except Exception as e:
        messages.error(request, f"Gagal: {extract_trigger_message(e)}")
    return redirect('fitur_biru:read_order_customer')