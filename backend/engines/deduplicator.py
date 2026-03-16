"""
Cross-platform product deduplicator.

Strategy: when a new product_listing is saved, check if a canonical product
already exists for the same item across platforms. If so, link to it.
Otherwise create a new canonical product row.

Dedup methods (in priority order):
1. platform_product_id exact match (same seller listing scraped twice)
2. Title similarity (fuzzy match using token overlap)
3. CLIP image embedding similarity (if embeddings available)
"""
import re
import asyncpg
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Minimum title similarity ratio to consider products the same
_TITLE_SIMILARITY_THRESHOLD = 0.75
# Minimum CLIP similarity to merge products
_EMBEDDING_SIMILARITY_THRESHOLD = 0.92


async def find_or_create_canonical_product(
    conn: asyncpg.Connection,
    title: str,
    image_url: Optional[str] = None,
    category_id: Optional[str] = None,
) -> str:
    """
    Find an existing canonical product matching this title, or create a new one.
    Returns product_id (UUID string).

    Dedup logic:
    1. Exact title match → reuse
    2. High fuzzy title similarity → reuse
    3. No match → create new
    """
    # 1. Exact match
    row = await conn.fetchrow(
        "SELECT id FROM products WHERE canonical_name = $1 LIMIT 1",
        title
    )
    if row:
        return str(row["id"])

    # 2. Fuzzy title similarity against recent products
    candidates = await conn.fetch("""
        SELECT id, canonical_name
        FROM products
        WHERE canonical_name % $1         -- pg_trgm similarity operator
        ORDER BY canonical_name <-> $1    -- trigram distance
        LIMIT 5
    """, title)

    for candidate in candidates:
        sim = _token_similarity(title, candidate["canonical_name"])
        if sim >= _TITLE_SIMILARITY_THRESHOLD:
            logger.debug(
                f"[Dedup] Merged '{title[:40]}' → "
                f"'{candidate['canonical_name'][:40]}' (sim={sim:.2f})"
            )
            return str(candidate["id"])

    # 3. Create new canonical product
    row = await conn.fetchrow("""
        INSERT INTO products (canonical_name, canonical_image_url, category_id)
        VALUES ($1, $2, $3)
        RETURNING id
    """, title, image_url, category_id)
    return str(row["id"])


async def find_or_create_canonical_product_simple(
    conn: asyncpg.Connection,
    title: str,
    image_url: Optional[str] = None,
    category_id: Optional[str] = None,
) -> str:
    """
    Simplified dedup without pg_trgm (for DBs without the extension).
    Falls back to exact match only, then creates new.
    """
    row = await conn.fetchrow(
        "SELECT id FROM products WHERE canonical_name = $1 LIMIT 1",
        title
    )
    if row:
        return str(row["id"])

    row = await conn.fetchrow("""
        INSERT INTO products (canonical_name, canonical_image_url, category_id)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        RETURNING id
    """, title, image_url, category_id)

    if not row:
        row = await conn.fetchrow(
            "SELECT id FROM products WHERE canonical_name = $1 LIMIT 1",
            title
        )

    return str(row["id"]) if row else None


async def deduplicate_listings(conn: asyncpg.Connection) -> int:
    """
    Batch dedup pass: find product_listings with similar titles and
    merge them under the same product_id. Returns count of merges.
    """
    # Find listings that share the same canonical product by title similarity
    rows = await conn.fetch("""
        SELECT pl.id, pl.title, pl.product_id
        FROM product_listings pl
        WHERE pl.product_id IS NULL
           OR pl.product_id IN (
               SELECT id FROM products WHERE canonical_name = ''
           )
        LIMIT 200
    """)

    merged = 0
    for row in rows:
        try:
            product_id = await find_or_create_canonical_product_simple(
                conn, row["title"]
            )
            if product_id and str(product_id) != str(row["product_id"]):
                await conn.execute(
                    "UPDATE product_listings SET product_id = $1 WHERE id = $2",
                    product_id, row["id"]
                )
                merged += 1
        except Exception as exc:
            logger.debug(f"[Dedup] Merge failed for listing {row['id']}: {exc}")

    if merged:
        logger.info(f"[Dedup] Merged {merged} listings to canonical products")
    return merged


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _normalize(text: str) -> set[str]:
    """Tokenize and normalize a product title for similarity comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    # Remove short filler tokens
    return {t for t in tokens if len(t) > 2}


def _token_similarity(a: str, b: str) -> float:
    """Jaccard similarity between title token sets."""
    tokens_a = _normalize(a)
    tokens_b = _normalize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)
