"""
Seed the categories table with Indonesian e-commerce product taxonomy.
Run: python scripts/seed_categories.py
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

CATEGORIES = [
    # (slug, name, parent_slug)
    ("fashion-wanita", "Fashion Wanita", None),
    ("tas-wanita", "Tas Wanita", "fashion-wanita"),
    ("baju-wanita", "Baju Wanita", "fashion-wanita"),
    ("sepatu-wanita", "Sepatu Wanita", "fashion-wanita"),
    ("aksesoris-wanita", "Aksesoris Wanita", "fashion-wanita"),

    ("fashion-pria", "Fashion Pria", None),
    ("sepatu-pria", "Sepatu Pria", "fashion-pria"),
    ("baju-pria", "Baju Pria", "fashion-pria"),
    ("tas-pria", "Tas Pria", "fashion-pria"),

    ("kecantikan", "Kecantikan & Perawatan", None),
    ("skincare", "Skincare", "kecantikan"),
    ("makeup", "Makeup", "kecantikan"),
    ("parfum", "Parfum", "kecantikan"),
    ("perawatan-rambut", "Perawatan Rambut", "kecantikan"),

    ("elektronik", "Elektronik", None),
    ("aksesoris-hp", "Aksesoris HP", "elektronik"),
    ("headphone", "Headphone & Earphone", "elektronik"),
    ("charger-kabel", "Charger & Kabel", "elektronik"),
    ("smartwatch", "Smartwatch", "elektronik"),

    ("rumah-tangga", "Rumah Tangga", None),
    ("peralatan-dapur", "Peralatan Dapur", "rumah-tangga"),
    ("dekorasi-rumah", "Dekorasi Rumah", "rumah-tangga"),
    ("perlengkapan-tidur", "Perlengkapan Tidur", "rumah-tangga"),

    ("olahraga", "Olahraga & Outdoor", None),
    ("jam-tangan", "Jam Tangan", "olahraga"),
    ("perlengkapan-gym", "Perlengkapan Gym", "olahraga"),

    ("mainan", "Mainan & Hobi", None),
    ("mainan-anak", "Mainan Anak", "mainan"),
    ("action-figure", "Action Figure", "mainan"),

    ("otomotif", "Otomotif", None),
    ("aksesoris-motor", "Aksesoris Motor", "otomotif"),
    ("aksesoris-mobil", "Aksesoris Mobil", "otomotif"),
]


async def seed():
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        return

    conn = await asyncpg.connect(db_url)
    try:
        # First pass: insert root categories
        slug_to_id: dict[str, str] = {}
        for slug, name, parent_slug in CATEGORIES:
            if parent_slug is not None:
                continue
            row = await conn.fetchrow("""
                INSERT INTO categories (name, slug, level)
                VALUES ($1, $2, 0)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, name, slug)
            slug_to_id[slug] = str(row["id"])
            print(f"  Inserted root: {name} ({slug})")

        # Second pass: insert child categories
        for slug, name, parent_slug in CATEGORIES:
            if parent_slug is None:
                continue
            parent_id = slug_to_id.get(parent_slug)
            row = await conn.fetchrow("""
                INSERT INTO categories (name, slug, parent_id, level)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, parent_id = EXCLUDED.parent_id
                RETURNING id
            """, name, slug, parent_id)
            slug_to_id[slug] = str(row["id"])
            print(f"  Inserted child: {name} ({slug}) → parent: {parent_slug}")

        print(f"\nSeeded {len(CATEGORIES)} categories successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
