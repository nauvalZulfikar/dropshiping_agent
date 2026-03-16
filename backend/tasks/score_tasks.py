"""
Celery tasks for computing opportunity scores.

Tasks:
- score_all_products:   batch score all unscored/stale listings
- score_single_listing: on-demand score for one listing
- embed_product_images: batch CLIP embed all products missing embeddings
- match_suppliers:      batch link suppliers to products via image similarity
"""
import asyncio
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Tasks
# ------------------------------------------------------------------

@celery_app.task(name="tasks.score_tasks.score_all_products")
def score_all_products():
    """Iterate all unscored/stale listings and compute opportunity score."""
    return asyncio.run(_score_all_async())


@celery_app.task(name="tasks.score_tasks.score_single_listing")
def score_single_listing(listing_id: str):
    """On-demand scoring for a single listing (called after new scrape)."""
    from engines.opportunity_scorer import compute_opportunity_score
    try:
        return asyncio.run(compute_opportunity_score(listing_id))
    except Exception as exc:
        logger.error(f"[ScoreTask] score_single_listing failed for {listing_id}: {exc}")
        raise


@celery_app.task(name="tasks.score_tasks.embed_product_images")
def embed_product_images():
    """Batch CLIP-embed all products that are missing image embeddings."""
    return asyncio.run(_embed_images_async())


@celery_app.task(name="tasks.score_tasks.match_suppliers")
def match_suppliers():
    """Batch match unlinked suppliers to products via CLIP similarity."""
    return asyncio.run(_match_suppliers_async())


# ------------------------------------------------------------------
# Async implementations
# ------------------------------------------------------------------

async def _score_all_async() -> dict:
    """
    Fetch all unscored or stale listings (not scored in last 2h).
    Score in batches of 500. Logs failures without crashing.
    """
    import asyncpg
    from config import settings
    from engines.opportunity_scorer import compute_opportunity_score

    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch("""
            SELECT pl.id
            FROM product_listings pl
            LEFT JOIN product_scores ps ON ps.listing_id = pl.id
            WHERE pl.is_active = TRUE
              AND (ps.id IS NULL OR ps.computed_at < NOW() - INTERVAL '2 hours')
            ORDER BY pl.created_at DESC
            LIMIT 500
        """)
    finally:
        await conn.close()

    scored = 0
    failed = 0
    for row in rows:
        try:
            await compute_opportunity_score(str(row["id"]))
            scored += 1
        except Exception as exc:
            logger.warning(f"[ScoreTask] Scoring failed for listing {row['id']}: {exc}")
            failed += 1

    logger.info(f"[ScoreTask] Batch complete: scored={scored}, failed={failed}, total={len(rows)}")
    return {"scored": scored, "failed": failed, "total": len(rows)}


async def _embed_images_async() -> dict:
    """
    Find products with a canonical_image_url but no embedding,
    compute CLIP embeddings, and store them.
    """
    import asyncpg
    from config import settings
    from engines.supplier_matcher import store_product_embedding

    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch("""
            SELECT id, canonical_image_url
            FROM products
            WHERE canonical_image_url IS NOT NULL
              AND canonical_image_url != ''
              AND image_embedding IS NULL
            LIMIT 100
        """)
    finally:
        await conn.close()

    embedded = 0
    failed = 0
    for row in rows:
        try:
            conn2 = await asyncpg.connect(settings.database_url)
            try:
                await store_product_embedding(conn2, str(row["id"]), row["canonical_image_url"])
                embedded += 1
            finally:
                await conn2.close()
        except Exception as exc:
            logger.warning(f"[ScoreTask] Embedding failed for product {row['id']}: {exc}")
            failed += 1

    logger.info(f"[ScoreTask] Image embedding: embedded={embedded}, failed={failed}")
    return {"embedded": embedded, "failed": failed}


async def _match_suppliers_async() -> dict:
    """
    For each unlinked supplier (product_id IS NULL), try to match
    it to a canonical product via CLIP similarity.
    """
    import asyncpg
    from config import settings
    from engines.supplier_matcher import embed_and_match_new_product

    conn = await asyncpg.connect(settings.database_url)
    try:
        # Find products that have embeddings but unlinked suppliers with images
        products = await conn.fetch("""
            SELECT id, canonical_image_url
            FROM products
            WHERE image_embedding IS NOT NULL
            LIMIT 50
        """)
    finally:
        await conn.close()

    matched = 0
    for product in products:
        try:
            matches = await embed_and_match_new_product(
                str(product["id"]),
                product["canonical_image_url"],
            )
            matched += len([m for m in matches if m.get("similarity", 0) > 0.85])
        except Exception as exc:
            logger.debug(f"[ScoreTask] Supplier match failed for product {product['id']}: {exc}")

    logger.info(f"[ScoreTask] Supplier matching: linked={matched}")
    return {"matched": matched}
