
import uuid
from django.db import connection
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
from django.utils import timezone


# ============================================================
# HELPER
# ============================================================
def _sp(cursor):
    """Set search_path ke schema tiktaktuk."""
    cursor.execute("SET search_path TO tiktaktuk")

def get_user_role(request):
    return request.session.get('role', None)

def get_customer_id(request):
    return request.session.get('customer_id', None)

def get_organizer_id(request):
    return request.session.get('organizer_id', None)

def extract_trigger_message(exc):
    """
    Membersihkan pesan error dari database/trigger.
    Menghilangkan bagian 'CONTEXT', 'PL/pgSQL line...', dll.
    """
    msg = str(exc)
    
    # 1. Kalau ada kata 'ERROR:', ambil setelahnya
    if "ERROR:" in msg:
        msg = msg.split("ERROR:")[1]
    
    # 2. Buang bagian CONTEXT dan seterusnya (biasanya dipisah baris baru)
    if "CONTEXT:" in msg:
        msg = msg.split("CONTEXT:")[0]
        
    # 3. Buang bagian 'at line ...' atau 'line ...' jika masih nyangkut
    if "line " in msg:
        msg = msg.split("line ")[0]

    # 4. Bersihkan spasi atau karakter aneh di ujung-ujung
    return msg.strip()


# ============================================================
# 14 – R-ORDER (Customer)
# ============================================================
def read_order_customer(request):
    role = get_user_role(request)
    customer_id = get_customer_id(request)
    
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')
    if role != 'customer' or not customer_id:
        messages.error(request, "Akses ditolak. Hanya customer yang bisa melihat pesanan.")
        return redirect('fitur_wajib:dashboard')

    # Ambil input search & filter di luar blok cursor biar rapi
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    # Buka koneksi
    with connection.cursor() as cur:
        _sp(cur) # 1. Set Search Path (WAJIB di dalem with)
        
        # 2. Query Stats (Harus menjorok ke dalem)
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')      AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')    AS pending,
                COUNT(*) FILTER (WHERE payment_status = 'CANCELLED') AS dibatalkan
            FROM "ORDER" WHERE customer_id = %s
        """, [customer_id])
        stats = cur.fetchone()

        # 3. Bangun Query List
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
        
        # 4. Eksekusi Query List (Harus menjorok ke dalem juga)
        cur.execute(query, params)
        orders = cur.fetchall()

    # Baru setelah dapet data (orders & stats), kita render HTML
    return render(request, 'read_order_cust.html', {
        'orders': orders, 
        'stats': stats,
        'search': search, 
        'status_filter': status_filter,
        'role': role,
    })


# ============================================================
# 14 – R-ORDER (Organizer)
# ============================================================
def read_order_organizer(request):
    role = get_user_role(request)
    organizer_id = get_organizer_id(request)
    
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')
    if role != 'organizer' or not organizer_id:
        messages.error(request, "Akses ditolak.")
        return redirect('fitur_wajib:dashboard')

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    with connection.cursor() as cur:
        _sp(cur) # 1. Masuk ke dalam 'with'
        
        # 2. Query Stats (Masuk ke dalam 'with')
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

        # 3. Bangun Query List
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

        # 4. Eksekusi Query List (WAJIB menjorok ke dalam 'with')
        cur.execute(query, params)
        orders = cur.fetchall()

    # Baru render setelah blok 'with' selesai
    return render(request, 'read_order_organizer.html', {
        'orders': orders, 
        'stats': stats,
        'search': search, 
        'status_filter': status_filter,
        'role': role,
    })

# ============================================================
# 14/15 – R/UD-ORDER (Admin)
# ============================================================
def read_order_admin(request):
    role = get_user_role(request)
    
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')
    
    if role != 'admin': 
        messages.error(request, f"Role kamu {role}, butuh administrator.")
        return redirect('fitur_wajib:dashboard')

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    # BUKA KONEKSI
    with connection.cursor() as cur:
        _sp(cur) # SETELAH INI, SEMUA HARUS MASUK KE DALAM (TAB)
        
        # 1. Query Stats
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')      AS lunas,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')    AS pending,
                COALESCE(SUM(total_amount) FILTER (WHERE payment_status = 'PAID'), 0) AS revenue
            FROM "ORDER"
        """)
        stats = cur.fetchone()

        # 2. Bangun Query List
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
        
        # 3. Jalankan Query List
        cur.execute(query, params)
        orders = cur.fetchall()
        # AKHIR DARI BLOK WITH (Koneksi otomatis tutup di sini)

    # BARU RENDER
    return render(request, 'read_order_admin.html', {
        'orders': orders, 
        'stats': stats,
        'search': search, 
        'status_filter': status_filter,
        'role': role,
    })


