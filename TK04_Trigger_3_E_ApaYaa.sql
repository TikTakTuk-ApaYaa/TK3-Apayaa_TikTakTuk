-- TK04 — TRIGGER 3 (FITUR HIJAU)
-- PENTING: semua referensi tabel sudah pakai schema eksplisit "tiktaktuk."
--          agar berjalan benar di Railway / Supabase tanpa mengandalkan search_path

DROP FUNCTION IF EXISTS tiktaktuk.fn_validate_event_artist() CASCADE;
DROP FUNCTION IF EXISTS tiktaktuk.sp_sisa_kuota_event(UUID) CASCADE;


-- ============================================================
-- BAGIAN 1: Trigger — Validasi EVENT_ARTIST
-- ============================================================
CREATE OR REPLACE FUNCTION tiktaktuk.fn_validate_event_artist()
RETURNS TRIGGER AS $$
DECLARE
    v_artist_name  VARCHAR;
    v_event_title  VARCHAR;
BEGIN
    -- Cek artist terdaftar
    SELECT name INTO v_artist_name
    FROM tiktaktuk.ARTIST
    WHERE artist_id = NEW.artist_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Artist dengan ID % tidak ditemukan.', NEW.artist_id;
    END IF;

    -- Cek event terdaftar
    SELECT event_title INTO v_event_title
    FROM tiktaktuk.EVENT
    WHERE event_id = NEW.event_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Event dengan ID % tidak ditemukan.', NEW.event_id;
    END IF;

    -- Cek duplikasi artist di event yang sama
    IF EXISTS (
        SELECT 1
        FROM tiktaktuk.EVENT_ARTIST
        WHERE artist_id = NEW.artist_id
          AND event_id  = NEW.event_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Artist "%" sudah terdaftar pada event "%".',
            v_artist_name, v_event_title;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_event_artist ON tiktaktuk.EVENT_ARTIST;

CREATE TRIGGER trg_validate_event_artist
BEFORE INSERT
ON tiktaktuk.EVENT_ARTIST
FOR EACH ROW
EXECUTE FUNCTION tiktaktuk.fn_validate_event_artist();


-- ============================================================
-- BAGIAN 2: Stored Procedure — Sisa Kuota Ticket Category
-- ============================================================
CREATE OR REPLACE FUNCTION tiktaktuk.sp_sisa_kuota_event(p_event_id UUID)
RETURNS TABLE (
    category_id   UUID,
    category_name VARCHAR,
    quota         INTEGER,
    sold          BIGINT,
    remaining     BIGINT
) AS $$
DECLARE
    v_exists INTEGER;
BEGIN
    -- Cek event ada
    SELECT COUNT(*) INTO v_exists
    FROM tiktaktuk.EVENT
    WHERE event_id = p_event_id;

    IF v_exists = 0 THEN
        RAISE EXCEPTION 'ERROR: Event dengan ID % tidak ditemukan.', p_event_id;
    END IF;

    RETURN QUERY
        SELECT
            tc.category_id,
            tc.category_name,
            tc.quota,
            COUNT(t.ticket_id)                    AS sold,
            tc.quota::BIGINT - COUNT(t.ticket_id) AS remaining
        FROM tiktaktuk.TICKET_CATEGORY tc
        LEFT JOIN tiktaktuk.TICKET t ON t.tcategory_id = tc.category_id
        WHERE tc.tevent_id = p_event_id
        GROUP BY tc.category_id, tc.category_name, tc.quota
        ORDER BY tc.category_name;
END;
$$ LANGUAGE plpgsql;