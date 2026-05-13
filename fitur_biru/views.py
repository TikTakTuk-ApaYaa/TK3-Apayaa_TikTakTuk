import uuid
import psycopg2
from django.shortcuts import render, redirect
from django.contrib import messages

from django.conf import settings
from decimal import Decimal

# ============================================================
# HELPER: Get raw DB connection (Supabase / PostgreSQL)
# ============================================================
def get_db_conn():
    """
    Kembalikan koneksi psycopg2 ke Supabase menggunakan URL string langsung.
    """
    conn = psycopg2.connect(
        settings.DATABASE_URL_STRING,
        options="-c search_path=tiktaktuk"
    )
    return conn


def get_user_role(request):
    """Ambil role user yang sedang login dari session."""
    return request.session.get('role', None)


def get_customer_id(request):
    return request.session.get('customer_id', None)


def get_organizer_id(request):
    return request.session.get('organizer_id', None)


# ============================================================
# HELPER: tangkap pesan error dari trigger PostgreSQL
# ============================================================
def extract_trigger_message(exc):
    """
    psycopg2.errors.RaiseException menyimpan pesan di exc.diag.message_primary.
    Fallback ke str(exc) kalau atribut tidak ada.
    """
    try:
        return exc.diag.message_primary
    except AttributeError:
        return str(exc)


# ================================================================
#  14 – R-ORDER (Customer)
# ================================================================

def read_order_customer(request):
    role = get_user_role(request)
    customer_id = get_customer_id(request)

    if role != 'customer' or not customer_id:
        messages.error(request, "Akses ditolak.")
        return redirect('dashboard')

    conn = get_db_conn()
    try:
        cur = conn.cursor()

        # Statistik
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')       AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')     AS pending,
                COUNT(*) FILTER (WHERE payment_status = 'CANCELLED')  AS dibatalkan
            FROM "ORDER"
            WHERE customer_id = %s
        """, (customer_id,))
        stats = cur.fetchone()

        # Daftar order
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        query = """
            SELECT
                o.order_id,
                o.order_date,
                o.payment_status,
                o.total_amount
            FROM "ORDER" o
            WHERE o.customer_id = %s
        """
        params = [customer_id]

        if search:
            query += " AND CAST(o.order_id AS TEXT) ILIKE %s"
            params.append(f'%{search}%')

        if status_filter != 'all':
            status_map = {'lunas': 'PAID', 'pending': 'UNPAID', 'dibatalkan': 'CANCELLED'}
            db_status = status_map.get(status_filter)
            if db_status:
                query += " AND o.payment_status = %s"
                params.append(db_status)

        query += " ORDER BY o.order_date DESC"
        cur.execute(query, params)
        orders = cur.fetchall()

    finally:
        conn.close()

    return render(request, 'read_order_cust.html', {
        'orders': orders,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
    })


# ================================================================
#  14 – R-ORDER (Organizer)
# ================================================================

def read_order_organizer(request):
    role = get_user_role(request)
    organizer_id = get_organizer_id(request)

    if role != 'organizer' or not organizer_id:
        messages.error(request, "Akses ditolak.")
        return redirect('dashboard')

    conn = get_db_conn()
    try:
        cur = conn.cursor()

        # Statistik
        cur.execute("""
            SELECT
                COUNT(DISTINCT o.order_id)                                                       AS total,
                COUNT(DISTINCT o.order_id) FILTER (WHERE o.payment_status = 'PAID')             AS lunas,
                COUNT(DISTINCT o.order_id) FILTER (WHERE o.payment_status = 'UNPAID')           AS pending,
                COALESCE(SUM(o.total_amount) FILTER (WHERE o.payment_status = 'PAID'), 0)       AS revenue
            FROM "ORDER" o
            JOIN TICKET t       ON t.torder_id  = o.order_id
            JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
            JOIN EVENT e        ON e.event_id   = tc.tevent_id
            WHERE e.organizer_id = %s
        """, (organizer_id,))
        stats = cur.fetchone()

        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        query = """
            SELECT DISTINCT
                o.order_id,
                c.full_name     AS customer_name,
                o.order_date,
                o.payment_status,
                o.total_amount
            FROM "ORDER" o
            JOIN CUSTOMER c     ON c.customer_id = o.customer_id
            JOIN TICKET t       ON t.torder_id   = o.order_id
            JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
            JOIN EVENT e        ON e.event_id    = tc.tevent_id
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

    finally:
        conn.close()

    return render(request, 'read_order_organizer.html', {
        'orders': orders,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
    })


# ================================================================
#  14 – R-ORDER (Admin)  +  15 – UD-ORDER (Admin)
# ================================================================

