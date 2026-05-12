import json
import uuid

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection


#  Helper: set schema search path
def _sp(cursor):
    """Set search_path ke schema Tiktaktuk."""
    cursor.execute("SET search_path TO Tiktaktuk")


def _clean_db_error(exc):
    """
    Ambil pesan error dari psycopg2 / PostgreSQL trigger RAISE.
    Trigger mengirim pesan dalam format:
        ERROR:  <pesan trigger>
    """
    msg = str(exc)
    # Ambil baris pertama yang mengandung ERROR:
    for line in msg.splitlines():
        line = line.strip()
        if line.startswith("ERROR:"):
            return line.replace("ERROR:", "").strip()
    return msg.splitlines()[0] if msg else "Terjadi kesalahan."


#  PAGE VIEWS (serve HTML templates)
def artist_page(request):
    return render(request, "artist_list.html")


def ticket_category_page(request):
    return render(request, "ticket_category_list.html")


#  API: ARTIST
@csrf_exempt
def api_artists(request):
    """GET /hijau/api/artists/  — daftar semua artis (+ pencarian)
       POST /hijau/api/artists/ — tambah artis baru
    """
    if request.method == "GET":
        q = request.GET.get("q", "").strip().lower()
        with connection.cursor() as c:
            _sp(c)
            if q:
                c.execute(
                    """
                    SELECT artist_id, name, genre
                    FROM ARTIST
                    WHERE LOWER(name) LIKE %s OR LOWER(COALESCE(genre,'')) LIKE %s
                    ORDER BY name
                    """,
                    [f"%{q}%", f"%{q}%"],
                )
            else:
                c.execute("SELECT artist_id, name, genre FROM ARTIST ORDER BY name")
            rows = c.fetchall()

        # Hitung total event per artis
        with connection.cursor() as c:
            _sp(c)
            c.execute(
                "SELECT artist_id, COUNT(DISTINCT event_id) FROM EVENT_ARTIST GROUP BY artist_id"
            )
            event_counts = {str(r[0]): r[1] for r in c.fetchall()}

        artists = [
            {
                "id": str(r[0]),
                "name": r[1],
                "genre": r[2] or "",
                "event_count": event_counts.get(str(r[0]), 0),
            }
            for r in rows
        ]
        return JsonResponse({"artists": artists, "total": len(artists)})

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        name = body.get("name", "").strip()
        genre = body.get("genre", "").strip()

        if not name:
            return JsonResponse({"error": "Nama artis tidak boleh kosong."}, status=400)

        artist_id = str(uuid.uuid4())
        try:
            with connection.cursor() as c:
                _sp(c)
                c.execute(
                    "INSERT INTO ARTIST (artist_id, name, genre) VALUES (%s, %s, %s)",
                    [artist_id, name, genre or None],
                )
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Artis berhasil ditambahkan.", "id": artist_id}, status=201)

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
def api_artist_detail(request, artist_id):
    """PUT /hijau/api/artists/<id>/  — update artis
       DELETE /hijau/api/artists/<id>/ — hapus artis
    """
    if request.method == "PUT":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        name = body.get("name", "").strip()
        genre = body.get("genre", "").strip()

        if not name:
            return JsonResponse({"error": "Nama artis tidak boleh kosong."}, status=400)

        try:
            with connection.cursor() as c:
                _sp(c)
                c.execute(
                    "UPDATE ARTIST SET name=%s, genre=%s WHERE artist_id=%s",
                    [name, genre or None, artist_id],
                )
                if c.rowcount == 0:
                    return JsonResponse({"error": "Artis tidak ditemukan."}, status=404)
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Artis berhasil diperbarui."})

    elif request.method == "DELETE":
        try:
            with connection.cursor() as c:
                _sp(c)
                # Cek apakah artis terdaftar di event — jika ada constraint FK, beri pesan jelas
                c.execute(
                    "SELECT COUNT(*) FROM EVENT_ARTIST WHERE artist_id=%s", [artist_id]
                )
                count = c.fetchone()[0]
                if count > 0:
                    return JsonResponse(
                        {"error": f"Artis masih terdaftar di {count} event. Hapus keterkaitan event terlebih dahulu."},
                        status=400,
                    )
                c.execute("DELETE FROM ARTIST WHERE artist_id=%s", [artist_id])
                if c.rowcount == 0:
                    return JsonResponse({"error": "Artis tidak ditemukan."}, status=404)
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Artis berhasil dihapus."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


