-- =============================================================================
-- 부동산 매물 관리 시스템 - 트리거/함수 DDL
-- 작성자: BE코코
-- 작성일: 2026-02-14
-- PostgreSQL 15+
-- =============================================================================

-- 1. updated_at 자동 갱신 함수
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_properties_updated_at
    BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_inquiries_updated_at
    BEFORE UPDATE ON inquiries
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();


-- 2. 매물번호 자동 생성 (P-YYYYMMDD-NNN)
-- 동시성 안전: property_no UNIQUE 제약 + 재시도 로직 (최대 3회)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_generate_property_no()
RETURNS TRIGGER AS $$
DECLARE
    today_str TEXT;
    seq_num INTEGER;
    retry_count INTEGER := 0;
BEGIN
    IF NEW.property_no IS NULL OR NEW.property_no = '' THEN
        today_str := TO_CHAR(NOW(), 'YYYYMMDD');
        LOOP
            SELECT COALESCE(MAX(
                CAST(SUBSTRING(property_no FROM 'P-\d{8}-(\d+)') AS INTEGER)
            ), 0) + 1 + retry_count
            INTO seq_num
            FROM properties
            WHERE property_no LIKE 'P-' || today_str || '-%';

            NEW.property_no := 'P-' || today_str || '-' || LPAD(seq_num::TEXT, 3, '0');

            -- UNIQUE 제약 위반 시 재시도 (최대 3회)
            BEGIN
                PERFORM 1 FROM properties WHERE property_no = NEW.property_no;
                IF NOT FOUND THEN
                    EXIT; -- 중복 없음, 루프 종료
                END IF;
            END;

            retry_count := retry_count + 1;
            IF retry_count >= 3 THEN
                RAISE EXCEPTION '매물번호 생성 실패: 3회 재시도 초과 (날짜: %)', today_str;
            END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_generate_property_no
    BEFORE INSERT ON properties
    FOR EACH ROW EXECUTE FUNCTION fn_generate_property_no();


-- 3. 가격 유효성 검증 (trade_type별 필수 가격 필드)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_validate_property_price()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.trade_type = '매매' AND (NEW.sale_price IS NULL OR NEW.sale_price <= 0) THEN
        RAISE EXCEPTION '매매 매물은 sale_price(양수)가 필수입니다.';
    END IF;
    IF NEW.trade_type = '전세' AND (NEW.deposit IS NULL OR NEW.deposit <= 0) THEN
        RAISE EXCEPTION '전세 매물은 deposit(양수)이 필수입니다.';
    END IF;
    IF NEW.trade_type = '월세' THEN
        IF NEW.deposit IS NULL THEN
            RAISE EXCEPTION '월세 매물은 deposit이 필수입니다.';
        END IF;
        IF NEW.monthly_rent IS NULL OR NEW.monthly_rent <= 0 THEN
            RAISE EXCEPTION '월세 매물은 monthly_rent(양수)가 필수입니다.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_property_price
    BEFORE INSERT OR UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION fn_validate_property_price();


-- 4. 변경이력 자동 기록 (15개 필드 추적)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_log_property_changes()
RETURNS TRIGGER AS $$
DECLARE
    fields TEXT[] := ARRAY[
        'property_type', 'trade_type', 'status',
        'sale_price', 'deposit', 'monthly_rent', 'maintenance_fee',
        'area_exclusive_m2', 'area_supply_m2',
        'sido', 'sigungu', 'dong', 'floor', 'direction', 'description'
    ];
    f TEXT;
    old_val TEXT;
    new_val TEXT;
BEGIN
    FOREACH f IN ARRAY fields LOOP
        EXECUTE format('SELECT ($1).%I::TEXT, ($2).%I::TEXT', f, f)
            INTO old_val, new_val
            USING OLD, NEW;
        IF old_val IS DISTINCT FROM new_val THEN
            INSERT INTO property_history (property_id, field_name, old_value, new_value)
            VALUES (NEW.id, f, old_val, new_val);
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_properties_log_changes
    AFTER UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION fn_log_property_changes();
