"""
Tokopedia Seller API adapter.
Docs: https://developer.tokopedia.com/
"""
from typing import Optional

import httpx

from core.logger import logger
from store.platforms.base import PlatformAdapter, ListingData, OrderData

BASE_URL = "https://fs.tokopedia.net"


class TokopediaAdapter(PlatformAdapter):

    def __init__(self, client_id: str, client_secret: str, shop_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.shop_id = shop_id
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://accounts.tokopedia.com/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            data = resp.json()
            self._token = data.get("access_token", "")

        return self._token

    async def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{BASE_URL}{path}"

        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, headers=headers, json=body or {})

        data = resp.json()
        if resp.status_code != 200:
            logger.error("tokopedia_api_error", path=path, status=resp.status_code, body=data)
        return data

    async def create_listing(self, data: ListingData) -> dict:
        body = {
            "products": [{
                "Name": data.name,
                "Description": data.description,
                "Price": data.price_idr,
                "Stock": data.stock,
                "Weight": data.weight_gram / 1000 if data.weight_gram else 0.5,
                "pictures": [{"file_path": img} for img in data.images],
            }]
        }
        result = await self._request("POST", f"/v3/products/fs/{self.client_id}/create", body)
        logger.info("tokopedia_listing_created", name=data.name)
        return result

    async def update_listing(self, platform_id: str, data: dict) -> dict:
        body = {"products": [{"id": int(platform_id), **data}]}
        return await self._request("POST", f"/v3/products/fs/{self.client_id}/edit", body)

    async def update_price(self, platform_id: str, price_idr: int) -> dict:
        result = await self.update_listing(platform_id, {"Price": price_idr})
        logger.info("tokopedia_price_updated", product_id=platform_id, price=price_idr)
        return result

    async def update_stock(self, platform_id: str, stock: int) -> dict:
        result = await self.update_listing(platform_id, {"Stock": stock})
        logger.info("tokopedia_stock_updated", product_id=platform_id, stock=stock)
        return result

    async def get_orders(self, status: Optional[str] = None) -> list[OrderData]:
        status_map = {
            "new": 220,
            "sent_to_supplier": 400,
            "shipped": 500,
            "delivered": 700,
        }
        params = f"?shop_id={self.shop_id}&per_page=50"
        if status and status in status_map:
            params += f"&status={status_map[status]}"

        data = await self._request("GET", f"/v2/order/list{params}")

        orders = []
        for item in data.get("data", []):
            orders.append(OrderData(
                platform_order_id=str(item.get("order_id", "")),
                buyer_name=item.get("buyer", {}).get("name", ""),
                buyer_phone=item.get("buyer", {}).get("phone", ""),
                shipping_address=item.get("recipient", {}).get("address", {}).get("address_full", ""),
                city=item.get("recipient", {}).get("address", {}).get("city", ""),
                postal_code=item.get("recipient", {}).get("address", {}).get("postal_code", ""),
                courier=item.get("logistics", {}).get("shipping_agency", ""),
                courier_service=item.get("logistics", {}).get("service_type", ""),
                quantity=sum(p.get("quantity", 1) for p in item.get("products", [])),
                sale_price_idr=int(item.get("amt", {}).get("ttl_product_price", 0)),
                product_sku=item.get("products", [{}])[0].get("sku", ""),
            ))

        logger.info("tokopedia_orders_fetched", count=len(orders))
        return orders

    async def update_tracking(self, platform_order_id: str, resi: str, courier: str) -> dict:
        body = {
            "order_id": int(platform_order_id),
            "shipping_ref_num": resi,
        }
        result = await self._request("POST", f"/v1/order/{platform_order_id}/fs/{self.client_id}/confirm-shipping", body)
        logger.info("tokopedia_tracking_updated", order=platform_order_id, resi=resi)
        return result

    async def get_product_info(self, platform_id: str) -> dict:
        data = await self._request("GET", f"/v1/products/info?product_id={platform_id}")
        return data.get("data", {})
