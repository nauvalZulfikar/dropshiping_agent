from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class SupplierResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    source: str
    source_product_id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    price_usd: Optional[float] = None
    price_idr: Optional[int] = None
    shipping_cost_idr: int = 0
    shipping_days_estimate: Optional[int] = None
    moq: int = 1
    seller_name: Optional[str] = None
    rating: Optional[float] = None
    scraped_at: Optional[datetime] = None

    class Config:
        from_attributes = True
