"""
Shopee Affiliate API client.
Docs: https://affiliate.shopee.co.id/
"""
from datetime import date, timedelta
from typing import Optional

import httpx
from pydantic import BaseModel

from core.config import SHOPEE_AFFILIATE_TOKEN
from core.logger import logger

BASE_URL = "https://open-api.affiliate.shopee.co.id/graphql"


class ShopeeProduct(BaseModel):
    item_id: str
    shop_id: str
    name: str
    price: int
    original_price: int
    discount: Optional[str] = None
    image_url: str
    product_url: str
    category: str
    rating: Optional[float] = None
    sales: Optional[int] = None
    commission_rate: Optional[float] = None


class ShopeePerformance(BaseModel):
    date: str
    clicks: int
    conversions: int
    gmv_idr: int
    commission_idr: int


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {SHOPEE_AFFILIATE_TOKEN}",
        "Content-Type": "application/json",
    }


async def search_products(
    keyword: str,
    limit: int = 50,
    sort_type: int = 2,
) -> list[ShopeeProduct]:
    query = """
    query {
        productOfferV2(
            keyword: "%s"
            limit: %d
            sortType: %d
        ) {
            nodes {
                itemId
                shopId
                productName
                price
                originalPrice
                discount
                imageUrl
                productLink
                categoryName
                ratingStar
                sales
                commissionRate
            }
        }
    }
    """ % (keyword, limit, sort_type)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BASE_URL,
            headers=_headers(),
            json={"query": query},
        )

        if resp.status_code != 200:
            logger.error("shopee_affiliate_search_failed", status=resp.status_code, body=resp.text[:200])
            return []

        data = resp.json()

    nodes = (
        data.get("data", {})
        .get("productOfferV2", {})
        .get("nodes", [])
    )

    products = []
    for node in nodes:
        products.append(ShopeeProduct(
            item_id=str(node.get("itemId", "")),
            shop_id=str(node.get("shopId", "")),
            name=node.get("productName", ""),
            price=int(node.get("price", 0)),
            original_price=int(node.get("originalPrice", 0)),
            discount=node.get("discount"),
            image_url=node.get("imageUrl", ""),
            product_url=node.get("productLink", ""),
            category=node.get("categoryName", ""),
            rating=node.get("ratingStar"),
            sales=node.get("sales"),
            commission_rate=node.get("commissionRate"),
        ))

    logger.info("shopee_affiliate_search", keyword=keyword, count=len(products))
    return products


async def get_performance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[ShopeePerformance]:
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    query = """
    query {
        affiliateReport(
            startDate: "%s"
            endDate: "%s"
        ) {
            nodes {
                date
                clicks
                conversions
                gmv
                commission
            }
        }
    }
    """ % (start_date.isoformat(), end_date.isoformat())

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BASE_URL,
            headers=_headers(),
            json={"query": query},
        )

        if resp.status_code != 200:
            logger.error("shopee_affiliate_perf_failed", status=resp.status_code, body=resp.text[:200])
            return []

        data = resp.json()

    nodes = (
        data.get("data", {})
        .get("affiliateReport", {})
        .get("nodes", [])
    )

    records = [
        ShopeePerformance(
            date=node.get("date", ""),
            clicks=int(node.get("clicks", 0)),
            conversions=int(node.get("conversions", 0)),
            gmv_idr=int(node.get("gmv", 0)),
            commission_idr=int(node.get("commission", 0)),
        )
        for node in nodes
    ]

    logger.info("shopee_affiliate_perf_fetched", count=len(records))
    return records
