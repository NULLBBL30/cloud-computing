from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    SALE = "SALE"
    RETURN = "RETURN"
    STOCK_RECEIVED = "STOCK_RECEIVED"
    ADJUSTMENT = "ADJUSTMENT"


class InventoryEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    store_id: str = Field(min_length=1, max_length=100)
    product_id: str = Field(min_length=1, max_length=100)
    event_type: EventType
    quantity: int = Field(gt=0, le=100000)


class InventoryResponse(BaseModel):
    tenant_id: str
    product_id: str
    quantity: int
