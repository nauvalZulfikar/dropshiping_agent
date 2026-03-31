CREATE TABLE IF NOT EXISTS affiliate_links (
    id              SERIAL PRIMARY KEY,
    link_id         VARCHAR(16) UNIQUE NOT NULL,
    product_id      VARCHAR(100),
    product_name    VARCHAR(500),
    merchant        VARCHAR(100),
    niche           VARCHAR(100),
    channel         VARCHAR(50),
    campaign        VARCHAR(100),
    content_id      VARCHAR(100),
    affiliate_url   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS affiliate_performance (
    id              SERIAL PRIMARY KEY,
    link_id         VARCHAR(16) REFERENCES affiliate_links(link_id),
    date            DATE NOT NULL,
    clicks          INTEGER DEFAULT 0,
    conversions     INTEGER DEFAULT 0,
    gmv_idr         BIGINT DEFAULT 0,
    commission_idr  BIGINT DEFAULT 0,
    avg_order_value BIGINT DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(link_id, date)
);

CREATE TABLE IF NOT EXISTS niche_scores (
    id              SERIAL PRIMARY KEY,
    niche           VARCHAR(100),
    scored_at       TIMESTAMP DEFAULT NOW(),
    epc             DECIMAL(10,2),
    cvr             DECIMAL(6,4),
    total_clicks    INTEGER,
    avg_order_value BIGINT,
    trend           VARCHAR(10),
    score           DECIMAL(5,1),
    decision        VARCHAR(50),
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS content_pieces (
    id              SERIAL PRIMARY KEY,
    content_id      VARCHAR(50) UNIQUE,
    channel         VARCHAR(50),
    niche           VARCHAR(100),
    product_ids     JSONB,
    script          TEXT,
    published_at    TIMESTAMP,
    views           INTEGER DEFAULT 0,
    likes           INTEGER DEFAULT 0,
    status          VARCHAR(20)
);
