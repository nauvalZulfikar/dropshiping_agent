"""
Abstract base class for marketplace platform adapters.
All platform integrations must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class ListingData(BaseModel):
    name: str
    description: str
    price_idr: int
    stock: int
    images: list[str]
    category_id: Optional[str] = None
    weight_gram: Optional[int] = None
    sku: Optional[str] = None
    variants: Optional[list[dict]] = None


class OrderData(BaseModel):
    platform_order_id: str
    buyer_name: str
    buyer_phone: str
    shipping_address: str
    city: str
    postal_code: str
    courier: str
    courier_service: str
    quantity: int
    sale_price_idr: int
    product_sku: str


class PlatformAdapter(ABC):
    """Abstract interface for marketplace platform integrations."""

    @abstractmethod
    async def create_listing(self, data: ListingData) -> dict:
        """Create a new product listing. Returns platform-specific product ID."""
        ...

    @abstractmethod
    async def update_listing(self, platform_id: str, data: dict) -> dict:
        """Update an existing listing (price, stock, description, etc)."""
        ...

    @abstractmethod
    async def update_price(self, platform_id: str, price_idr: int) -> dict:
        """Update product price."""
        ...

    @abstractmethod
    async def update_stock(self, platform_id: str, stock: int) -> dict:
        """Update product stock."""
        ...

    @abstractmethod
    async def get_orders(self, status: Optional[str] = None) -> list[OrderData]:
        """Fetch orders from platform, optionally filtered by status."""
        ...

    @abstractmethod
    async def update_tracking(self, platform_order_id: str, resi: str, courier: str) -> dict:
        """Push tracking number (resi) to platform."""
        ...

    @abstractmethod
    async def get_product_info(self, platform_id: str) -> dict:
        """Get current product info from platform."""
        ...
