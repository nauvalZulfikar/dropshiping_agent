CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    platform        VARCHAR(50),
    platform_order_id VARCHAR(100) UNIQUE,
    product_id      INTEGER REFERENCES products(id),
    supplier_id     INTEGER REFERENCES suppliers(id),
    buyer_name      VARCHAR(200),
    buyer_phone     VARCHAR(20),
    shipping_address TEXT,
    city            VARCHAR(100),
    postal_code     VARCHAR(10),
    courier         VARCHAR(50),
    courier_service VARCHAR(50),
    quantity        INTEGER DEFAULT 1,
    sale_price_idr  INTEGER,
    cogs_idr        INTEGER,
    platform_fee_idr INTEGER,
    net_profit_idr  INTEGER,
    status          VARCHAR(50),
    resi            VARCHAR(100),
    sent_to_supplier_at TIMESTAMP,
    shipped_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id              SERIAL PRIMARY KEY,
    customer_phone  VARCHAR(20),
    platform        VARCHAR(50),
    role            VARCHAR(10),
    message         TEXT,
    escalated       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);
