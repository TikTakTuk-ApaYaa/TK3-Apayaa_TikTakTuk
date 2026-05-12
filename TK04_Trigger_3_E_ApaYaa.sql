-- ============================================================
--  TK04 — TRIGGER 4 (KELOMPOK FITUR HIJAU)
--  Validasi Promotion saat digunakan ke sebuah Order
--  Schema: tiktaktuk
-- ============================================================

SET search_path TO tiktaktuk;

-- ── Hapus function lama kalau ada ──────────────────────────
DROP FUNCTION IF EXISTS sp_sisa_kuota_event(UUID) CASCADE;
DROP FUNCTION IF EXISTS fn_validate_promotion_on_order() CASCADE;

-- ──────────────────────────────────────────────────────────
--  STORED PROCEDURE: Tampilkan sisa kuota tiket per event
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_sisa_kuota_event(p_event_id UUID)
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
            COUNT(t.ticket_id)                          AS sold,
            tc.quota::BIGINT - COUNT(t.ticket_id)       AS remaining
        FROM tiktaktuk.TICKET_CATEGORY tc
        LEFT JOIN tiktaktuk.TICKET t ON t.tcategory_id = tc.category_id
        WHERE tc.tevent_id = p_event_id
        GROUP BY tc.category_id, tc.category_name, tc.quota
        ORDER BY tc.category_name;
END;
$$ LANGUAGE plpgsql;


-- ──────────────────────────────────────────────────────────
--  TRIGGER FUNCTION: Validasi promotion sebelum masuk order
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_validate_promotion_on_order()
RETURNS TRIGGER AS $$
DECLARE
    v_promo       RECORD;
    v_usage_count INTEGER;
    v_event_date  DATE;
BEGIN
    -- Validasi 4a: Promotion harus terdaftar
    SELECT * INTO v_promo
    FROM tiktaktuk.PROMOTION
    WHERE promotion_id = NEW.promotion_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'ERROR: Promotion dengan ID % tidak ditemukan.',
            NEW.promotion_id;
    END IF;

    -- Validasi 4b: Belum melebihi usage_limit
    SELECT COUNT(*)
    INTO v_usage_count
    FROM tiktaktuk.ORDER_PROMOTION
    WHERE promotion_id = NEW.promotion_id;

    IF v_usage_count >= v_promo.usage_limit THEN
        RAISE EXCEPTION
            'ERROR: Promotion "%" telah mencapai batas maksimum penggunaan.',
            v_promo.promo_code;
    END IF;

    -- Validasi 4c: Tanggal event dalam periode berlaku promotion
    SELECT e.event_datetime::DATE INTO v_event_date
    FROM tiktaktuk."ORDER" o
    JOIN tiktaktuk.TICKET t           ON t.torder_id    = o.order_id
    JOIN tiktaktuk.TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
    JOIN tiktaktuk.EVENT e            ON e.event_id     = tc.tevent_id
    WHERE o.order_id = NEW.order_id
    LIMIT 1;

    IF v_event_date IS NOT NULL THEN
        IF v_event_date < v_promo.start_date OR v_event_date > v_promo.end_date THEN
            RAISE EXCEPTION
                'ERROR: Promotion "%" tidak berlaku untuk tanggal event ini.',
                v_promo.promo_code;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_promotion ON tiktaktuk.ORDER_PROMOTION;

CREATE TRIGGER trg_validate_promotion
BEFORE INSERT
ON tiktaktuk.ORDER_PROMOTION
FOR EACH ROW
EXECUTE FUNCTION fn_validate_promotion_on_order();