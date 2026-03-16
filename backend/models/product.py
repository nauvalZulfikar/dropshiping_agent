from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from uuid import UUID


class ProductListingResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    platform: str
    platform_product_id: Optional[str] = None
    title: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    price_idr: int
    original_price_idr: Optional[int] = None
    sold_count: int = 0
    sold_30d: int = 0
    review_count: int = 0
    rating: Optional[float] = None
    seller_name: Optional[str] = None
    seller_id: Optional[str] = None
    seller_badge: Optional[str] = None
    seller_city: Optional[str] = None
    stock: Optional[int] = None
    is_active: bool = True
    scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # Scores (joined from product_scores)
    margin_pct: Optional[float] = None
    opportunity_score: Optional[float] = None
    trend_score: Optional[float] = None
    sellability_score: Optional[float] = None
    competition_score: Optional[float] = None
    gate_passed: Optional[bool] = None

    class Config:
        from_attributes = True


class PriceHistoryPoint(BaseModel):
    price_idr: int
    sold_count: Optional[int] = None
    recorded_at: datetime
