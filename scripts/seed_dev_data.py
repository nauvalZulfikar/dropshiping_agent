"""
Generate realistic seed data for development dashboard.
Run: python scripts/seed_dev_data.py
"""
import asyncio
import random
import string
from datetime import datetime, timedelta

import asyncpg

DATABASE_URL = "postgresql://dropship:dropship123@localhost:5432/dropship"

NICHES = ["skincare", "aksesori hp", "peralatan dapur", "fashion wanita", "suplemen"]
CHANNELS = ["tiktok", "ig", "youtube", "blog"]
PLATFORMS = ["shopee", "tokopedia", "tiktok"]
COURIERS = ["JNE", "J&T", "SiCepat", "AnterAja"]
CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Medan", "Semarang",
    "Makassar", "Palembang", "Tangerang", "Depok", "Bekasi",
]
STATUSES = ["new", "sent_to_supplier", "shipped", "delivered", "returned"]

PRODUCTS_BY_NICHE = {
    "skincare": [
        ("Serum Vitamin C", 25000, 89000),
        ("Sunscreen SPF 50", 18000, 65000),
        ("Moisturizer Aloe Vera", 12000, 45000),
        ("Facial Wash Gentle", 15000, 55000),
        ("Sheet Mask Pack 10pcs", 20000, 79000),
        ("Toner Centella", 22000, 75000),
    ],
    "aksesori hp": [
        ("Case iPhone 15 Clear", 8000, 35000),
        ("Tempered Glass Samsung", 5000, 25000),
        ("Ring Holder Magnetic", 6000, 28000),
        ("Kabel Type-C 2m", 7000, 32000),
        ("Earphone TWS Mini", 35000, 129000),
        ("Powerbank 10000mAh", 55000, 189000),
    ],
    "peralatan dapur": [
        ("Pisau Chef Stainless", 25000, 89000),
        ("Talenan Bambu", 12000, 45000),
        ("Set Spatula Silikon", 15000, 55000),
        ("Wadah Bumbu Set 6pcs", 18000, 65000),
        ("Gelas Ukur 500ml", 8000, 32000),
        ("Saringan Minyak", 10000, 39000),
    ],
    "fashion wanita": [
        ("Hijab Pashmina", 15000, 55000),
        ("Tas Selempang Mini", 28000, 99000),
        ("Kaos Oversized", 22000, 79000),
        ("Celana Kulot", 30000, 109000),
        ("Sandal Platform", 25000, 89000),
        ("Gelang Set 5pcs", 8000, 35000),
    ],
    "suplemen": [
        ("Vitamin C 1000mg", 20000, 75000),
        ("Multivitamin Daily", 35000, 129000),
        ("Omega 3 Fish Oil", 40000, 149000),
        ("Collagen Drink", 28000, 99000),
        ("Probiotik Kapsul", 32000, 119000),
        ("Zinc Tablet", 15000, 55000),
    ],
}


def rand_phone() -> str:
    return f"628{random.randint(100000000, 999999999)}"


def rand_link_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=12))


