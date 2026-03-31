"""
Involve Asia API client.
Docs: https://developers.involve.asia/
"""
import hashlib
import hmac
import time
from datetime import date, timedelta
from typing import Optional

import httpx
from pydantic import BaseModel

from core.config import INVOLVE_ASIA_API_KEY, INVOLVE_ASIA_SECRET
from core.logger import logger

BASE_URL = "https://api.involve.asia/v2"


class ConversionRecord(BaseModel):
    transaction_id: str
    offer_id: str
    offer_name: str
    click_date: str
    conversion_date: str
    sale_amount: int
    commission: int
    status: str
    sub_id: Optional[str] = None


class ClickRecord(BaseModel):
    date: str
    offer_id: str
    offer_name: str
    clicks: int
    sub_id: Optional[str] = None


def _make_signature(timestamp: str) -> str:
    message = f"{INVOLVE_ASIA_API_KEY}{timestamp}"
    return hmac.new(
        INVOLVE_ASIA_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def _headers() -> dict:
    ts = str(int(time.time()))
    return {
        "Authorization": f"Bearer {INVOLVE_ASIA_API_KEY}",
        "X-Timestamp": ts,
        "X-Signature": _make_signature(ts),
        "Accept": "application/json",
    }


async def get_conversions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[ConversionRecord]:
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "per_page": 100,
    }

    records: list[ConversionRecord] = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params["page"] = page
            resp = await client.get(
                f"{BASE_URL}/conversions",
                headers=_headers(),
                params=params,
            )

            if resp.status_code != 200:
                logger.error("involve_asia_conversions_failed", status=resp.status_code, body=resp.text[:200])
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                records.append(ConversionRecord(
                    transaction_id=str(item.get("transaction_id", "")),
                    offer_id=str(item.get("offer_id", "")),
                    offer_name=item.get("offer_name", ""),
                    click_date=item.get("click_date", ""),
                    conversion_date=item.get("conversion_date", ""),
                    sale_amount=int(item.get("sale_amount", 0)),
                    commission=int(item.get("commission", 0)),
                    status=item.get("status", ""),
                    sub_id=item.get("sub_id"),
                ))

            if page >= data.get("last_page", 1):
                break
            page += 1

    logger.info("involve_asia_conversions_fetched", count=len(records), start=str(start_date), end=str(end_date))
    return records


async def get_clicks(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[ClickRecord]:
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "group_by": "date,offer",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/reports/clicks",
            headers=_headers(),
            params=params,
        )

        if resp.status_code != 200:
            logger.error("involve_asia_clicks_failed", status=resp.status_code, body=resp.text[:200])
            return []

        data = resp.json()
        items = data.get("data", [])

    records = [
        ClickRecord(
            date=item.get("date", ""),
            offer_id=str(item.get("offer_id", "")),
            offer_name=item.get("offer_name", ""),
            clicks=int(item.get("clicks", 0)),
            sub_id=item.get("sub_id"),
        )
        for item in items
    ]

    logger.info("involve_asia_clicks_fetched", count=len(records), start=str(start_date), end=str(end_date))
    return records


async def get_offers() -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/offers", headers=_headers())

        if resp.status_code != 200:
            logger.error("involve_asia_offers_failed", status=resp.status_code)
            return []

        data = resp.json()

    logger.info("involve_asia_offers_fetched", count=len(data.get("data", [])))
    return data.get("data", [])