def update_order_admin(request, order_id):
    # 1. Cek Login & Role
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')
    
    if get_user_role(request) != 'admin':
        messages.error(request, "Akses ditolak.")
        return redirect('fitur_wajib:dashboard')

    # 2. Cek Method POST
    if request.method == 'POST':
        new_status = request.POST.get('payment_status')
        
        # Validasi status agar tidak asal input
        if new_status not in {'PAID', 'UNPAID', 'CANCELLED'}:
            messages.error(request, "Status tidak valid.")
            return redirect('fitur_biru:read_order_admin')

        try:
            # 3. Eksekusi Query (Pake gaya Django Native)
            with connection.cursor() as cur:
                _sp(cur) # Set search path ke schema lo
                cur.execute(
                    'UPDATE "ORDER" SET payment_status = %s WHERE order_id = %s',
                    [new_status, order_id]
                )
                
                # Cek apakah ada baris yang terupdate
                if cur.rowcount == 0:
                    messages.warning(request, "Data order tidak ditemukan.")
                else:
                    messages.success(request, f"Status order {order_id} berhasil diubah jadi {new_status}.")
        
        except Exception as e:
            # Pake helper extract_trigger_message yang udah kita bahas tadi
            messages.error(request, f"Gagal update: {extract_trigger_message(e)}")
            
    return redirect('fitur_biru:read_order_admin')


def delete_order_admin(request, order_id):
    # 1. Cek Login & Role
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')
    
    if get_user_role(request) != 'admin':
        messages.error(request, "Akses ditolak.")
        return redirect('fitur_wajib:dashboard')

    if request.method == 'POST':
        try:
            # 2. Pake with connection.cursor() (Native Django)
            with connection.cursor() as cur:
                _sp(cur) # Set schema tiktaktuk
                
                # 3. Hapus data berelasi (Manual Cascade)
                cur.execute('DELETE FROM ORDER_PROMOTION WHERE order_id = %s', [order_id])
                
                cur.execute("""
                    DELETE FROM HAS_RELATIONSHIP
                    WHERE ticket_id IN (SELECT ticket_id FROM TICKET WHERE torder_id = %s)
                """, [order_id])
                
                cur.execute('DELETE FROM TICKET WHERE torder_id = %s', [order_id])
                
                # 4. Hapus order utama
                cur.execute('DELETE FROM "ORDER" WHERE order_id = %s', [order_id])
                
                # Gak perlu conn.commit() kalau pake 'with', otomatis dihandle Django
                messages.success(request, f"Order {order_id} berhasil dihapus.")
                
        except Exception as e:
            # Gak perlu conn.rollback() manual
            messages.error(request, f"Gagal hapus: {extract_trigger_message(e)}")

    return redirect('fitur_biru:read_order_admin')