async def seed():
    conn = await asyncpg.connect(DATABASE_URL)

    # Clear existing data
    for table in [
        "conversations", "orders", "price_history", "customer_segments",
        "products", "suppliers", "content_pieces", "niche_scores",
        "affiliate_performance", "affiliate_links",
    ]:
        await conn.execute(f"DELETE FROM {table}")
    print("Cleared existing data")

    # --- Suppliers ---
    supplier_ids = []
    suppliers = [
        ("Supplier Guangzhou A", "8613800138000", 45, 5, 0.03),
        ("Supplier Shenzhen B", "8613900139000", 30, 4, 0.02),
        ("Supplier Jakarta C", "6281234567890", 15, 2, 0.04),
    ]
    for name, phone, resp_min, delivery_day, return_rate in suppliers:
        sid = await conn.fetchval(
            "INSERT INTO suppliers (name, wa_phone, avg_response_min, avg_delivery_day, return_rate) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING id",
            name, phone, resp_min, delivery_day, return_rate,
        )
        supplier_ids.append(sid)
    print(f"Seeded {len(supplier_ids)} suppliers")

    # --- Products ---
    product_ids = []
    for niche, products in PRODUCTS_BY_NICHE.items():
        for name, cogs, price in products:
            sku = f"SKU-{rand_link_id()[:6].upper()}"
            pid = await conn.fetchval(
                "INSERT INTO products (sku, name, niche, supplier_id, cogs_idr, current_price, stock, platform_ids) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id",
                sku, name, niche, random.choice(supplier_ids), cogs, price,
                random.randint(0, 100),
                f'{{"shopee": "SP{random.randint(10000,99999)}", "tokopedia": "TP{random.randint(10000,99999)}"}}',
            )
            product_ids.append((pid, niche, cogs, price))
    print(f"Seeded {len(product_ids)} products")

    # --- Affiliate links + performance ---
    now = datetime.now()
    link_count = 0
    for niche in NICHES:
        for channel in CHANNELS:
            for i in range(3):
                link_id = rand_link_id()
                await conn.execute(
                    "INSERT INTO affiliate_links (link_id, product_name, merchant, niche, channel, campaign, affiliate_url) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    link_id,
                    f"Produk {niche.title()} #{i+1}",
                    random.choice(["involve_asia", "shopee", "tiktok"]),
                    niche, channel,
                    f"campaign_{niche}_{channel}",
                    f"https://affiliate.example.com/{link_id}",
                )

                # Performance data for 30 days
                base_epc = {"skincare": 3500, "aksesori hp": 2000, "peralatan dapur": 1500, "fashion wanita": 4000, "suplemen": 2800}
                for day_offset in range(30):
                    date = (now - timedelta(days=day_offset)).date()
                    clicks = random.randint(5, 80)
                    cvr = random.uniform(0.01, 0.08)
                    conversions = max(0, int(clicks * cvr))
                    aov = random.randint(50000, 300000)
                    gmv = conversions * aov
                    epc = base_epc.get(niche, 2000) * random.uniform(0.6, 1.5)
                    commission = int(gmv * random.uniform(0.03, 0.10))

                    await conn.execute(
                        "INSERT INTO affiliate_performance (link_id, date, clicks, conversions, gmv_idr, commission_idr, avg_order_value) "
                        "VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT DO NOTHING",
                        link_id, date, clicks, conversions, gmv, commission, aov,
                    )
                link_count += 1
    print(f"Seeded {link_count} affiliate links with 30 days performance")

    # --- Niche scores ---
    for niche in NICHES:
        base_epc = {"skincare": 3500, "aksesori hp": 2000, "peralatan dapur": 1500, "fashion wanita": 4000, "suplemen": 2800}
        epc = base_epc.get(niche, 2000) * random.uniform(0.8, 1.2)
        cvr = random.uniform(0.015, 0.06)
        clicks = random.randint(200, 3000)
        aov = random.randint(80000, 250000)
        trend = random.choice(["up", "flat", "down"])

        score = 0
        if epc >= 5000: score += 35
        elif epc >= 2000: score += 25
        elif epc >= 800: score += 15
        if cvr >= 0.05: score += 25
        elif cvr >= 0.025: score += 18
        elif cvr >= 0.01: score += 10
        if aov >= 300000: score += 20
        elif aov >= 150000: score += 14
        if clicks >= 2000: score += 10
        elif clicks >= 500: score += 7
        if trend == "up": score += 10

        if score >= 65 and clicks >= 200:
            decision = "flip_to_dropship"
        elif score >= 45 and clicks >= 100:
            decision = "scale_affiliate"
        elif score >= 25:
            decision = "optimize"
        else:
            decision = "abandon"

        await conn.execute(
            "INSERT INTO niche_scores (niche, epc, cvr, total_clicks, avg_order_value, trend, score, decision) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            niche, epc, cvr, clicks, aov, trend, score, decision,
        )
    print(f"Seeded {len(NICHES)} niche scores")

    # --- Orders (90 days) ---
    order_count = 0
    for day_offset in range(90):
        date = now - timedelta(days=day_offset)
        daily_orders = random.randint(2, 15)

        # More orders on payday (1, 2, 25, 26, 27)
        if date.day in [1, 2, 25, 26, 27]:
            daily_orders = int(daily_orders * 1.5)

        # Harbolnas
        if date.day == date.month and date.month <= 12:
            daily_orders = int(daily_orders * 2.5)

        for _ in range(daily_orders):
            pid, niche, cogs, price = random.choice(product_ids)
            sid = random.choice(supplier_ids)
            platform = random.choice(PLATFORMS)
            platform_fee = int(price * 0.08)
            net_profit = price - cogs - platform_fee
            qty = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]

            # Weighted status — older orders more likely delivered
            if day_offset < 2:
                status = random.choices(STATUSES[:3], weights=[0.3, 0.4, 0.3])[0]
            elif day_offset < 7:
                status = random.choices(STATUSES, weights=[0.05, 0.1, 0.3, 0.5, 0.05])[0]
            else:
                status = random.choices(STATUSES, weights=[0.01, 0.02, 0.05, 0.87, 0.05])[0]

            order_time = date.replace(
                hour=random.randint(6, 23),
                minute=random.randint(0, 59),
            )

            await conn.execute(
                "INSERT INTO orders (platform, platform_order_id, product_id, supplier_id, "
                "buyer_name, buyer_phone, shipping_address, city, postal_code, courier, courier_service, "
                "quantity, sale_price_idr, cogs_idr, platform_fee_idr, net_profit_idr, status, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)",
                platform,
                f"{platform.upper()}-{random.randint(1000000, 9999999)}",
                pid, sid,
                f"Buyer {random.randint(100, 999)}",
                rand_phone(),
                f"Jl. Contoh No.{random.randint(1, 200)}",
                random.choice(CITIES),
                f"{random.randint(10000, 99999)}",
                random.choice(COURIERS),
                random.choice(["REG", "YES", "OKE"]),
                qty, price * qty, cogs * qty, platform_fee * qty, net_profit * qty,
                status, order_time,
            )
            order_count += 1
    print(f"Seeded {order_count} orders (90 days)")

    # --- Conversations ---
    conv_count = 0
    escalation_keywords = ["refund", "palsu", "belum sampai", "kecewa", "mau retur"]
    normal_messages = [
        "Kak, barangnya ready?",
        "Kapan ya estimasi sampainya?",
        "Warna lain ada kak?",
        "Bisa COD gak?",
        "Makasih kak, barangnya udah sampai!",
        "Apakah bisa request packaging bubble wrap?",
        "Harga bisa kurang gak kak?",
    ]
    for _ in range(200):
        phone = rand_phone()
        platform = random.choice(PLATFORMS)
        is_escalated = random.random() < 0.12

        msg = random.choice(escalation_keywords if is_escalated else normal_messages)
        created = now - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))

        await conn.execute(
            "INSERT INTO conversations (customer_phone, platform, role, message, escalated, created_at) "
            "VALUES ($1, $2, 'user', $3, $4, $5)",
            phone, platform, msg, is_escalated, created,
        )

        # Bot reply
        await conn.execute(
            "INSERT INTO conversations (customer_phone, platform, role, message, escalated, created_at) "
            "VALUES ($1, $2, 'assistant', $3, FALSE, $4)",
            phone, platform,
            "Mohon maaf akan saya eskalasi ke tim." if is_escalated else "Terima kasih, barang ready kak. Mau order?",
            created + timedelta(seconds=random.randint(3, 30)),
        )
        conv_count += 2
    print(f"Seeded {conv_count} conversation messages")

    # --- Content pieces ---
    for niche in NICHES:
        for channel in CHANNELS[:2]:
            cid = f"CT-{rand_link_id()[:6].upper()}"
            await conn.execute(
                "INSERT INTO content_pieces (content_id, channel, niche, script, status, views, likes, published_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                cid, channel, niche,
                f"Script konten {niche} untuk {channel}...",
                random.choice(["published", "draft"]),
                random.randint(100, 50000),
                random.randint(10, 5000),
                now - timedelta(days=random.randint(1, 30)),
            )
    print(f"Seeded {len(NICHES) * 2} content pieces")

    await conn.close()
    print("\nSeed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
