import json
import uuid
from functools import wraps

from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt


def _schema(cursor):
    cursor.execute("SET search_path TO tiktaktuk;")


def _login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("user_id"):
            return redirect("fitur_wajib:login")
        return fn(request, *args, **kwargs)
    return wrapper


def _api_login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("user_id"):
            return JsonResponse({"error": "Silakan login terlebih dahulu."}, status=401)
        return fn(request, *args, **kwargs)
    return wrapper


def _can_manage(role):
    return role in ("admin", "organizer")


def _clean_db_error(exc):
    msg = str(exc)
    for line in msg.splitlines():
        line = line.strip()
        if line and not any(line.startswith(x) for x in ["LINE", "^", "QUERY", "CONTEXT"]):
            if ":" in line:
                parts = line.split(":", 1)
                if parts[0].strip().upper() == "ERROR":
                    return parts[1].strip()
            return line
    return msg or "Terjadi kesalahan database."


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _ticket_scope_sql(role, customer_id=None, organizer_id=None, alias="e"):
    if role == "customer" and customer_id:
        return " AND o.customer_id = %s", [customer_id]
    if role == "organizer" and organizer_id:
        return f" AND {alias}.organizer_id = %s", [organizer_id]
    return "", []


@_login_required
def seat_management(request):
    return render(request, "seat-main.html", {"role": request.session.get("role", "guest")})


@_login_required
def ticket_management(request):
    return render(request, "ticket-main.html", {"role": request.session.get("role", "guest")})


