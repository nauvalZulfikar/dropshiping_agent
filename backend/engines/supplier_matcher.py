"""
Supplier matcher — image-based similarity using CLIP embeddings + pgvector.

Strategy (AGENTS.md §3.5):
1. Download product image → compute CLIP embedding (512-dim vector)
2. Store embedding in products.image_embedding
3. For supplier matching: find suppliers whose image is most similar
   via pgvector cosine similarity
4. On new product saved, enqueue embedding task via Celery
"""
import asyncio
import io
import logging
from typing import Optional

import asyncpg
import httpx
import numpy as np

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# CLIP model name — ViT-B/32 produces 512-dim vectors matching the schema
_CLIP_MODEL = "clip-ViT-B-32"
_model = None  # lazy-loaded singleton


def _get_model():
    """Lazy-load CLIP model — only instantiated when first needed."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[SupplierMatcher] Loading CLIP model: {_CLIP_MODEL}")
            _model = SentenceTransformer(_CLIP_MODEL)
            logger.info("[SupplierMatcher] CLIP model loaded")
        except ImportError:
            logger.error("[SupplierMatcher] sentence-transformers not installed")
            raise
    return _model


async def embed_image(image_url: str) -> Optional[np.ndarray]:
    """
    Download image from URL and compute CLIP embedding.
    Returns numpy array of shape (512,), or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            image_bytes = resp.content
    except Exception as exc:
        logger.warning(f"[SupplierMatcher] Image download failed ({image_url[:60]}): {exc}")
        return None

    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Run in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, _encode_image, image)
        return embedding
    except Exception as exc:
        logger.warning(f"[SupplierMatcher] Embedding failed: {exc}")
        return None


def _encode_image(image) -> np.ndarray:
    """Synchronous CLIP encode — called via run_in_executor."""
    model = _get_model()
    embedding = model.encode(image, convert_to_numpy=True)
    # Normalize to unit vector for cosine similarity
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding.astype(np.float32)


async def store_product_embedding(conn: asyncpg.Connection, product_id: str, image_url: str):
    """
    Compute and store CLIP embedding for a product's canonical image.
    Updates products.image_embedding.
    """
    embedding = await embed_image(image_url)
    if embedding is None:
        return

    # pgvector expects the embedding as a list
    embedding_list = embedding.tolist()
    await conn.execute("""
        UPDATE products
        SET image_embedding = $1::vector, canonical_image_url = $2
        WHERE id = $3
    """, str(embedding_list), image_url, product_id)
    logger.info(f"[SupplierMatcher] Stored embedding for product {product_id[:8]}...")


async def match_supplier_to_product(
    conn: asyncpg.Connection,
    product_id: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Find top-k suppliers whose image is most similar to the product's CLIP embedding.
    Uses pgvector cosine similarity on products.image_embedding vs supplier images.

    Returns list of supplier dicts sorted by similarity desc.
    """
    # Get product embedding
    product = await conn.fetchrow(
        "SELECT image_embedding FROM products WHERE id = $1",
        product_id
    )
    if not product or not product["image_embedding"]:
        logger.debug(f"[SupplierMatcher] No embedding for product {product_id}")
        return []

    # Find suppliers without product_id linkage (unmatched) and compute similarity
    rows = await conn.fetch("""
        SELECT
            s.id, s.title, s.url, s.price_idr, s.shipping_cost_idr,
            s.moq, s.seller_name, s.rating, s.source,
            1 - (p.image_embedding <=> $1::vector) AS similarity
        FROM suppliers s
        JOIN products p ON p.id = $2
        WHERE s.image_url IS NOT NULL
        ORDER BY similarity DESC
        LIMIT $3
    """, str(product["image_embedding"]), product_id, top_k)

    return [dict(r) for r in rows]


async def embed_and_match_new_product(product_id: str, image_url: str):
    """
    Full pipeline: embed a new product's image then find matching suppliers.
    Called from Celery task after new product saved.
    """
    conn = await asyncpg.connect(settings.asyncpg_url)
    try:
        await store_product_embedding(conn, product_id, image_url)
        matches = await match_supplier_to_product(conn, product_id, top_k=3)

        # Link top supplier to product if not already linked
        for match in matches:
            if match.get("similarity", 0) > 0.85:
                await conn.execute("""
                    UPDATE suppliers SET product_id = $1
                    WHERE id = $2 AND product_id IS NULL
                """, product_id, match["id"])
                logger.info(
                    f"[SupplierMatcher] Linked supplier {match['id'][:8]}... "
                    f"to product {product_id[:8]}... (sim={match['similarity']:.3f})"
                )

        return matches
    finally:
        await conn.close()
