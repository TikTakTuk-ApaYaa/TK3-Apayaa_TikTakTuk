SET search_path TO tiktaktuk;

CREATE OR REPLACE FUNCTION fn_cek_kursi_terisi()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM HAS_RELATIONSHIP hr
        WHERE hr.seat_id = OLD.seat_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Kursi % - Baris % No. % tidak dapat dihapus karena sudah terisi.',
            OLD.section,
            OLD.row_number,
            OLD.seat_number;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cek_kursi_terisi ON SEAT;

CREATE TRIGGER trg_cek_kursi_terisi
BEFORE DELETE ON SEAT
FOR EACH ROW
EXECUTE FUNCTION fn_cek_kursi_terisi();

CREATE OR REPLACE FUNCTION fn_cek_kuota_kategori_tiket()
RETURNS TRIGGER AS $$
DECLARE
    v_category_name TICKET_CATEGORY.category_name%TYPE;
    v_quota TICKET_CATEGORY.quota%TYPE;
    v_total_tiket INTEGER;
BEGIN
    SELECT tc.category_name, tc.quota
    INTO v_category_name, v_quota
    FROM TICKET_CATEGORY tc
    WHERE tc.category_id = NEW.tcategory_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Kategori tiket tidak ditemukan.';
    END IF;

    SELECT COUNT(*)
    INTO v_total_tiket
    FROM TICKET t
    WHERE t.tcategory_id = NEW.tcategory_id;

    IF v_total_tiket >= v_quota THEN
        RAISE EXCEPTION 'ERROR: Kuota kategori tiket "%" sudah penuh. Tidak dapat membuat tiket baru.',
            v_category_name;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cek_kuota_kategori_tiket ON TICKET;

CREATE TRIGGER trg_cek_kuota_kategori_tiket
BEFORE INSERT ON TICKET
FOR EACH ROW
EXECUTE FUNCTION fn_cek_kuota_kategori_tiket();