@csrf_exempt
@_api_login_required
def api_seats(request):
    role = request.session.get("role", "guest")

    if request.method == "GET":
        q = request.GET.get("q", "").strip()
        venue_id = request.GET.get("venue_id", "").strip()

        sql = """
            SELECT s.seat_id, s.section, s.row_number, s.seat_number,
                   s.venue_id, v.venue_name,
                   CASE WHEN COUNT(hr.ticket_id) > 0 THEN TRUE ELSE FALSE END AS is_assigned
            FROM seat s
            JOIN venue v ON v.venue_id = s.venue_id
            LEFT JOIN has_relationship hr ON hr.seat_id = s.seat_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += """
                AND (
                    s.section ILIKE %s OR s.row_number ILIKE %s OR
                    s.seat_number ILIKE %s OR v.venue_name ILIKE %s
                )
            """
            params.extend([f"%{q}%"] * 4)
        if venue_id:
            sql += " AND s.venue_id = %s"
            params.append(venue_id)
        sql += """
            GROUP BY s.seat_id, s.section, s.row_number, s.seat_number, s.venue_id, v.venue_name
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
        """

        with connection.cursor() as cur:
            _schema(cur)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.execute("SELECT venue_id, venue_name FROM venue ORDER BY venue_name")
            venues = [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]

        seats = [
            {
                "id": str(r[0]),
                "section": r[1],
                "row": r[2],
                "number": r[3],
                "venue_id": str(r[4]),
                "venue_name": r[5],
                "is_assigned": bool(r[6]),
            }
            for r in rows
        ]
        return JsonResponse({
            "seats": seats,
            "venues": venues,
            "stats": {
                "total": len(seats),
                "available": sum(1 for seat in seats if not seat["is_assigned"]),
                "filled": sum(1 for seat in seats if seat["is_assigned"]),
            },
            "can_manage": _can_manage(role),
        })

    if request.method == "POST":
        if not _can_manage(role):
            return JsonResponse({"error": "Akses ditolak."}, status=403)

        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        venue_id = body.get("venue_id", "").strip()
        section = body.get("section", "").strip()
        row_number = body.get("row_number", "").strip()
        seat_number = body.get("seat_number", "").strip()

        if not all([venue_id, section, row_number, seat_number]):
            return JsonResponse({"error": "Venue, section, baris, dan nomor kursi wajib diisi."}, status=400)

        try:
            with transaction.atomic(), connection.cursor() as cur:
                _schema(cur)
                cur.execute("SELECT 1 FROM venue WHERE venue_id = %s", [venue_id])
                if not cur.fetchone():
                    return JsonResponse({"error": "Venue tidak ditemukan."}, status=404)
                cur.execute(
                    """
                    SELECT 1 FROM seat
                    WHERE venue_id=%s AND LOWER(section)=LOWER(%s)
                      AND LOWER(row_number)=LOWER(%s) AND LOWER(seat_number)=LOWER(%s)
                    """,
                    [venue_id, section, row_number, seat_number],
                )
                if cur.fetchone():
                    return JsonResponse({"error": "Kursi dengan venue, section, baris, dan nomor tersebut sudah ada."}, status=400)

                seat_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO seat (seat_id, section, seat_number, row_number, venue_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [seat_id, section, seat_number, row_number, venue_id],
                )
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Kursi berhasil ditambahkan.", "id": seat_id}, status=201)

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
@_api_login_required
def api_seat_detail(request, seat_id):
    role = request.session.get("role", "guest")
    if not _can_manage(role):
        return JsonResponse({"error": "Akses ditolak."}, status=403)

    if request.method == "PUT":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        venue_id = body.get("venue_id", "").strip()
        section = body.get("section", "").strip()
        row_number = body.get("row_number", "").strip()
        seat_number = body.get("seat_number", "").strip()

        if not all([venue_id, section, row_number, seat_number]):
            return JsonResponse({"error": "Venue, section, baris, dan nomor kursi wajib diisi."}, status=400)

        try:
            with transaction.atomic(), connection.cursor() as cur:
                _schema(cur)
                cur.execute(
                    """
                    SELECT s.venue_id, COUNT(hr.ticket_id)
                    FROM seat s
                    LEFT JOIN has_relationship hr ON hr.seat_id = s.seat_id
                    WHERE s.seat_id = %s
                    GROUP BY s.venue_id
                    """,
                    [str(seat_id)],
                )
                row = cur.fetchone()
                if not row:
                    return JsonResponse({"error": "Kursi tidak ditemukan."}, status=404)
                if row[1] and str(row[0]) != venue_id:
                    return JsonResponse({"error": "Kursi yang sudah dipakai tiket tidak boleh dipindahkan ke venue lain."}, status=400)

                cur.execute(
                    """
                    SELECT 1 FROM seat
                    WHERE seat_id <> %s AND venue_id=%s AND LOWER(section)=LOWER(%s)
                      AND LOWER(row_number)=LOWER(%s) AND LOWER(seat_number)=LOWER(%s)
                    """,
                    [str(seat_id), venue_id, section, row_number, seat_number],
                )
                if cur.fetchone():
                    return JsonResponse({"error": "Kursi dengan venue, section, baris, dan nomor tersebut sudah ada."}, status=400)

                cur.execute(
                    """
                    UPDATE seat
                    SET venue_id=%s, section=%s, row_number=%s, seat_number=%s
                    WHERE seat_id=%s
                    """,
                    [venue_id, section, row_number, seat_number, str(seat_id)],
                )
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Kursi berhasil diperbarui."})

    if request.method == "DELETE":
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _schema(cur)
                cur.execute("SELECT COUNT(*) FROM has_relationship WHERE seat_id = %s", [str(seat_id)])
                if cur.fetchone()[0] > 0:
                    return JsonResponse({"error": "Kursi sudah dipakai tiket sehingga tidak dapat dihapus."}, status=400)
                cur.execute("DELETE FROM seat WHERE seat_id = %s", [str(seat_id)])
                if cur.rowcount == 0:
                    return JsonResponse({"error": "Kursi tidak ditemukan."}, status=404)
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Kursi berhasil dihapus."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
@_api_login_required
def api_tickets(request):
    role = request.session.get("role", "guest")
    customer_id = request.session.get("customer_id")
    organizer_id = request.session.get("organizer_id")

    if request.method == "GET":
        q = request.GET.get("q", "").strip()
        status = request.GET.get("status", "").strip()

        scope_sql, scope_params = _ticket_scope_sql(role, customer_id, organizer_id)
        sql = f"""
            SELECT t.ticket_id, t.ticket_code, t.tcategory_id, tc.category_name,
                   tc.price, t.torder_id, o.payment_status, o.customer_id, c.full_name,
                   e.event_id, e.event_title, e.event_datetime, v.venue_id, v.venue_name,
                   s.seat_id, s.section, s.row_number, s.seat_number,
                   CASE
                     WHEN o.payment_status = 'CANCELLED' THEN 'Dibatalkan'
                     WHEN o.payment_status = 'UNPAID' THEN 'Pending'
                     WHEN e.event_datetime < NOW() THEN 'Terpakai'
                     ELSE 'Valid'
                   END AS ticket_status
            FROM ticket t
            JOIN ticket_category tc ON tc.category_id = t.tcategory_id
            JOIN event e ON e.event_id = tc.tevent_id
            JOIN venue v ON v.venue_id = e.venue_id
            JOIN "ORDER" o ON o.order_id = t.torder_id
            JOIN customer c ON c.customer_id = o.customer_id
            LEFT JOIN has_relationship hr ON hr.ticket_id = t.ticket_id
            LEFT JOIN seat s ON s.seat_id = hr.seat_id
            WHERE 1=1 {scope_sql}
        """
        params = list(scope_params)
        if q:
            sql += " AND (t.ticket_code ILIKE %s OR e.event_title ILIKE %s OR c.full_name ILIKE %s OR v.venue_name ILIKE %s)"
            params.extend([f"%{q}%"] * 4)
        sql += " ORDER BY e.event_datetime DESC, t.ticket_code"

        with connection.cursor() as cur:
            _schema(cur)
            cur.execute(sql, params)
            rows = cur.fetchall()

        tickets = []
        for r in rows:
            ticket = {
                "id": str(r[0]),
                "code": r[1],
                "category_id": str(r[2]),
                "category": r[3],
                "price": float(r[4]),
                "order_id": str(r[5]),
                "payment_status": r[6],
                "customer_id": str(r[7]),
                "customer": r[8],
                "event_id": str(r[9]),
                "event": r[10],
                "datetime": r[11].strftime("%Y-%m-%d %H:%M") if r[11] else "",
                "venue_id": str(r[12]),
                "venue": r[13],
                "seat_id": str(r[14]) if r[14] else "",
                "seat": f"{r[15]} {r[16]}{r[17]}" if r[14] else "-",
                "status": r[18],
            }
            if not status or status == "Semua Status" or ticket["status"] == status:
                tickets.append(ticket)

        return JsonResponse({
            "tickets": tickets,
            "stats": {
                "total": len(tickets),
                "valid": sum(1 for ticket in tickets if ticket["status"] == "Valid"),
                "used": sum(1 for ticket in tickets if ticket["status"] == "Terpakai"),
            },
            "role": role,
            "can_manage": _can_manage(role),
        })

    if request.method == "POST":
        if not _can_manage(role):
            return JsonResponse({"error": "Akses ditolak."}, status=403)

        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        category_id = body.get("category_id", "").strip()
        order_id = body.get("order_id", "").strip()
        seat_id = body.get("seat_id", "").strip() or None
        ticket_code = body.get("ticket_code", "").strip()

        if not all([category_id, order_id]):
            return JsonResponse({"error": "Kategori tiket dan order wajib dipilih."}, status=400)

        ticket_id = str(uuid.uuid4())
        ticket_code = ticket_code or f"TTK-{ticket_id[:8].upper()}"

        ok, err = _validate_ticket_links(category_id, order_id, seat_id, role, organizer_id)
        if not ok:
            return JsonResponse({"error": err}, status=400)

        try:
            with transaction.atomic(), connection.cursor() as cur:
                _schema(cur)
                cur.execute(
                    """
                    INSERT INTO ticket (ticket_id, ticket_code, tcategory_id, torder_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [ticket_id, ticket_code, category_id, order_id],
                )
                if seat_id:
                    cur.execute(
                        "INSERT INTO has_relationship (seat_id, ticket_id) VALUES (%s, %s)",
                        [seat_id, ticket_id],
                    )
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Tiket berhasil ditambahkan.", "id": ticket_id}, status=201)

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
@_api_login_required
def api_ticket_detail(request, ticket_id):
    role = request.session.get("role", "guest")
    organizer_id = request.session.get("organizer_id")
    if not _can_manage(role):
        return JsonResponse({"error": "Akses ditolak."}, status=403)

    if request.method == "PUT":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        category_id = body.get("category_id", "").strip()
        order_id = body.get("order_id", "").strip()
        seat_id = body.get("seat_id", "").strip() or None
        ticket_code = body.get("ticket_code", "").strip()

        if not all([ticket_code, category_id, order_id]):
            return JsonResponse({"error": "Kode tiket, kategori, dan order wajib diisi."}, status=400)

        ok, err = _validate_ticket_links(category_id, order_id, seat_id, role, organizer_id, ticket_id=str(ticket_id))
        if not ok:
            return JsonResponse({"error": err}, status=400)

        try:
            with transaction.atomic(), connection.cursor() as cur:
                _schema(cur)
                cur.execute(
                    """
                    UPDATE ticket
                    SET ticket_code=%s, tcategory_id=%s, torder_id=%s
                    WHERE ticket_id=%s
                    """,
                    [ticket_code, category_id, order_id, str(ticket_id)],
                )
                if cur.rowcount == 0:
                    return JsonResponse({"error": "Tiket tidak ditemukan."}, status=404)
                cur.execute("DELETE FROM has_relationship WHERE ticket_id=%s", [str(ticket_id)])
                if seat_id:
                    cur.execute(
                        "INSERT INTO has_relationship (seat_id, ticket_id) VALUES (%s, %s)",
                        [seat_id, str(ticket_id)],
                    )
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Tiket berhasil diperbarui."})

    if request.method == "DELETE":
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _schema(cur)
                if role == "organizer" and organizer_id:
                    cur.execute(
                        """
                        SELECT 1
                        FROM ticket t
                        JOIN ticket_category tc ON tc.category_id = t.tcategory_id
                        JOIN event e ON e.event_id = tc.tevent_id
                        WHERE t.ticket_id=%s AND e.organizer_id=%s
                        """,
                        [str(ticket_id), organizer_id],
                    )
                    if not cur.fetchone():
                        return JsonResponse({"error": "Tiket tidak ditemukan untuk event organizer ini."}, status=404)

                cur.execute("DELETE FROM has_relationship WHERE ticket_id=%s", [str(ticket_id)])
                cur.execute("DELETE FROM ticket WHERE ticket_id=%s", [str(ticket_id)])
                if cur.rowcount == 0:
                    return JsonResponse({"error": "Tiket tidak ditemukan."}, status=404)
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Tiket berhasil dihapus."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


