"""
AI-powered content generator using Claude API.
Generates scripts for TikTok, IG, YouTube, blog posts.
"""
from typing import Optional

from anthropic import AsyncAnthropic

from core.config import ANTHROPIC_API_KEY
from core.db import execute
from core.logger import logger

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Kamu adalah copywriter Indonesia yang ahli membuat konten affiliate marketing.
Target audiens: usia 18-35 tahun, aktif di social media, suka belanja online.
Gaya bahasa: casual, relatable, pakai bahasa Indonesia sehari-hari (boleh campur bahasa gaul).
Tujuan: buat audiens tertarik klik link affiliate tanpa terasa hard-selling."""

CHANNEL_PROMPTS = {
    "tiktok": """Buat script TikTok 30-60 detik untuk produk berikut.
Format:
- Hook (3 detik pertama — harus bikin penonton berhenti scroll)
- Problem (masalah yang dirasakan target audiens)
- Solution (produk ini sebagai solusi)
- CTA (ajak klik link di bio)

Panjang: 100-150 kata. Tambahkan instruksi visual [dalam kurung siku].""",

    "ig": """Buat caption Instagram untuk produk berikut.
Format:
- Hook di baris pertama (max 125 karakter supaya tidak terpotong)
- Story/pengalaman personal (2-3 paragraf pendek)
- CTA (ajak klik link di bio)
- 5-10 hashtag relevan

Panjang: 150-250 kata.""",

    "youtube": """Buat script YouTube Shorts 60 detik untuk produk berikut.
Format:
- Hook (5 detik pertama)
- Demo/review singkat
- Pros & cons (jujur, bukan hard sell)
- CTA (link di deskripsi)

Panjang: 150-200 kata. Tambahkan instruksi visual [dalam kurung siku].""",

    "blog": """Buat artikel blog review produk berikut.
Format:
- Judul SEO-friendly (include keyword utama)
- Intro (1 paragraf, langsung ke poin)
- Fitur utama (3-5 bullet points)
- Kelebihan & kekurangan
- Kesimpulan + CTA

Panjang: 400-600 kata. Optimasi untuk keyword yang relevan.""",
}


async def generate_content(
    channel: str,
    niche: str,
    product_name: str,
    product_url: str,
    price_idr: Optional[int] = None,
    key_features: Optional[str] = None,
    content_id: Optional[str] = None,
) -> dict:
    channel_prompt = CHANNEL_PROMPTS.get(channel, CHANNEL_PROMPTS["ig"])

    user_prompt = f"""{channel_prompt}

Produk: {product_name}
Niche: {niche}
{"Harga: Rp " + f"{price_idr:,}" if price_idr else ""}
{"Fitur utama: " + key_features if key_features else ""}
Link: {product_url}"""

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    script = response.content[0].text

    if content_id:
        await execute(
            "INSERT INTO content_pieces (content_id, channel, niche, script, status) "
            "VALUES ($1, $2, $3, $4, 'draft') "
            "ON CONFLICT (content_id) DO UPDATE SET script = $4",
            content_id, channel, niche, script,
        )

    logger.info(
        "content_generated",
        channel=channel, niche=niche, product=product_name,
        tokens_used=response.usage.output_tokens,
    )

    return {
        "content_id": content_id,
        "channel": channel,
        "niche": niche,
        "script": script,
    }
