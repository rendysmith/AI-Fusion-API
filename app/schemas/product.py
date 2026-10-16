"""Product CRUD Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any


class ProductBase(BaseModel):
    """Base product fields."""

    name: str
    description: Optional[str] = None
    price: int
    currency: str = "RUB"
    display_type: str
    rewards: Dict[str, Any]
    external_id_getcourse: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class ProductCreate(ProductBase):
    """Request to create a product."""

    pass


class ProductUpdate(BaseModel):
    """Request to update a product."""

    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    display_type: Optional[str] = None
    rewards: Optional[Dict[str, Any]] = None
    external_id_getcourse: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ProductResponse(ProductBase):
    """Product response with timestamps."""

    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
