"""
Shopee Open Platform adapter.
Docs: https://open.shopee.com/
"""
import hashlib
import hmac
import time
from typing import Optional

import httpx

from core.config import SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_SHOP_ID
from core.logger import logger
from store.platforms.base import PlatformAdapter, ListingData, OrderData

BASE_URL = "https://partner.shopeemobile.com/api/v2"


def _sign(path: str, timestamp: int) -> str:
    base_string = f"{SHOPEE_PARTNER_ID}{path}{timestamp}{SHOPEE_SHOP_ID}"
    return hmac.new(
        SHOPEE_PARTNER_KEY.encode(),
        base_string.encode(),
        hashlib.sha256,
    ).hexdigest()


def _common_params(path: str) -> dict:
    ts = int(time.time())
    return {
        "partner_id": int(SHOPEE_PARTNER_ID),
        "shop_id": int(SHOPEE_SHOP_ID),
        "timestamp": ts,
        "sign": _sign(path, ts),
    }


class ShopeeAdapter(PlatformAdapter):

    async def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        url = f"{BASE_URL}{path}"
        params = _common_params(path)

        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, params=params)
            else:
                resp = await client.post(url, params=params, json=body or {})

        data = resp.json()
        if data.get("error"):
            logger.error("shopee_api_error", path=path, error=data.get("error"), message=data.get("message"))
        return data

    async def create_listing(self, data: ListingData) -> dict:
        body = {
            "item_name": data.name,
            "description": data.description,
            "original_price": data.price_idr / 100,
            "normal_stock": data.stock,
            "weight": data.weight_gram / 1000 if data.weight_gram else 0.5,
            "image": {"image_id_list": data.images},
            "category_id": int(data.category_id) if data.category_id else 0,
        }
        result = await self._request("POST", "/product/add_item", body)
        logger.info("shopee_listing_created", name=data.name, result=result.get("item_id"))
        return result

    async def update_listing(self, platform_id: str, data: dict) -> dict:
        body = {"item_id": int(platform_id), **data}
        return await self._request("POST", "/product/update_item", body)

    async def update_price(self, platform_id: str, price_idr: int) -> dict:
        body = {
            "item_id": int(platform_id),
            "price_list": [{"original_price": price_idr / 100}],
        }
        result = await self._request("POST", "/product/update_price", body)
        logger.info("shopee_price_updated", item_id=platform_id, price=price_idr)
        return result

    async def update_stock(self, platform_id: str, stock: int) -> dict:
        body = {
            "item_id": int(platform_id),
            "stock_list": [{"normal_stock": stock}],
        }
        result = await self._request("POST", "/product/update_stock", body)
        logger.info("shopee_stock_updated", item_id=platform_id, stock=stock)
        return result

    async def get_orders(self, status: Optional[str] = None) -> list[OrderData]:
        params_extra = {}
        if status:
            status_map = {
                "new": "READY_TO_SHIP",
                "shipped": "SHIPPED",
                "delivered": "COMPLETED",
                "returned": "CANCELLED",
            }
            params_extra["order_status"] = status_map.get(status, status)

        body = {
            "time_range_field": "create_time",
            "time_from": int(time.time()) - 7 * 86400,
            "time_to": int(time.time()),
            "page_size": 50,
            **params_extra,
        }
        data = await self._request("GET", "/order/get_order_list")

        orders = []
        for item in data.get("response", {}).get("order_list", []):
            order_sn = item.get("order_sn", "")
            detail = await self._request("GET", f"/order/get_order_detail?order_sn_list={order_sn}")
            order_info = detail.get("response", {}).get("order_list", [{}])[0]

            orders.append(OrderData(
                platform_order_id=order_sn,
                buyer_name=order_info.get("buyer_username", ""),
                buyer_phone=order_info.get("recipient_address", {}).get("phone", ""),
                shipping_address=order_info.get("recipient_address", {}).get("full_address", ""),
                city=order_info.get("recipient_address", {}).get("city", ""),
                postal_code=order_info.get("recipient_address", {}).get("zipcode", ""),
                courier=order_info.get("shipping_carrier", ""),
                courier_service="",
                quantity=sum(i.get("model_quantity_purchased", 1) for i in order_info.get("item_list", [])),
                sale_price_idr=int(float(order_info.get("total_amount", 0)) * 100),
                product_sku=order_info.get("item_list", [{}])[0].get("item_sku", ""),
            ))

        logger.info("shopee_orders_fetched", count=len(orders))
        return orders

    async def update_tracking(self, platform_order_id: str, resi: str, courier: str) -> dict:
        body = {
            "order_sn": platform_order_id,
            "tracking_number": resi,
        }
        result = await self._request("POST", "/logistics/ship_order", body)
        logger.info("shopee_tracking_updated", order=platform_order_id, resi=resi)
        return result

    async def get_product_info(self, platform_id: str) -> dict:
        data = await self._request("GET", f"/product/get_item_base_info?item_id_list={platform_id}")
        items = data.get("response", {}).get("item_list", [])
        return items[0] if items else {}
