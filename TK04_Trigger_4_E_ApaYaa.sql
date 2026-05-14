SET search_path TO tiktaktuk;

-- 1. UBAH NAMA FUNGSI JADI: sp_sisa_kuota_biru
DROP FUNCTION IF EXISTS sp_sisa_kuota_biru(UUID) CASCADE;
CREATE OR REPLACE FUNCTION sp_sisa_kuota_biru(p_event_id UUID)
RETURNS TABLE(
    category_id UUID,
    category_name VARCHAR,
    remaining INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tc.category_id,
        tc.category_name,
        (tc.quota - COALESCE(COUNT(t.ticket_id)::INTEGER, 0))::INTEGER AS remaining
    FROM tiktaktuk.ticket_category tc
    LEFT JOIN tiktaktuk.ticket t ON tc.category_id = t.tcategory_id
    WHERE tc.tevent_id = p_event_id
    GROUP BY tc.category_id, tc.category_name, tc.quota;
END;
$$ LANGUAGE plpgsql;


-- 2. TRIGGER CEK KUOTA
CREATE OR REPLACE FUNCTION check_ticket_quota()
RETURNS TRIGGER AS $$
DECLARE
    v_quota INTEGER;
    v_terjual INTEGER;
BEGIN
    -- Ambil kuota maksimal
    SELECT quota INTO v_quota 
    FROM tiktaktuk.ticket_category 
    WHERE category_id = NEW.tcategory_id;

    -- Hitung yang sudah terjual
    SELECT COUNT(*) INTO v_terjual 
    FROM tiktaktuk.ticket 
    WHERE tcategory_id = NEW.tcategory_id;

    IF v_terjual >= v_quota THEN
        RAISE EXCEPTION 'Maaf, kuota untuk kategori tiket ini sudah habis.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_ticket_quota ON tiktaktuk.ticket;
CREATE TRIGGER trg_check_ticket_quota
BEFORE INSERT ON tiktaktuk.ticket
FOR EACH ROW EXECUTE FUNCTION check_ticket_quota();


-- 3. TRIGGER VALIDASI PROMOSI
CREATE OR REPLACE FUNCTION validate_promotion()
RETURNS TRIGGER AS $$
DECLARE
    v_start DATE;
    v_end DATE;
    v_limit INTEGER;
    v_used INTEGER;
BEGIN
    -- Ambil info promosi
    SELECT start_date, end_date, usage_limit INTO v_start, v_end, v_limit
    FROM tiktaktuk.promotion
    WHERE promotion_id = NEW.promotion_id;

    -- 1. Validasi Tanggal
    IF CURRENT_DATE < v_start OR CURRENT_DATE > v_end THEN
        RAISE EXCEPTION 'Kode promo tidak dapat digunakan (diluar periode promo).';
    END IF;

    -- 2. Validasi Limit Penggunaan
    SELECT COUNT(*) INTO v_used
    FROM tiktaktuk.order_promotion
    WHERE promotion_id = NEW.promotion_id;

    IF v_used >= v_limit THEN
        RAISE EXCEPTION 'Maaf, kuota penggunaan kode promo ini sudah habis.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_promotion ON tiktaktuk.order_promotion;
CREATE TRIGGER trg_validate_promotion
BEFORE INSERT ON tiktaktuk.order_promotion
FOR EACH ROW EXECUTE FUNCTION validate_promotion();