def read_order_admin(request):
    role = get_user_role(request)
    if role != 'administrator':
        messages.error(request, "Akses ditolak.")
        return redirect('dashboard')

    conn = get_db_conn()
    try:
        cur = conn.cursor()

        # Statistik
        cur.execute("""
            SELECT
                COUNT(*)                                                              AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')                      AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')                    AS pending,
                COALESCE(SUM(total_amount) FILTER (WHERE payment_status = 'PAID'), 0) AS revenue
            FROM "ORDER"
        """)
        stats = cur.fetchone()

        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        query = """
            SELECT
                o.order_id,
                c.full_name     AS customer_name,
                o.order_date,
                o.payment_status,
                o.total_amount
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

    finally:
        conn.close()

    return render(request, 'read_order_admin.html', {
        'orders': orders,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
    })



def update_order_admin(request, order_id):
    """Update payment_status order — Admin only."""
    if get_user_role(request) != 'administrator':
        messages.error(request, "Akses ditolak.")
        return redirect('dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('payment_status')
        allowed = {'PAID', 'UNPAID', 'CANCELLED'}
        if new_status not in allowed:
            messages.error(request, "Status tidak valid.")
            return redirect('read_order_admin')

        conn = get_db_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                'UPDATE "ORDER" SET payment_status = %s WHERE order_id = %s',
                (new_status, order_id)
            )
            conn.commit()
            messages.success(request, "Status order berhasil diperbarui.")
        except Exception as e:
            conn.rollback()
            messages.error(request, f"Gagal update: {e}")
        finally:
            conn.close()

    return redirect('read_order_admin')



def delete_order_admin(request, order_id):
    """Delete order — Admin only."""
    if get_user_role(request) != 'administrator':
        messages.error(request, "Akses ditolak.")
        return redirect('dashboard')

    if request.method == 'POST':
        conn = get_db_conn()
        try:
            cur = conn.cursor()
            # Hapus ORDER_PROMOTION dulu (FK)
            cur.execute(
                'DELETE FROM ORDER_PROMOTION WHERE order_id = %s',
                (order_id,)
            )
            # Hapus HAS_RELATIONSHIP via TICKET
            cur.execute("""
                DELETE FROM HAS_RELATIONSHIP
                WHERE ticket_id IN (
                    SELECT ticket_id FROM TICKET WHERE torder_id = %s
                )
            """, (order_id,))
            # Hapus TICKET
            cur.execute('DELETE FROM TICKET WHERE torder_id = %s', (order_id,))
            # Hapus ORDER
            cur.execute('DELETE FROM "ORDER" WHERE order_id = %s', (order_id,))
            conn.commit()
            messages.success(request, "Order berhasil dihapus.")
        except Exception as e:
            conn.rollback()
            messages.error(request, f"Gagal hapus: {e}")
        finally:
            conn.close()

    return redirect('read_order_admin')


# ================================================================
#  13 – C-ORDER (Customer) — Checkout Tiket
# ================================================================

def create_order(request, event_id):
    """
    Halaman checkout tiket untuk Customer.
    Menampilkan info event + kategori tiket beserta sisa kuota
    (menggunakan stored procedure get_ticket_category_quota).
    """
    role = get_user_role(request)
    customer_id = get_customer_id(request)

    if role != 'customer' or not customer_id:
        messages.error(request, "Hanya Customer yang bisa membeli tiket.")
        return redirect('read_event')

    conn = get_db_conn()
    try:
        cur = conn.cursor()

        # Info event
        cur.execute("""
            SELECT e.event_id, e.event_title, v.venue_name, e.event_datetime,
                   e.description
            FROM EVENT e
            JOIN VENUE v ON v.venue_id = e.venue_id
            WHERE e.event_id = %s
        """, (event_id,))
        event = cur.fetchone()
        if not event:
            messages.error(request, "Event tidak ditemukan.")
            return redirect('read_event')

        # Sisa kuota per kategori — panggil stored procedure (YANG BENER & JOIN HARGA)
        cur.execute("""
            SELECT sp.category_id, sp.category_name, tc.price, sp.remaining
            FROM sp_sisa_kuota_event(%s) sp
            JOIN TICKET_CATEGORY tc ON tc.category_id = sp.category_id
        """, (str(event_id),))
        categories = cur.fetchall()
        # returns: (category_id, category_name, price, remaining_quota)

        if request.method == 'POST':
            category_id  = request.POST.get('category_id')
            qty          = int(request.POST.get('qty', 1))
            promo_code   = request.POST.get('promo_code', '').strip()

            if qty < 1 or qty > 10:
                messages.error(request, "Jumlah tiket harus antara 1–10.")
                conn.close()
                return redirect('create_order', event_id=event_id)

            # Harga dari kategori yang dipilih
            selected_cat = next((c for c in categories if str(c[0]) == category_id), None)
            if not selected_cat:
                messages.error(request, "Kategori tiket tidak valid.")
                conn.close()
                return redirect('create_order', event_id=event_id)

            price_per_ticket = Decimal(str(selected_cat[2]))
            total_amount     = price_per_ticket * qty

            # Terapkan promo jika ada — trigger akan validasi di server
            promotion_id = None
            if promo_code:
                cur.execute(
                    "SELECT promotion_id, discount_type, discount_value FROM PROMOTION WHERE promo_code = %s",
                    (promo_code,)
                )
                promo = cur.fetchone()
                if promo:
                    promotion_id = promo[0]
                    disc_type, disc_val = promo[1], Decimal(str(promo[2]))
                    if disc_type == 'PERCENTAGE':
                        total_amount -= total_amount * (disc_val / 100)
                    else:
                        total_amount = max(total_amount - disc_val, Decimal('0'))
                else:
                    messages.error(request, "Kode promo tidak valid.")
                    conn.close()
                    return redirect('create_order', event_id=event_id)

            total_amount = max(total_amount, Decimal('0'))

            try:
                order_id = uuid.uuid4()
                # INSERT ORDER — trigger check_promotion_before_order_promotion
                cur.execute("""
                    INSERT INTO "ORDER" (order_id, order_date, payment_status, total_amount, customer_id)
                    VALUES (%s, NOW(), 'UNPAID', %s, %s)
                """, (str(order_id), total_amount, customer_id))

                # INSERT ORDER_PROMOTION jika ada promo
                # Trigger validate_promotion_usage akan jalan di sini
                if promotion_id:
                    op_id = uuid.uuid4()
                    cur.execute("""
                        INSERT INTO ORDER_PROMOTION (order_promotion_id, promotion_id, order_id)
                        VALUES (%s, %s, %s)
                    """, (str(op_id), str(promotion_id), str(order_id)))

                # Buat tiket sejumlah qty
                # Trigger check_ticket_quota_before_insert akan jalan tiap INSERT
                for i in range(qty):
                    ticket_id   = uuid.uuid4()
                    ticket_code = f"TTK-{str(order_id)[:8].upper()}-{category_id[:4].upper()}-{i+1:03d}"
                    cur.execute("""
                        INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id)
                        VALUES (%s, %s, %s, %s)
                    """, (str(ticket_id), ticket_code, category_id, str(order_id)))

                conn.commit()
                messages.success(request, f"Pesanan berhasil dibuat! Order ID: {order_id}")
                return redirect('read_order_customer')

            except psycopg2.Error as e:
                conn.rollback()
                err_msg = extract_trigger_message(e)
                messages.error(request, err_msg)
                return redirect('create_order', event_id=event_id)

    finally:
        conn.close()

    return render(request, 'create_order.html', {
        'event': event,
        'categories': categories,
    })


# ================================================================
#  17 – R-PROMOTION  (Semua role + Guest)
# ================================================================
def read_promotion(request):
    """
    Semua pengguna (termasuk guest) bisa lihat daftar promosi.
    Admin mendapatkan tombol aksi CUD.
    """
    conn = get_db_conn()
    try:
        cur = conn.cursor()

        # Statistik
        cur.execute("""
            SELECT
                COUNT(*) AS total_promo,
                COALESCE(SUM(
                    (SELECT COUNT(*) FROM ORDER_PROMOTION op WHERE op.promotion_id = p.promotion_id)
                ), 0) AS total_usage,
                COUNT(*) FILTER (WHERE p.discount_type = 'PERCENTAGE') AS total_persen
            FROM PROMOTION p
        """)
        stats = cur.fetchone()

        search = request.GET.get('search', '')
        type_filter = request.GET.get('type', 'all')

        query = """
            SELECT
                p.promotion_id,
                p.promo_code,
                p.discount_type,
                p.discount_value,
                p.start_date,
                p.end_date,
                p.usage_limit,
                (SELECT COUNT(*) FROM ORDER_PROMOTION op WHERE op.promotion_id = p.promotion_id) AS used_count
            FROM PROMOTION p
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND p.promo_code ILIKE %s"
            params.append(f'%{search}%')

        if type_filter != 'all':
            type_map = {'persentase': 'PERCENTAGE', 'nominal': 'NOMINAL'}
            db_type = type_map.get(type_filter)
            if db_type:
                query += " AND p.discount_type = %s"
                params.append(db_type)

        query += " ORDER BY p.promo_code ASC"
        cur.execute(query, params)
        promotions = cur.fetchall()

    finally:
        conn.close()

    role = get_user_role(request)
    template = 'CRUD_promo_admin.html' if role == 'administrator' else (
        'read_promo_organizer.html' if role == 'organizer' else
        'read_promo_guest.html'
    )
    # customer dan guest pakai template yang sama
    if role == 'customer':
        template = 'read_promo_cust.html'

    return render(request, template, {
        'promotions': promotions,
        'stats': stats,
        'search': search,
        'type_filter': type_filter,
    })