# ============================================================
# 13 – C-ORDER (Customer) — Checkout
# ============================================================
def create_order(request, event_id):
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')

    role = get_user_role(request)
    customer_id = get_customer_id(request)

    if role != 'customer' or not customer_id:
        messages.error(request, "Hanya customer yang bisa membeli tiket.")
        return redirect('fitur_kuning:event_list')

    # Buka koneksi pake gaya Django Native
    with connection.cursor() as cur:
        _sp(cur) # Set search path biar bisa baca table ORDER, EVENT, dll.

        # 1. Ambil Info Event
        cur.execute("""
            SELECT e.event_id, e.event_title, v.venue_name, e.event_datetime,
                   e.description, v.is_reserved
            FROM EVENT e
            JOIN VENUE v ON v.venue_id = e.venue_id
            WHERE e.event_id = %s
        """, [str(event_id)])
        event = cur.fetchone()
        
        if not event:
            messages.error(request, "Event tidak ditemukan.")
            return redirect('fitur_kuning:event_list')

        # 2. Ambil Sisa Kuota via Stored Procedure
        # Gunakan schema prefix tiktaktuk langsung di nama fungsinya
        cur.execute("""
            SELECT 
                sp.category_id, 
                sp.category_name, 
                tc.price,          -- Kita ambil harga dari tabel asli (TICKET_CATEGORY)
                sp.remaining       -- Sisa kuota dari Stored Procedure
            FROM tiktaktuk.sp_sisa_kuota_biru(%s::uuid) sp
            JOIN tiktaktuk.TICKET_CATEGORY tc ON tc.category_id = sp.category_id
        """, [str(event_id)])
        categories = cur.fetchall()

        if request.method == 'POST':
            category_id = request.POST.get('category_id')
            qty         = int(request.POST.get('qty', 1))
            promo_code  = request.POST.get('promo_code', '').strip()

            # Validasi Input Sederhana
            if qty < 1 or qty > 10:
                messages.error(request, "Jumlah tiket harus antara 1–10.")
                return redirect('fitur_biru:create_order', event_id=event_id)

            selected_cat = next((c for c in categories if str(c[0]) == category_id), None)
            if not selected_cat:
                messages.error(request, "Kategori tiket tidak valid.")
                return redirect('fitur_biru:create_order', event_id=event_id)

            if selected_cat[3] < qty:
                messages.error(request, f"Kuota tidak cukup. Sisa: {selected_cat[3]} tiket.")
                return redirect('fitur_biru:create_order', event_id=event_id)

            # 3. Hitung Harga & Promo
            price_per_ticket = Decimal(str(selected_cat[2]))
            total_amount     = price_per_ticket * qty
            promotion_id     = None

            if promo_code:
                cur.execute("SELECT promotion_id, discount_type, discount_value FROM PROMOTION WHERE promo_code = %s", [promo_code])
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
                    return redirect('fitur_biru:create_order', event_id=event_id)

            total_amount = max(total_amount, Decimal('0'))

            # 4. Proses Insert (Dibungkus Try-Except untuk nangkep Trigger)
            try:
                order_id = uuid.uuid4()
                # Insert ke tabel ORDER (pakai double quote karena ORDER itu reserved keyword)
                cur.execute("""
                    INSERT INTO "ORDER" (order_id, order_date, payment_status, total_amount, customer_id)
                    VALUES (%s, NOW(), 'UNPAID', %s, %s)
                """, [str(order_id), total_amount, customer_id])

                if promotion_id:
                    cur.execute("""
                        INSERT INTO ORDER_PROMOTION (order_promotion_id, promotion_id, order_id)
                        VALUES (%s, %s, %s)
                    """, [str(uuid.uuid4()), str(promotion_id), str(order_id)])

                # Insert Tiket sesuai Quantity
                for i in range(qty):
                    t_id = uuid.uuid4()
                    t_code = f"TTK-{str(order_id)[:8].upper()}-{i+1:03d}"
                    cur.execute("""
                        INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id)
                        VALUES (%s, %s, %s, %s)
                    """, [str(t_id), t_code, category_id, str(order_id)])

                messages.success(request, f"Pesanan berhasil! Order ID: {str(order_id)[:8].upper()}")
                return redirect('fitur_biru:read_order_customer')

            except Exception as e:
                # Nangkep error dari trigger (misal: "Tiket sudah habis" atau "Promo expired")
                messages.error(request, extract_trigger_message(e))
                return redirect('fitur_biru:create_order', event_id=event_id)

    # Render halaman checkout
    return render(request, 'create_order.html', {
        'event': event,
        'categories': categories,
        'role': role,
    })

