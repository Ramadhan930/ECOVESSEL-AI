from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ShipmentEditRequest(BaseModel):
    """Skema data untuk menerima request edit dari pengguna di Dashboard"""
    region: str
    shipping_mode: str
    scheduled_shipment_days: int
    product_category: str

class ShipmentResponse(BaseModel):
    """Skema standard respons data logistik aktif"""
    id: int
    region: str
    shipping_mode: str
    scheduled_shipment_days: int
    product_category: str
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True