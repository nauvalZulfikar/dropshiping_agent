CREATE TABLE IF NOT EXISTS suppliers (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200),
    wa_phone        VARCHAR(20),
    platform_url    TEXT,
    avg_response_min INTEGER,
    avg_delivery_day INTEGER,
    return_rate     DECIMAL(4,2),
    is_active       BOOLEAN DEFAULT TRUE,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    sku             VARCHAR(100) UNIQUE,
    name            VARCHAR(500),
    niche           VARCHAR(100),
    supplier_id     INTEGER REFERENCES suppliers(id),
    supplier_sku    VARCHAR(100),
    supplier_url    TEXT,
    cogs_idr        INTEGER,
    floor_margin    DECIMAL(4,2) DEFAULT 0.15,
    current_price   INTEGER,
    stock           INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    platform_ids    JSONB,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
