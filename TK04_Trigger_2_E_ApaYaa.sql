-- ================================================================
-- TRIGGER FITUR KUNING (No. 2 dari daftar trigger)
-- Trigger 1: Cegah duplikasi nama venue di kota yang sama (ignore case)
-- Trigger 2: Cegah penghapusan venue yg masih punya event aktif
-- ================================================================

SET search_path TO tiktaktuk;

-- ---------------------------------------------------------------
-- TRIGGER 1: Cegah duplikasi nama venue di kota yang sama
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION tiktaktuk.fn_cek_duplikasi_venue()
RETURNS TRIGGER AS $$
DECLARE
    v_existing_id UUID;
BEGIN
    SELECT venue_id INTO v_existing_id
    FROM tiktaktuk.venue
    WHERE LOWER(venue_name) = LOWER(NEW.venue_name)
      AND LOWER(city)       = LOWER(NEW.city)
      AND venue_id         <> COALESCE(NEW.venue_id, gen_random_uuid());

    IF FOUND THEN
        RAISE EXCEPTION 'Venue ''%'' di kota ''%'' sudah terdaftar dengan ID %.',
            NEW.venue_name, NEW.city, v_existing_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cek_duplikasi_venue ON tiktaktuk.venue;
CREATE TRIGGER trg_cek_duplikasi_venue
    BEFORE INSERT OR UPDATE OF venue_name, city
    ON tiktaktuk.venue
    FOR EACH ROW
    EXECUTE FUNCTION tiktaktuk.fn_cek_duplikasi_venue();


-- ---------------------------------------------------------------
-- TRIGGER 2: Cegah penghapusan venue yang masih punya event aktif
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION tiktaktuk.fn_cek_venue_event_aktif()
RETURNS TRIGGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM tiktaktuk.event
    WHERE venue_id       = OLD.venue_id
      AND event_datetime >= CURRENT_TIMESTAMP;

    IF v_count > 0 THEN
        RAISE EXCEPTION 'Venue ''%'' masih memiliki event aktif sehingga tidak dapat dihapus.',
            OLD.venue_name;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cek_venue_event_aktif ON tiktaktuk.venue;
CREATE TRIGGER trg_cek_venue_event_aktif
    BEFORE DELETE
    ON tiktaktuk.venue
    FOR EACH ROW
    EXECUTE FUNCTION tiktaktuk.fn_cek_venue_event_aktif();