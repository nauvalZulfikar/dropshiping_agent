"""
AI-powered listing title, description, and tag generator.
Uses Claude API to create optimized marketplace listings.
"""
from typing import Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from core.config import ANTHROPIC_API_KEY
from core.logger import logger

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Kamu adalah spesialis listing marketplace Indonesia (Shopee, Tokopedia, TikTok Shop).
Tugasmu membuat judul dan deskripsi produk yang SEO-optimized untuk marketplace Indonesia.
Aturan:
- Judul max 120 karakter, include keyword utama di depan
- Deskripsi: fitur bullet points, bahan/material, ukuran, cara pakai
- Bahasa Indonesia natural, tidak spam keyword
- Tambahkan emoji yang relevan tapi jangan berlebihan
- Sertakan call-to-action di akhir deskripsi"""


class ListingContent(BaseModel):
    title: str
    description: str
    tags: list[str]


async def generate_listing(
    product_name: str,
    niche: str,
    key_features: Optional[str] = None,
    target_platform: str = "shopee",
    price_idr: Optional[int] = None,
) -> ListingContent:
    prompt = f"""Buat listing untuk marketplace {target_platform}:

Produk: {product_name}
Niche: {niche}
{"Harga: Rp " + f"{price_idr:,}" if price_idr else ""}
{"Fitur: " + key_features if key_features else ""}

Output dalam format:
JUDUL: [judul produk max 120 karakter]
DESKRIPSI: [deskripsi lengkap]
TAGS: [comma-separated tags, 5-10 tags]"""

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    # Parse response
    title = ""
    description = ""
    tags = []

    lines = text.split("\n")
    current_section = ""

    for line in lines:
        if line.startswith("JUDUL:"):
            title = line.replace("JUDUL:", "").strip()
            current_section = "title"
        elif line.startswith("DESKRIPSI:"):
            description = line.replace("DESKRIPSI:", "").strip()
            current_section = "desc"
        elif line.startswith("TAGS:"):
            tags_str = line.replace("TAGS:", "").strip()
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            current_section = "tags"
        elif current_section == "desc":
            description += "\n" + line

    description = description.strip()

    logger.info(
        "listing_generated",
        product=product_name, platform=target_platform,
        title_len=len(title), tokens=response.usage.output_tokens,
    )

    return ListingContent(title=title, description=description, tags=tags)
