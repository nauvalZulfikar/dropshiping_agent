"""
TikTok Shop API adapter.
Docs: https://partner.tiktokshop.com/
"""
import hashlib
import hmac
import time
from typing import Optional

import httpx

from core.logger import logger
from store.platforms.base import PlatformAdapter, ListingData, OrderData

BASE_URL = "https://open-api.tiktokglobalshop.com"


class TikTokAdapter(PlatformAdapter):

    def __init__(self, app_key: str, app_secret: str, shop_id: str, access_token: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_id = shop_id
        self.access_token = access_token

    def _sign(self, path: str, params: dict) -> str:
        sorted_params = sorted(params.items())
        base_string = path + "".join(f"{k}{v}" for k, v in sorted_params)
        return hmac.new(
            self.app_secret.encode(),
            base_string.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _common_params(self, path: str) -> dict:
        ts = int(time.time())
        params = {
            "app_key": self.app_key,
            "shop_id": self.shop_id,
            "timestamp": str(ts),
            "access_token": self.access_token,
        }
        params["sign"] = self._sign(path, params)
        return params

    async def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        url = f"{BASE_URL}{path}"
        params = self._common_params(path)

        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, params=params)
            else:
                resp = await client.post(url, params=params, json=body or {})

        data = resp.json()
        if data.get("code") != 0:
            logger.error("tiktok_api_error", path=path, code=data.get("code"), message=data.get("message"))
        return data

    async def create_listing(self, data: ListingData) -> dict:
        body = {
            "product_name": data.name,
            "description": data.description,
            "category_id": data.category_id or "",
            "images": [{"id": img} for img in data.images],
            "skus": [{
                "original_price": str(data.price_idr),
                "stock_infos": [{"available_stock": data.stock}],
                "seller_sku": data.sku or "",
            }],
            "package_weight": {"value": str(data.weight_gram or 500), "unit": "GRAM"},
        }
        result = await self._request("POST", "/api/products", body)
        logger.info("tiktok_listing_created", name=data.name)
        return result

    async def update_listing(self, platform_id: str, data: dict) -> dict:
        return await self._request("PUT", f"/api/products/{platform_id}", data)

    async def update_price(self, platform_id: str, price_idr: int) -> dict:
        body = {
            "skus": [{"original_price": str(price_idr)}],
        }
        result = await self._request("PUT", f"/api/products/{platform_id}/prices", body)
        logger.info("tiktok_price_updated", product_id=platform_id, price=price_idr)
        return result

    async def update_stock(self, platform_id: str, stock: int) -> dict:
        body = {
            "skus": [{"stock_infos": [{"available_stock": stock}]}],
        }
        result = await self._request("PUT", f"/api/products/{platform_id}/stocks", body)
        logger.info("tiktok_stock_updated", product_id=platform_id, stock=stock)
        return result

    async def get_orders(self, status: Optional[str] = None) -> list[OrderData]:
        body = {
            "page_size": 50,
            "sort_by": "CREATE_TIME",
            "sort_type": 2,
        }
        if status:
            status_map = {
                "new": "AWAITING_SHIPMENT",
                "shipped": "SHIPPED",
                "delivered": "DELIVERED",
                "returned": "CANCELLED",
            }
            body["order_status"] = status_map.get(status, status)

        data = await self._request("POST", "/api/orders/search", body)

        orders = []
        for item in data.get("data", {}).get("orders", []):
            recipient = item.get("recipient_address", {})
            line_items = item.get("line_items", [])

            orders.append(OrderData(
                platform_order_id=item.get("order_id", ""),
                buyer_name=recipient.get("name", ""),
                buyer_phone=recipient.get("phone", ""),
                shipping_address=recipient.get("full_address", ""),
                city=recipient.get("city", ""),
                postal_code=recipient.get("zipcode", ""),
                courier=item.get("shipping_provider", ""),
                courier_service="",
                quantity=sum(li.get("quantity", 1) for li in line_items),
                sale_price_idr=int(float(item.get("payment", {}).get("total_amount", 0))),
                product_sku=line_items[0].get("seller_sku", "") if line_items else "",
            ))

        logger.info("tiktok_orders_fetched", count=len(orders))
        return orders

    async def update_tracking(self, platform_order_id: str, resi: str, courier: str) -> dict:
        body = {
            "order_id": platform_order_id,
            "tracking_number": resi,
            "shipping_provider_id": courier,
        }
        result = await self._request("POST", "/api/orders/ship", body)
        logger.info("tiktok_tracking_updated", order=platform_order_id, resi=resi)
        return result

    async def get_product_info(self, platform_id: str) -> dict:
        data = await self._request("GET", f"/api/products/{platform_id}")
        return data.get("data", {})
