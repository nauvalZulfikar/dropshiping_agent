"""
UTM link builder + DB logger.
Generates trackable affiliate links and logs them to database.
"""
import secrets
import string
from typing import Optional

from core.db import execute, fetchval
from core.logger import logger


def _generate_link_id(length: int = 12) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def create_affiliate_link(
    affiliate_url: str,
    product_id: Optional[str] = None,
    product_name: Optional[str] = None,
    merchant: str = "involve_asia",
    niche: str = "",
    channel: str = "",
    campaign: str = "",
    content_id: Optional[str] = None,
) -> dict:
    link_id = _generate_link_id()

    utm_params = (
        f"utm_source={channel}"
        f"&utm_medium=affiliate"
        f"&utm_campaign={campaign}"
        f"&utm_content={link_id}"
    )

    separator = "&" if "?" in affiliate_url else "?"
    tracked_url = f"{affiliate_url}{separator}{utm_params}"

    await execute(
        "INSERT INTO affiliate_links "
        "(link_id, product_id, product_name, merchant, niche, channel, campaign, content_id, affiliate_url) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        link_id, product_id, product_name, merchant, niche, channel, campaign, content_id, tracked_url,
    )

    logger.info(
        "affiliate_link_created",
        link_id=link_id, niche=niche, channel=channel, merchant=merchant,
    )

    return {
        "link_id": link_id,
        "url": tracked_url,
        "niche": niche,
        "channel": channel,
    }


async def get_link_by_id(link_id: str) -> Optional[dict]:
    row = await fetchval(
        "SELECT link_id, product_name, merchant, niche, channel, affiliate_url "
        "FROM affiliate_links WHERE link_id = $1",
        link_id,
    )
    return dict(row) if row else None


async def get_links_by_niche(niche: str) -> list[dict]:
    from core.db import fetch
    rows = await fetch(
        "SELECT link_id, product_name, merchant, channel, affiliate_url, created_at "
        "FROM affiliate_links WHERE niche = $1 ORDER BY created_at DESC",
        niche,
    )
    return [dict(r) for r in rows]