def _validate_ticket_links(category_id, order_id, seat_id, role, organizer_id=None, ticket_id=None):
    with connection.cursor() as cur:
        _schema(cur)
        cur.execute(
            """
            SELECT tc.quota, e.event_id, e.event_title, e.venue_id, e.organizer_id,
                   COUNT(t.ticket_id) FILTER (WHERE t.ticket_id <> COALESCE(%s::uuid, '00000000-0000-0000-0000-000000000000'::uuid)) AS sold
            FROM ticket_category tc
            JOIN event e ON e.event_id = tc.tevent_id
            LEFT JOIN ticket t ON t.tcategory_id = tc.category_id
            WHERE tc.category_id = %s
            GROUP BY tc.category_id, tc.quota, e.event_id, e.event_title, e.venue_id, e.organizer_id
            """,
            [ticket_id, category_id],
        )
        cat = cur.fetchone()
        if not cat:
            return False, "Kategori tiket tidak ditemukan."
        quota, _event_id, _event_title, event_venue_id, event_organizer_id, sold = cat
        if role == "organizer" and organizer_id and str(event_organizer_id) != str(organizer_id):
            return False, "Organizer hanya dapat mengelola tiket untuk event miliknya."
        if sold >= quota:
            return False, "Kuota kategori tiket ini sudah habis."

        cur.execute("SELECT 1 FROM \"ORDER\" WHERE order_id = %s", [order_id])
        if not cur.fetchone():
            return False, "Order tidak ditemukan."

        if seat_id:
            cur.execute(
                """
                SELECT s.venue_id
                FROM seat s
                WHERE s.seat_id = %s
                """,
                [seat_id],
            )
            seat = cur.fetchone()
            if not seat:
                return False, "Kursi tidak ditemukan."
            if str(seat[0]) != str(event_venue_id):
                return False, "Kursi harus berasal dari venue event kategori tiket."

            cur.execute(
                """
                SELECT 1 FROM has_relationship
                WHERE seat_id = %s AND ticket_id <> COALESCE(%s::uuid, '00000000-0000-0000-0000-000000000000'::uuid)
                """,
                [seat_id, ticket_id],
            )
            if cur.fetchone():
                return False, "Kursi tersebut sudah dipakai tiket lain."

    return True, None


