import httpx
from typing import Optional

from core.config import FONNTE_API_KEY
from core.logger import logger

FONNTE_URL = "https://api.fonnte.com/send"


async def send_whatsapp(
    phone: str,
    message: str,
    image_url: Optional[str] = None,
) -> dict:
    headers = {"Authorization": FONNTE_API_KEY}
    payload = {
        "target": phone,
        "message": message,
    }
    if image_url:
        payload["url"] = image_url

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(FONNTE_URL, headers=headers, data=payload)
        result = resp.json()

    if result.get("status"):
        logger.info("wa_sent", phone=phone, message_len=len(message))
    else:
        logger.error("wa_send_failed", phone=phone, detail=result.get("detail", ""))

    return result


async def send_order_to_supplier(
    phone: str,
    order_id: int,
    product_name: str,
    variant: str,
    quantity: int,
    buyer_name: str,
    buyer_phone: str,
    shipping_address: str,
    city: str,
    postal_code: str,
    courier: str,
    courier_service: str,
) -> dict:
    message = (
        f"ORDER BARU #{order_id}\n\n"
        f"Produk: {product_name}\n"
        f"Variasi: {variant}\n"
        f"Qty: {quantity}\n\n"
        f"KIRIM KE:\n"
        f"Nama: {buyer_name}\n"
        f"HP: {buyer_phone}\n"
        f"Alamat: {shipping_address}\n"
        f"Kota: {city} {postal_code}\n\n"
        f"Kurir: {courier} ({courier_service})\n"
        f"Mohon kirim hari ini. Resi balas ke sini ya."
    )
    return await send_whatsapp(phone, message)


async def send_stock_alert(
    phone: str,
    product_name: str,
    stock: int,
    supplier_name: str,
) -> dict:
    message = (
        f"STOK KRITIS\n"
        f"Produk: {product_name}\n"
        f"Sisa stok: {stock} pcs\n"
        f"Supplier: {supplier_name}\n"
        f"Action: Restock atau nonaktifkan listing"
    )
    return await send_whatsapp(phone, message)


async def send_niche_flip_alert(
    phone: str,
    niche: str,
    score: float,
    epc: float,
    cvr: float,
    aov: int,
    clicks: int,
) -> dict:
    message = (
        f"NICHE SIAP DI-FLIP KE DROPSHIP\n"
        f"Niche: {niche}\n"
        f"Score: {score}/100\n"
        f"EPC: Rp {epc:,.0f}\n"
        f"CVR: {cvr:.1%}\n"
        f"AOV: Rp {aov:,}\n"
        f"Total klik: {clicks:,}\n"
        f"Action: Cari supplier lalu buka toko di niche ini"
    )
    return await send_whatsapp(phone, message)
