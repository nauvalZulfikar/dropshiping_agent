from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class MarginResult(BaseModel):
    sell_price_idr: int
    supplier_price_idr: int
    shipping_cost_idr: int
    platform_fee_idr: int
    gross_profit_idr: int
    net_profit_idr: int
    margin_pct: float
    gross_margin_pct: float
    supplier_price_ratio: float


class CompetitionAnalysis(BaseModel):
    product_id: UUID
    platform: str
    seller_count: int
    price_min_idr: Optional[int] = None
    price_max_idr: Optional[int] = None
    price_avg_idr: Optional[int] = None
    price_median_idr: Optional[int] = None
    top_seller_name: Optional[str] = None
    top_seller_sold_count: Optional[int] = None
    analyzed_at: Optional[datetime] = None


class NicheMapItem(BaseModel):
    niche: str
    slug: str
    market_size_idr: Optional[int] = None
    avg_margin: Optional[float] = None
    seller_count: int
    avg_trend_score: Optional[float] = None
    listing_count: int
