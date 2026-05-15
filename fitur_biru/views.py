import uuid
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.db import connection  # Pengganti psycopg2 manual
from django.utils import timezone

# ============================================================
# HELPER
# ============================================================
def _set_schema(cursor):
    """Mengatur schema agar selalu ke tiktaktuk."""
    cursor.execute("SET search_path TO tiktaktuk, public")

def get_user_role(request):
    return request.session.get('role', None)

def get_customer_id(request):
    return request.session.get('customer_id', None)

def get_organizer_id(request):
    return request.session.get('organizer_id', None)

def extract_trigger_message(exc):
    """Membersihkan pesan error dari PostgreSQL Trigger."""
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
        messages.error(request, "Akses ditolak.")
        return redirect('fitur_wajib:dashboard')

    with connection.cursor() as cursor:
        _set_schema(cursor)
        # Stats
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')      AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')    AS pending,
                COUNT(*) FILTER (WHERE payment_status = 'CANCELLED') AS dibatalkan
            FROM "ORDER" WHERE customer_id = %s
        """, (customer_id,))
        stats = cursor.fetchone()

        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        query = """
            SELECT order_id, order_date, payment_status, total_amount
            FROM "ORDER" WHERE customer_id = %s
        """
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
        cursor.execute(query, params)
        orders = cursor.fetchall()

    return render(request, 'read_order_cust.html', {
        'orders': orders, 'stats': stats,
        'search': search, 'status_filter': status_filter, 'role': role,
    })

# ============================================================
# 13 – C-ORDER (Checkout)
# ============================================================
def create_order(request, event_id):
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')

    role = get_user_role(request)
    customer_id = get_customer_id(request)

    if role != 'customer' or not customer_id:
        messages.error(request, "Hanya customer yang bisa membeli tiket.")
        return redirect('fitur_kuning:event_list')

    with connection.cursor() as cursor:
        _set_schema(cursor)
        
        # Ambil Info Event
        cursor.execute("""
            SELECT e.event_id, e.event_title, v.venue_name, e.event_datetime, e.description
            FROM EVENT e JOIN VENUE v ON v.venue_id = e.venue_id
            WHERE e.event_id = %s
        """, (str(event_id),))
        event = cursor.fetchone()

        # Ambil Sisa Kuota via SP
        cursor.execute("SELECT category_id, category_name, price, remaining FROM sp_sisa_kuota_biru(%s::uuid)", (str(event_id),))
        categories = cursor.fetchall()

        if request.method == 'POST':
            category_id = request.POST.get('category_id')
            qty = int(request.POST.get('qty', 1))
            promo_code = request.POST.get('promo_code', '').strip()

            selected_cat = next((c for c in categories if str(c[0]) == category_id), None)
            if not selected_cat or selected_cat[3] < qty:
                messages.error(request, "Kategori tidak valid atau kuota habis.")
                return redirect('fitur_biru:create_order', event_id=event_id)

            price_per_ticket = Decimal(str(selected_cat[2]))
            total_amount = price_per_ticket * qty
            promotion_id = None

            if promo_code:
                cursor.execute("SELECT promotion_id, discount_type, discount_value FROM PROMOTION WHERE promo_code = %s", (promo_code,))
                promo = cursor.fetchone()
                if promo:
                    promotion_id = promo[0]
                    disc_type, disc_val = promo[1], Decimal(str(promo[2]))
                    if disc_type == 'PERCENTAGE':
                        total_amount -= total_amount * (disc_val / 100)
                    else:
                        total_amount = max(total_amount - disc_val, Decimal('0'))

            try:
                order_id = uuid.uuid4()
                cursor.execute("""
                    INSERT INTO "ORDER" (order_id, order_date, payment_status, total_amount, customer_id)
                    VALUES (%s, NOW(), 'UNPAID', %s, %s)
                """, (str(order_id), total_amount, customer_id))

                if promotion_id:
                    cursor.execute("INSERT INTO ORDER_PROMOTION (order_promotion_id, promotion_id, order_id) VALUES (%s, %s, %s)", 
                                   (str(uuid.uuid4()), str(promotion_id), str(order_id)))

                for i in range(qty):
                    t_id = uuid.uuid4()
                    t_code = f"TTK-{str(order_id)[:8].upper()}-{i+1:03d}"
                    cursor.execute("INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id) VALUES (%s, %s, %s, %s)",
                                   (str(t_id), t_code, category_id, str(order_id)))

                messages.success(request, "Pesanan berhasil dibuat!")
                return redirect('fitur_biru:read_order_customer')

            except Exception as e:
                messages.error(request, extract_trigger_message(e))
                return redirect('fitur_biru:create_order', event_id=event_id)

    return render(request, 'create_order.html', {'event': event, 'categories': categories, 'role': role})

# ============================================================
# PEMBAYARAN & KONFIRMASI
# ============================================================
def confirm_payment(request, order_id):
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')

    with connection.cursor() as cursor:
        _set_schema(cursor)
        cursor.execute('SELECT payment_deadline, payment_status FROM "ORDER" WHERE order_id = %s', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return redirect('fitur_biru:read_order_customer')

        deadline, status = order[0], order[1]
        if deadline and timezone.is_naive(deadline):
            deadline = timezone.make_aware(deadline)
            
        if status == 'UNPAID':
            if timezone.now() > deadline:
                cursor.execute("UPDATE \"ORDER\" SET payment_status = 'CANCELLED' WHERE order_id = %s", (order_id,))
                messages.error(request, "Waktu pembayaran habis!")
            else:
                cursor.execute("UPDATE \"ORDER\" SET payment_status = 'PAID' WHERE order_id = %s", (order_id,))
                messages.success(request, "Pembayaran Berhasil!")
        
    return redirect('fitur_biru:read_order_customer')

# ============================================================
# 17 – PROMOTION (READ)
# ============================================================
def read_promotion(request):
    role = get_user_role(request)
    with connection.cursor() as cursor:
        _set_schema(cursor)
        cursor.execute("SELECT promo_code, discount_type, discount_value, start_date, end_date FROM PROMOTION")
        promotions = cursor.fetchall()

    templates = {'admin': 'CRUD_promo_admin.html', 'organizer': 'read_promo_organizer.html', 'customer': 'read_promo_cust.html'}
    return render(request, templates.get(role, 'read_promo_guest.html'), {'promotions': promotions, 'role': role})