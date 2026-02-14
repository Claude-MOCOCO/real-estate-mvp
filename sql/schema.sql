-- =============================================================================
-- 부동산 매물 관리 시스템 - DB 스키마 DDL
-- 작성자: BE코코
-- 작성일: 2026-02-14
-- PostgreSQL 15+
-- =============================================================================

-- 1. ENUM 타입 정의
-- -----------------------------------------------------------------------------

CREATE TYPE property_type_enum AS ENUM (
    '아파트', '빌라', '오피스텔', '원룸',
    '상가', '사무실', '토지', '주택'
);

CREATE TYPE trade_type_enum AS ENUM ('매매', '전세', '월세');

CREATE TYPE direction_enum AS ENUM (
    '남향', '남동향', '남서향', '동향',
    '서향', '북향', '북동향', '북서향'
);

CREATE TYPE property_status_enum AS ENUM (
    'active', 'in_contract', 'completed', 'hidden'
);

CREATE TYPE contact_type_enum AS ENUM (
    '매수자', '매도자', '임차인', '임대인', '기타'
);

CREATE TYPE inquiry_status_enum AS ENUM ('open', 'in_progress', 'closed');


-- 2. 테이블 DDL
-- -----------------------------------------------------------------------------

-- 2-1. properties (매물 마스터)
CREATE TABLE properties (
    id              BIGSERIAL       PRIMARY KEY,
    property_no     VARCHAR(16)     NOT NULL UNIQUE,     -- P-YYYYMMDD-NNN

    -- 유형
    property_type   property_type_enum  NOT NULL,
    trade_type      trade_type_enum     NOT NULL,

    -- 주소
    sido            VARCHAR(50)     NOT NULL,
    sigungu         VARCHAR(50)     NOT NULL,
    dong            VARCHAR(50)     NOT NULL,
    address_detail  VARCHAR(200),
    road_address    VARCHAR(200),
    latitude        NUMERIC(10, 7),
    longitude       NUMERIC(10, 7),

    -- 면적 (m2 단위)
    area_exclusive_m2   NUMERIC(10, 2),
    area_supply_m2      NUMERIC(10, 2),

    -- 가격 (만원 단위)
    sale_price      BIGINT,           -- 매매가
    deposit         BIGINT,           -- 보증금 (전세/월세)
    monthly_rent    INTEGER,          -- 월세

    -- 상세 정보
    floor           VARCHAR(20),      -- 층수 ('3', 'B1', '복층' 등)
    total_floors    INTEGER,
    room_count      SMALLINT,
    bathroom_count  SMALLINT,
    direction       direction_enum,
    built_year      SMALLINT,
    parking_available   BOOLEAN     DEFAULT FALSE,
    maintenance_fee     INTEGER,      -- 관리비 (만원)
    options         JSONB           DEFAULT '[]'::jsonb,  -- ["에어컨","냉장고"]
    tags            JSONB           DEFAULT '[]'::jsonb,  -- ["역세권","신축"]
    memo            TEXT,
    description     TEXT,

    -- 관리
    status          property_status_enum    DEFAULT 'active',
    source          VARCHAR(100),
    source_url      VARCHAR(500),

    -- 시간
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,    -- soft delete

    -- CHECK 제약조건
    CONSTRAINT chk_sale_price_positive      CHECK (sale_price IS NULL OR sale_price >= 0),
    CONSTRAINT chk_deposit_positive         CHECK (deposit IS NULL OR deposit >= 0),
    CONSTRAINT chk_monthly_rent_positive    CHECK (monthly_rent IS NULL OR monthly_rent >= 0),
    CONSTRAINT chk_area_exclusive_positive  CHECK (area_exclusive_m2 IS NULL OR area_exclusive_m2 > 0),
    CONSTRAINT chk_area_supply_positive     CHECK (area_supply_m2 IS NULL OR area_supply_m2 > 0),
    CONSTRAINT chk_area_supply_gte_exclusive CHECK (area_supply_m2 IS NULL OR area_exclusive_m2 IS NULL OR area_supply_m2 >= area_exclusive_m2),
    CONSTRAINT chk_total_floors_positive    CHECK (total_floors IS NULL OR total_floors > 0),
    CONSTRAINT chk_room_count_positive      CHECK (room_count IS NULL OR room_count >= 0),
    CONSTRAINT chk_bathroom_count_positive  CHECK (bathroom_count IS NULL OR bathroom_count >= 0),
    CONSTRAINT chk_built_year_range         CHECK (built_year IS NULL OR (built_year >= 1900 AND built_year <= 2100)),
    CONSTRAINT chk_maintenance_fee_positive CHECK (maintenance_fee IS NULL OR maintenance_fee >= 0),
    CONSTRAINT chk_latitude_range           CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    CONSTRAINT chk_longitude_range          CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180))
);

