-- ================================================================
-- Проєкт «Дані» | Схема бази даних
-- Зберігання статистичних даних Укрстату
-- ================================================================

-- Розширення
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Довідники
-- ================================================================

-- Регіони України
CREATE TABLE regions (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    koatuu_code CHAR(10), -- Код КОАТУУ
    region_type VARCHAR(20) CHECK (region_type IN ('oblast', 'city', 'raion')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Категорії статистичних показників
CREATE TABLE indicator_categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL UNIQUE, -- напр. "Ринок праці"
    slug        VARCHAR(100) NOT NULL UNIQUE, -- напр. "labour_market"
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Одиниці виміру
CREATE TABLE units (
    id     SERIAL PRIMARY KEY,
    name   VARCHAR(100) NOT NULL UNIQUE, -- напр. "грн", "тис. осіб", "%"
    symbol VARCHAR(20)
);

-- 2. Довідник показників
CREATE TABLE indicators (
    id           SERIAL PRIMARY KEY,
    category_id  INT NOT NULL REFERENCES indicator_categories(id),
    name         VARCHAR(500) NOT NULL, -- повна назва показника
    short_name   VARCHAR(200),
    unit_id      INT REFERENCES units(id),
    source_table VARCHAR(200), -- назва таблиці Укрстату
    source_url   TEXT, -- посилання на першоджерело
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, category_id)
);

-- 3. Факти (значення показників)
CREATE TABLE stat_values (
    id             BIGSERIAL PRIMARY KEY,
    indicator_id   INT NOT NULL REFERENCES indicators(id),
    region_id      INT REFERENCES regions(id), -- NULL = загальнонаціональне
    period_year    SMALLINT NOT NULL,
    period_month   SMALLINT CHECK (period_month BETWEEN 1 AND 12),  -- NULL = річне
    value          NUMERIC(18, 4),
    is_estimated   BOOLEAN DEFAULT FALSE, -- позначка "оцінка"
    is_preliminary BOOLEAN DEFAULT FALSE, -- "попередні дані"
    raw_value      TEXT, -- оригінальний рядок з Excel (для аудиту)
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (indicator_id, region_id, period_year, period_month)
);

-- 4. Журнал завантажень (ETL audit log)
CREATE TABLE import_logs (
    id             BIGSERIAL PRIMARY KEY,
    source_file    TEXT NOT NULL,
    sheet_name     VARCHAR(200),
    rows_parsed    INT DEFAULT 0,
    rows_inserted  INT DEFAULT 0,
    rows_skipped   INT DEFAULT 0,
    errors         JSONB, -- масив помилок рядків
    status         VARCHAR(20) CHECK (status IN ('success', 'partial', 'failed')),
    started_at     TIMESTAMPTZ DEFAULT NOW(),
    finished_at    TIMESTAMPTZ
);

-- 5. Індекси для швидкого пошуку
CREATE INDEX idx_stat_values_indicator ON stat_values (indicator_id);
CREATE INDEX idx_stat_values_region    ON stat_values (region_id);
CREATE INDEX idx_stat_values_year      ON stat_values (period_year);
CREATE INDEX idx_stat_values_composite ON stat_values (indicator_id, region_id, period_year);

-- 6. Корисне view для дашбордів
CREATE VIEW v_stat_dashboard AS
SELECT
    sv.id,
    ic.name AS category,
    i.name AS indicator,
    i.short_name,
    u.symbol AS unit,
    r.name AS region,
    sv.period_year AS year,
    sv.period_month AS month,
    sv.value,
    sv.is_estimated,
    sv.is_preliminary
FROM stat_values sv
JOIN indicators i ON sv.indicator_id = i.id
JOIN indicator_categories ic ON i.category_id = ic.id
LEFT JOIN regions r ON sv.region_id = r.id
LEFT JOIN units u ON i.unit_id = u.id;

-- 7. Seed-дані (базові довідники)
INSERT INTO units (name, symbol) VALUES
    ('гривня',          'грн'),
    ('тисяча гривень',  'тис. грн'),
    ('мільйон гривень', 'млн грн'),
    ('відсоток',        '%'),
    ('тисяча осіб',     'тис. осіб'),
    ('особа',           'осіб'),
    ('одиниця',         'од.');

INSERT INTO indicator_categories (name, slug) VALUES
    ('Ринок праці',                'labour_market'),
    ('Демографія',                 'demography'),
    ('Промисловість',              'industry'),
    ('Сільське господарство',      'agriculture'),
    ('Зовнішня торгівля',          'foreign_trade'),
    ('Валовий внутрішній продукт', 'gdp');

INSERT INTO regions (name, region_type) VALUES
    ('Вінницька область',         'oblast'),
    ('Дніпропетровська область',  'oblast'),
    ('Івано-Франківська область', 'oblast'),
    ('Київська область',          'oblast'),
    ('Львівська область',         'oblast'),
    ('Харківська область',        'oblast'),
    ('Одеська область',           'oblast'),
    ('м. Київ',                   'city');
