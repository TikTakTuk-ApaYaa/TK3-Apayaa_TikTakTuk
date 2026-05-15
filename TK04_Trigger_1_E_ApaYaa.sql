SET search_path TO tiktaktuk;


CREATE OR REPLACE FUNCTION validate_username_registration()
RETURNS TRIGGER AS $$
BEGIN

    IF NEW.username !~ '^[a-zA-Z0-9]+$' THEN
        RAISE EXCEPTION 'ERROR: Username "%" hanya boleh mengandung huruf dan angka tanpa simbol atau spasi.', NEW.username;
    END IF;

    IF EXISTS (
        SELECT 1 
        FROM USER_ACCOUNT 
        WHERE LOWER(username) = LOWER(NEW.username) 
          AND user_id != NEW.user_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Username "%" sudah terdaftar, gunakan username lain.', NEW.username;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trg_validate_user_account
BEFORE INSERT OR UPDATE ON USER_ACCOUNT
FOR EACH ROW
EXECUTE FUNCTION validate_username_registration();