-- 2-2. property_history (변경이력)
CREATE TABLE property_history (
    id              BIGSERIAL       PRIMARY KEY,
    property_id     BIGINT          NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    field_name      VARCHAR(50)     NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- 2-3. contacts (고객 정보) — DDL만, Tool은 Phase 2
CREATE TABLE contacts (
    id              BIGSERIAL       PRIMARY KEY,
    name            VARCHAR(50)     NOT NULL,
    phone           VARCHAR(20),
    email           VARCHAR(100),
    contact_type    contact_type_enum   NOT NULL,
    company         VARCHAR(100),       -- 소속 (중개사무소 등)
    memo            TEXT,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- 2-4. inquiries (고객 문의 이력) — DDL만, Tool은 Phase 2
CREATE TABLE inquiries (
    id              BIGSERIAL       PRIMARY KEY,
    contact_id      BIGINT          NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    property_id     BIGINT          REFERENCES properties(id) ON DELETE SET NULL,
    content         TEXT            NOT NULL,
    status          inquiry_status_enum DEFAULT 'open',
    memo            TEXT,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);


-- 3. 인덱스
-- -----------------------------------------------------------------------------

-- 지역 검색 (활성 매물 전용)
CREATE INDEX idx_properties_region
    ON properties (sido, sigungu, dong)
    WHERE deleted_at IS NULL;

-- 유형 필터
CREATE INDEX idx_properties_type
    ON properties (property_type, trade_type)
    WHERE deleted_at IS NULL;

-- 매매가 범위
CREATE INDEX idx_properties_sale_price
    ON properties (sale_price)
    WHERE deleted_at IS NULL AND sale_price IS NOT NULL;

-- 보증금 범위
CREATE INDEX idx_properties_deposit
    ON properties (deposit)
    WHERE deleted_at IS NULL AND deposit IS NOT NULL;

-- 월세 범위
CREATE INDEX idx_properties_monthly_rent
    ON properties (monthly_rent)
    WHERE deleted_at IS NULL AND monthly_rent IS NOT NULL;

-- 면적 범위
CREATE INDEX idx_properties_area_exclusive
    ON properties (area_exclusive_m2)
    WHERE deleted_at IS NULL AND area_exclusive_m2 IS NOT NULL;

-- 활성 매물 상태 필터
CREATE INDEX idx_properties_active_status
    ON properties (status)
    WHERE deleted_at IS NULL;

-- 최신 매물 정렬
CREATE INDEX idx_properties_created_desc
    ON properties (created_at DESC);

-- JSONB 옵션/태그 포함 검색 (GIN)
CREATE INDEX idx_properties_options_gin
    ON properties USING GIN (options)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_properties_tags_gin
    ON properties USING GIN (tags)
    WHERE deleted_at IS NULL;

-- 변경이력 조회
CREATE INDEX idx_property_history_pid
    ON property_history (property_id, changed_at DESC);

-- 문의 조회
CREATE INDEX idx_inquiries_contact_id
    ON inquiries (contact_id);

CREATE INDEX idx_inquiries_property_id
    ON inquiries (property_id, created_at DESC);

-- 고객 전화번호 검색
CREATE INDEX idx_contacts_phone
    ON contacts (phone)
    WHERE phone IS NOT NULL AND deleted_at IS NULL;
