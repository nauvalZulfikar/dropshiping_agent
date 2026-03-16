import logging
import httpx
from functools import lru_cache

logger = logging.getLogger(__name__)

# Fallback rate if Bank Indonesia API is unavailable
_FALLBACK_IDR_PER_USD = 15_800


async def fetch_usd_to_idr_rate() -> float:
    """
    Fetch the current USD/IDR exchange rate from Bank Indonesia open data.
    Falls back to hardcoded rate if the API is unavailable.
    """
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=IDR"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rate = data["rates"]["IDR"]
            logger.info(f"USD/IDR rate fetched: {rate}")
            return float(rate)
    except Exception as exc:
        logger.warning(f"Failed to fetch USD/IDR rate: {exc}. Using fallback: {_FALLBACK_IDR_PER_USD}")
        return float(_FALLBACK_IDR_PER_USD)


def usd_to_idr(usd_amount: float, rate: float = _FALLBACK_IDR_PER_USD) -> int:
    """Convert USD amount to IDR integer (always store as BIGINT)."""
    return int(round(usd_amount * rate))


def format_idr(amount_idr: int) -> str:
    """Format an integer IDR amount as human-readable string, e.g. Rp 15.000."""
    return f"Rp {amount_idr:,.0f}".replace(",", ".")


def parse_idr_string(raw: str) -> int:
    """
    Parse IDR price strings from scraped pages into integer.
    Handles formats: 'Rp 15.000', '15.000', '15,000', 'IDR15000'
    """
    cleaned = raw.upper().replace("RP", "").replace("IDR", "").strip()
    # Remove thousand separators (both . and ,) — Indonesian uses '.' as thousands separator
    cleaned = cleaned.replace(".", "").replace(",", "")
    try:
        return int(cleaned)
    except ValueError:
        logger.warning(f"Could not parse IDR string: '{raw}'")
        return 0


def parse_sold_count(raw: str) -> int:
    """
    Parse sold count strings:
    - '1,2rb terjual' → 1200  (Tokopedia format)
    - '1.2K sold'     → 1200  (Shopee format)
    - '1200'          → 1200
    """
    if not raw:
        return 0
    s = raw.lower().replace("terjual", "").replace("sold", "").strip()
    s = s.replace(",", ".")
    try:
        if "rb" in s or "k" in s:
            s = s.replace("rb", "").replace("k", "").strip()
            return int(round(float(s) * 1000))
        if "jt" in s or "m" in s:
            s = s.replace("jt", "").replace("m", "").strip()
            return int(round(float(s) * 1_000_000))
        return int(float(s))
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse sold count: '{raw}'")
        return 0