#  API: TICKET CATEGORY
@csrf_exempt
def api_ticket_categories(request):
    """GET /hijau/api/ticket-categories/  — daftar kategori tiket
       POST /hijau/api/ticket-categories/ — tambah kategori tiket
    """
    if request.method == "GET":
        q = request.GET.get("q", "").strip().lower()
        event_filter = request.GET.get("event_id", "").strip()

        sql = """
            SELECT tc.category_id, tc.category_name, tc.quota, tc.price,
                   tc.tevent_id, e.event_title,
                   COALESCE(
                       (SELECT COUNT(*) FROM TICKET t WHERE t.tcategory_id = tc.category_id),
                       0
                   ) AS sold
            FROM TICKET_CATEGORY tc
            JOIN EVENT e ON e.event_id = tc.tevent_id
            WHERE 1=1
        """
        params = []

        if q:
            sql += " AND (LOWER(tc.category_name) LIKE %s OR LOWER(e.event_title) LIKE %s)"
            params += [f"%{q}%", f"%{q}%"]
        if event_filter:
            sql += " AND tc.tevent_id = %s"
            params.append(event_filter)

        sql += " ORDER BY e.event_title, tc.category_name"

        with connection.cursor() as c:
            _sp(c)
            c.execute(sql, params)
            rows = c.fetchall()

        categories = [
            {
                "id": str(r[0]),
                "name": r[1],
                "quota": r[2],
                "price": float(r[3]),
                "event_id": str(r[4]),
                "event_title": r[5],
                "sold": r[6],
                "remaining": r[2] - r[6],
            }
            for r in rows
        ]
        return JsonResponse({"categories": categories, "total": len(categories)})

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        category_name = body.get("category_name", "").strip()
        quota = body.get("quota")
        price = body.get("price")
        event_id = body.get("event_id", "").strip()

        # Validasi input
        errors = {}
        if not category_name:
            errors["category_name"] = "Nama kategori tidak boleh kosong."
        if quota is None or int(quota) < 1:
            errors["quota"] = "Kuota harus lebih dari 0."
        if price is None or float(price) < 0:
            errors["price"] = "Harga tidak boleh negatif."
        if not event_id:
            errors["event_id"] = "Event harus dipilih."
        if errors:
            return JsonResponse({"error": "Validasi gagal.", "fields": errors}, status=400)

        category_id = str(uuid.uuid4())
        try:
            with connection.cursor() as c:
                _sp(c)
                c.execute(
                    """
                    INSERT INTO TICKET_CATEGORY (category_id, category_name, quota, price, tevent_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [category_id, category_name, int(quota), float(price), event_id],
                )
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse(
            {"message": "Kategori tiket berhasil ditambahkan.", "id": category_id},
            status=201,
        )

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
def api_ticket_category_detail(request, category_id):
    """PUT /hijau/api/ticket-categories/<id>/  — update
       DELETE /hijau/api/ticket-categories/<id>/ — hapus
    """
    if request.method == "PUT":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Request body tidak valid."}, status=400)

        category_name = body.get("category_name", "").strip()
        quota = body.get("quota")
        price = body.get("price")
        event_id = body.get("event_id", "").strip()

        if not category_name:
            return JsonResponse({"error": "Nama kategori tidak boleh kosong."}, status=400)

        try:
            with connection.cursor() as c:
                _sp(c)
                c.execute(
                    """
                    UPDATE TICKET_CATEGORY
                    SET category_name=%s, quota=%s, price=%s, tevent_id=%s
                    WHERE category_id=%s
                    """,
                    [category_name, int(quota), float(price), event_id, category_id],
                )
                if c.rowcount == 0:
                    return JsonResponse({"error": "Kategori tidak ditemukan."}, status=404)
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Kategori tiket berhasil diperbarui."})

    elif request.method == "DELETE":
        try:
            with connection.cursor() as c:
                _sp(c)
                # Cek apakah ada tiket yang sudah dibuat untuk kategori ini
                c.execute(
                    "SELECT COUNT(*) FROM TICKET WHERE tcategory_id=%s", [category_id]
                )
                count = c.fetchone()[0]
                if count > 0:
                    return JsonResponse(
                        {"error": f"Kategori masih memiliki {count} tiket. Tidak dapat dihapus."},
                        status=400,
                    )
                c.execute(
                    "DELETE FROM TICKET_CATEGORY WHERE category_id=%s", [category_id]
                )
                if c.rowcount == 0:
                    return JsonResponse({"error": "Kategori tidak ditemukan."}, status=404)
        except Exception as exc:
            return JsonResponse({"error": _clean_db_error(exc)}, status=400)

        return JsonResponse({"message": "Kategori tiket berhasil dihapus."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


#  API: EVENTS (untuk dropdown di form kategori)
def api_events(request):
    """GET /hijau/api/events/ — daftar semua event (untuk dropdown)"""
    with connection.cursor() as c:
        _sp(c)
        c.execute(
            "SELECT event_id, event_title, event_datetime FROM EVENT ORDER BY event_title"
        )
        rows = c.fetchall()
    events = [{"id": str(r[0]), "title": r[1], "datetime": str(r[2])} for r in rows]
    return JsonResponse({"events": events})