# ================================================================
#  16 – CUD-PROMOTION  (Admin only)
# ================================================================

def create_promotion(request):
    if get_user_role(request) != 'administrator':
        messages.error(request, "Akses ditolak.")
        return redirect('read_promotion')

    if request.method == 'POST':
        promo_code    = request.POST.get('promo_code', '').strip()
        discount_type = request.POST.get('discount_type', '').upper()
        discount_value = request.POST.get('discount_value')
        start_date    = request.POST.get('start_date')
        end_date      = request.POST.get('end_date')
        usage_limit   = request.POST.get('usage_limit')

        # Validasi basic
        if not all([promo_code, discount_type, discount_value, start_date, end_date, usage_limit]):
            messages.error(request, "Semua field wajib diisi.")
            return redirect('read_promotion')

        if discount_type not in ('NOMINAL', 'PERCENTAGE'):
            messages.error(request, "Tipe diskon tidak valid.")
            return redirect('read_promotion')

        if end_date < start_date:
            messages.error(request, "Tanggal berakhir harus >= tanggal mulai.")
            return redirect('read_promotion')

        conn = get_db_conn()
        try:
            cur = conn.cursor()
            promo_id = uuid.uuid4()
            cur.execute("""
                INSERT INTO PROMOTION
                    (promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (str(promo_id), promo_code, discount_type,
                  discount_value, start_date, end_date, usage_limit))
            conn.commit()
            messages.success(request, f"Promosi '{promo_code}' berhasil dibuat.")
        except psycopg2.Error as e:
            conn.rollback()
            messages.error(request, extract_trigger_message(e))
        finally:
            conn.close()

    return redirect('read_promotion')



def update_promotion(request, promotion_id):
    if get_user_role(request) != 'administrator':
        messages.error(request, "Akses ditolak.")
        return redirect('read_promotion')

    if request.method == 'POST':
        promo_code    = request.POST.get('promo_code', '').strip()
        discount_type = request.POST.get('discount_type', '').upper()
        discount_value = request.POST.get('discount_value')
        start_date    = request.POST.get('start_date')
        end_date      = request.POST.get('end_date')
        usage_limit   = request.POST.get('usage_limit')

        if not all([promo_code, discount_type, discount_value, start_date, end_date, usage_limit]):
            messages.error(request, "Semua field wajib diisi.")
            return redirect('read_promotion')

        if end_date < start_date:
            messages.error(request, "Tanggal berakhir harus >= tanggal mulai.")
            return redirect('read_promotion')

        conn = get_db_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE PROMOTION
                SET promo_code = %s, discount_type = %s, discount_value = %s,
                    start_date = %s, end_date = %s, usage_limit = %s
                WHERE promotion_id = %s
            """, (promo_code, discount_type, discount_value,
                  start_date, end_date, usage_limit, promotion_id))
            conn.commit()
            messages.success(request, "Promosi berhasil diperbarui.")
        except psycopg2.Error as e:
            conn.rollback()
            messages.error(request, extract_trigger_message(e))
        finally:
            conn.close()

    return redirect('read_promotion')



def delete_promotion(request, promotion_id):
    if get_user_role(request) != 'administrator':
        messages.error(request, "Akses ditolak.")
        return redirect('read_promotion')

    if request.method == 'POST':
        conn = get_db_conn()
        try:
            cur = conn.cursor()
            # Hapus ORDER_PROMOTION dulu karena FK
            cur.execute('DELETE FROM ORDER_PROMOTION WHERE promotion_id = %s', (promotion_id,))
            cur.execute('DELETE FROM PROMOTION WHERE promotion_id = %s', (promotion_id,))
            conn.commit()
            messages.success(request, "Promosi berhasil dihapus.")
        except psycopg2.Error as e:
            conn.rollback()
            messages.error(request, extract_trigger_message(e))
        finally:
            conn.close()

    return redirect('read_promotion')