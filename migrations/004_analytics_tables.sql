CREATE TABLE IF NOT EXISTS price_history (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(id),
    price           INTEGER,
    competitor_avg  INTEGER,
    recorded_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_segments (
    id              SERIAL PRIMARY KEY,
    customer_phone  VARCHAR(20),
    segment         VARCHAR(50),
    recency_days    INTEGER,
    frequency       INTEGER,
    monetary_idr    BIGINT,
    scored_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_products_niche ON products(niche);
CREATE INDEX IF NOT EXISTS idx_affiliate_perf_date ON affiliate_performance(date);
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(customer_phone);