# ============================================================
# 17 – R-PROMOTION (Semua role)
# ============================================================
def read_promotion(request):
    # 1. Cek Login
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')

    search      = request.GET.get('search', '')
    type_filter = request.GET.get('type', 'all')
    role        = get_user_role(request)

    # 2. Buka Koneksi
    with connection.cursor() as cur:
        _sp(cur) # Set search_path

        # 3. Query Stats
        cur.execute("""
            SELECT
                COUNT(*) AS total_promo,
                COALESCE((SELECT COUNT(*) FROM ORDER_PROMOTION), 0) AS total_usage,
                COUNT(*) FILTER (WHERE discount_type = 'PERCENTAGE') AS total_persen
            FROM PROMOTION
        """)
        stats = cur.fetchone()

        # 4. Bangun Query List Promotion
        query = """
            SELECT
                p.promotion_id, p.promo_code, p.discount_type, p.discount_value,
                p.start_date, p.end_date, p.usage_limit,
                (SELECT COUNT(*) FROM ORDER_PROMOTION op WHERE op.promotion_id = p.promotion_id) AS used_count
            FROM PROMOTION p WHERE 1=1
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
        
        # 5. Eksekusi Query (Pastikan menjorok ke dalam blok 'with')
        cur.execute(query, params)
        promotions = cur.fetchall()

    # 6. Tentukan Template Berdasarkan Role
    if role == 'admin':                    
        template = 'CRUD_promo_admin.html'
    elif role == 'organizer':
        template = 'read_promo_organizer.html'
    elif role == 'customer':
        template = 'read_promo_cust.html'
    else:
        template = 'read_promo_guest.html'

    return render(request, template, {
        'promotions': promotions, 
        'stats': stats,
        'search': search, 
        'type_filter': type_filter,
        'role': role,
    })

# ============================================================
# 16 – CUD-PROMOTION (Admin)
# ============================================================

def create_promotion(request):
    if get_user_role(request) != 'admin':  
        messages.error(request, "Akses ditolak.")
        return redirect('fitur_biru:read_promotion')

    if request.method == 'POST':
        data = request.POST
        try:
            with connection.cursor() as cur:
                _sp(cur)
                cur.execute("""
                    INSERT INTO PROMOTION
                        (promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [str(uuid.uuid4()), data['promo_code'], data['discount_type'].upper(),
                      data['discount_value'], data['start_date'], data['end_date'], data['usage_limit']])
            messages.success(request, f"Promosi '{data['promo_code']}' berhasil dibuat.")
        except Exception as e:
            messages.error(request, extract_trigger_message(e))
    return redirect('fitur_biru:read_promotion')

def update_promotion(request, promotion_id):
    if get_user_role(request) != 'admin':  
        return redirect('fitur_biru:read_promotion')

    if request.method == 'POST':
        data = request.POST
        try:
            with connection.cursor() as cur:
                _sp(cur)
                cur.execute("""
                    UPDATE PROMOTION
                    SET promo_code=%s, discount_type=%s, discount_value=%s,
                        start_date=%s, end_date=%s, usage_limit=%s
                    WHERE promotion_id=%s
                """, [data['promo_code'], data['discount_type'].upper(), data['discount_value'],
                      data['start_date'], data['end_date'], data['usage_limit'], promotion_id])
            messages.success(request, "Promosi berhasil diperbarui.")
        except Exception as e:
            messages.error(request, extract_trigger_message(e))
    return redirect('fitur_biru:read_promotion')

def delete_promotion(request, promotion_id):
    if get_user_role(request) != 'admin':  
        return redirect('fitur_biru:read_promotion')

    if request.method == 'POST':
        try:
            with connection.cursor() as cur:
                _sp(cur)
                # Hapus relasi dulu baru parent-nya
                cur.execute('DELETE FROM ORDER_PROMOTION WHERE promotion_id = %s', [promotion_id])
                cur.execute('DELETE FROM PROMOTION WHERE promotion_id = %s', [promotion_id])
            messages.success(request, "Promosi berhasil dihapus.")
        except Exception as e:
            messages.error(request, extract_trigger_message(e))
    return redirect('fitur_biru:read_promotion')

# ============================================================
# 15 – CONFIRM PAYMENT
# ============================================================

def confirm_payment(request, order_id):
    if not request.session.get('user_id'):
        return redirect('fitur_wajib:login')

    try:
        with connection.cursor() as cur:
            _sp(cur)
            # 1. Ambil data (pakai double quote "ORDER" karena reserved keyword)
            cur.execute('SELECT payment_deadline, payment_status FROM "ORDER" WHERE order_id = %s', [order_id])
            order = cur.fetchone()
            
            if not order:
                messages.error(request, "Order tidak ditemukan.")
                return redirect('fitur_biru:read_order_customer')

            deadline, status = order[0], order[1]
            
            # Handle timezone biar gak error comparison
            if deadline and timezone.is_naive(deadline):
                deadline = timezone.make_aware(deadline)
            
            if status == 'UNPAID':
                if timezone.now() > deadline:
                    cur.execute('UPDATE "ORDER" SET payment_status = \'CANCELLED\' WHERE order_id = %s', [order_id])
                    messages.error(request, "Waktu habis (30 detik). Order dibatalkan otomatis.")
                else:
                    cur.execute('UPDATE "ORDER" SET payment_status = \'PAID\' WHERE order_id = %s', [order_id])
                    messages.success(request, "Pembayaran berhasil dikonfirmasi!")
            else:
                messages.info(request, f"Order sudah berstatus {status}.")
                
    except Exception as e:
        messages.error(request, f"Gagal konfirmasi: {extract_trigger_message(e)}")

    return redirect('fitur_biru:read_order_customer')