@_api_login_required
def api_ticket_options(request):
    role = request.session.get("role", "guest")
    organizer_id = request.session.get("organizer_id")

    category_sql = """
        SELECT tc.category_id, tc.category_name, tc.price, tc.quota,
               e.event_title, e.event_id, e.venue_id
        FROM ticket_category tc
        JOIN event e ON e.event_id = tc.tevent_id
        WHERE 1=1
    """
    category_params = []
    if role == "organizer" and organizer_id:
        category_sql += " AND e.organizer_id = %s"
        category_params.append(organizer_id)
    category_sql += " ORDER BY e.event_title, tc.category_name"

    with connection.cursor() as cur:
        _schema(cur)
        cur.execute(category_sql, category_params)
        categories = [
            {
                "id": str(r[0]),
                "name": r[1],
                "price": float(r[2]),
                "quota": r[3],
                "event": r[4],
                "event_id": str(r[5]),
                "venue_id": str(r[6]),
            }
            for r in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT o.order_id, c.full_name, o.payment_status, o.total_amount
            FROM "ORDER" o
            JOIN customer c ON c.customer_id = o.customer_id
            ORDER BY o.order_date DESC
            """
        )
        orders = [
            {
                "id": str(r[0]),
                "customer": r[1],
                "status": r[2],
                "total": float(r[3]),
            }
            for r in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT s.seat_id, s.section, s.row_number, s.seat_number, s.venue_id, v.venue_name
            FROM seat s
            JOIN venue v ON v.venue_id = s.venue_id
            WHERE NOT EXISTS (
                SELECT 1 FROM has_relationship hr WHERE hr.seat_id = s.seat_id
            )
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
            """
        )
        seats = [
            {
                "id": str(r[0]),
                "label": f"{r[5]} - {r[1]} {r[2]}{r[3]}",
                "venue_id": str(r[4]),
            }
            for r in cur.fetchall()
        ]

    return JsonResponse({"categories": categories, "orders": orders, "seats": seats})
